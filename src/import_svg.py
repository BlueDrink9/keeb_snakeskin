import copy
from functools import cache, reduce
import math
import os
from pathlib import Path

import svgpathtools as svg
from build123d import *
# Shape not imported as part of * for some reason
from build123d import Shape
# pylint has trouble with the OCP imports
# pylint: disable=no-name-in-module, import-error

if "__file__" in globals():
    script_dir = Path(__file__).parent
else:
    script_dir = Path(os.getcwd())


# For debugging/viewing in cq-editor or vscode's ocp_vscode plugin.
if __name__ not in ["__cq_main__", "temp"]:
    show_object = lambda *_, **__: None
    log = lambda x: print(x)
    # show_object = lambda *_, **__: None

    if __name__ == "__main__":
        import ocp_vscode as ocp
        from ocp_vscode import show

        ocp.set_port(3939)
        ocp.set_defaults(reset_camera=ocp.Camera.KEEP)
        show_object = lambda *args, **__: ocp.show(args)


def import_svg_as_buildline_code(file_name: str) -> tuple[str, str]:
    """translate_to_buildline_code

    Translate the contents of the given svg file into executable build123d/BuildLine code.

    Args:
        file_name (str): svg file name

    Returns:
        tuple[str, str]: code, builder instance name
    """

    translator = {
        "Line": ["Line", "start", "end"],
        "CubicBezier": ["Bezier", "start", "control1", "control2", "end"],
        "QuadraticBezier": ["Bezier", "start", "control", "end"],
        "Arc": [
            "EllipticalCenterArc",
            # "EllipticalStartArc",
            "start",
            "end",
            "radius",
            "rotation",
            "large_arc",
            "sweep",
        ],
    }
    paths_info = svg2paths(file_name)
    paths, _path_attributes = paths_info[0], paths_info[1]
    builder_name = os.path.basename(file_name).split(".")[0]
    builder_name = builder_name if builder_name.isidentifier() else "builder"
    buildline_code = [
        "from build123d import *",
        f"with BuildLine() as {builder_name}:",
    ]
    for path in paths:
        for curve in path:
            class_name = type(curve).__name__
            if class_name == "Arc":
                values = [
                    (curve.__dict__["center"].real, curve.__dict__["center"].imag)
                ]
                values.append(curve.__dict__["radius"].real)
                values.append(curve.__dict__["radius"].imag)
                start, end = sorted(
                    [
                        curve.__dict__["theta"],
                        curve.__dict__["theta"] + curve.__dict__["delta"],
                    ]
                )
                values.append(start)
                values.append(end)
                values.append(degrees(curve.__dict__["phi"]))
                if curve.__dict__["delta"] < 0.0:
                    values.append("AngularDirection.CLOCKWISE")
                else:
                    values.append("AngularDirection.COUNTER_CLOCKWISE")

                # EllipticalStartArc implementation
                # values = [p.__dict__[parm] for parm in translator[class_name][1:3]]
                # values.append(p.__dict__["radius"].real)
                # values.append(p.__dict__["radius"].imag)
                # values.extend([p.__dict__[parm] for parm in translator[class_name][4:]])
            else:
                values = [curve.__dict__[parm] for parm in translator[class_name][1:]]
            values_str = ",".join(
                [
                    f"({v.real}, {v.imag})" if isinstance(v, complex) else str(v)
                    for v in values
                ]
            )
            buildline_code.append(f"    {translator[class_name][0]}({values_str})")

    return ("\n".join(buildline_code), builder_name)


def import_svg_as_face(path):
    """Import SVG as paths and convert to build123d face. Although build123d has a native SVG import, it doesn't create clean wire connections from kicad exports of some shapes (in my experience), causing some more advanced operations to fail (e.g. tapers).
    This is how I used to do it, using b123d import:
    # Round trip from outline to wires to face to wires to connect the disconnected
    # edges that an svg gets imported with.
    outline = import_svg(script_dir / "build/outline.svg")
    outline = make_face(outline.wires()).wire().fix_degenerate_edges(0.01)
    """

    # script, object_name = import_svg_as_buildline_code(path)
    # exec(script)
    # with BuildSketch() as general_import:
    #     exec("add("+object_name+".line)")
    #     make_face()
    def point(path_point):
        return (path_point.real, path_point.imag)

    paths, attributes = svg.svg2paths(path)
    [print("Error: path has multiple segments: ", p) for p in paths if len(p) != 1]
    curves = []
    for p in paths:
        curves.extend(p)
    curves = remove_duplicate_paths(curves, tolerance=0.01)
    curves = sort_paths(curves)
    lines = []
    first_line = curves[0]
    with BuildPart() as bd_p:
        with BuildSketch() as bd_s:
            with BuildLine() as bd_l:
                line_start = point(first_line.start)
                for i, p in enumerate(curves):
                    # Filter out tiny edges that may cause issues with OCCT ops
                    if p.length() < 0.1:
                        continue
                    line_end = point(p.end)
                    # Forcefully reconnect the end to the start
                    if i == len(curves) - 1:
                        line_end = point(first_line.start)
                    # else:
                    #     if Vertex(line_end).distance(Vertex(line_start)) < 0.1:
                        # Skip this path if it's really short, just go
                        # straight to the next one.
                        # continue
                    if isinstance(p, svg.Line):
                        l = Line(line_start, line_end)
                    elif isinstance(p, svg.Arc):
                        # If we can use a RadiusArc, do so because we can
                        # define the start and end positions to mate with the
                        # previous paths.
                        try:
                        #     l = RadiusArc(line_start, line_end, radius=p.radius.real)
                        # except ValueError:
                            # Usually because the radius wasn't big enough to
                            # span the distance. Probably not a standard radius
                            # curve.
                            start, end = sorted(
                                [
                                    p.theta,
                                    p.theta + p.delta,
                                ]
                            )
                            if p.delta < 0.0:
                                dir_ = AngularDirection.CLOCKWISE
                            else:
                                dir_ = AngularDirection.COUNTER_CLOCKWISE
                            l = EllipticalCenterArc(
                                center=point(p.center),
                                x_radius=abs(p.radius.real),
                                y_radius=abs(p.radius.imag),
                                start_angle=start,
                                end_angle=end,
                                rotation=math.degrees(p.phi),
                                angular_direction=dir_,
                                # mode=Mode.PRIVATE,
                            )
                            l = l.move(Location(l @ 0 - line_start))
                            # l.mode = Mode.ADD
                        except:
                            pass

                    else:
                        print("Unknown path type for ", p)
                        raise ValueError
                    # log(f"path_{i}\n{str(p)}  len={p.length}")
                    # show_object(l, name=f"path_{i}")
                    line_start = l @ 1

            show_object(bd_l.line, name="line")
            make_face()

    face = bd_s.sketch.face()
    face.move(Loc(-face.center()))

    # Going through a round of offset out then back in rounds off
    # internally projecting corners just a little, and seems to help reduce the creation of invalid shapes. This won't prevent a case from fitting in, just place tiny gaps in some small concave (from the perspective of the gap) corners.
    off = 1.0
    face = offset(offset(face, off), -off)

    # Flip the face because SVG import seems to be upside down
    face = mirror(face, about=Plane.XZ).face()
    # Project to make sure it's all on the same plane. I think it should be
    # regardless, but just in case...
    face = -project(face, Plane.XY).face()
    # show_object(face, "imported face")
    return face


def sort_paths(lines):
    """Return list of paths sorted and flipped so that they are connected end to end as the list iterates."""
    if not lines:
        return []

    def euclidean_distance(p1, p2):
        return math.sqrt((p1.real - p2.real) ** 2 + (p1.imag - p2.imag) ** 2)

    # Start with the first line
    sorted_lines = [lines.pop(0)]

    while lines:
        last_line = sorted_lines[-1]
        last_end = last_line.end

        # Find the closest line to the last end point
        closest_line, closest_distance, flip = None, float("inf"), False
        for line in lines:
            dist_start = euclidean_distance(last_end, line.start)
            dist_end = euclidean_distance(last_end, line.end)
            # if end is closer than start, flip the line right way around
            if dist_start < closest_distance:
                closest_line, closest_distance, flip = line, dist_start, False
            if dist_end < closest_distance:
                closest_line, closest_distance, flip = line, dist_end, True

        # Flip the line if necessary
        if flip:
            t = closest_line.start
            closest_line.start = closest_line.end
            closest_line.end = t
            if isinstance(closest_line, svg.Arc):
                closest_line.radius = -closest_line.radius

        sorted_lines.append(closest_line)
        lines.remove(closest_line)

    return sorted_lines


def are_paths_similar(path1, path2, tolerance=0.01):
    """Compares two paths, handling reversed paths, based on type, start/end points, length, and other attributes."""

    def points_are_close(p1, p2):
        return abs(p1.real - p2.real) < tolerance and abs(p1.imag - p2.imag) < tolerance

    def lengths_are_close(p1, p2):
        return abs(p1.length() - p2.length()) / max(p1.length(), p2.length()) < tolerance

    # Compare path types
    if type(path1) != type(path2):
        return False

    # Compare lengths (paths must have similar lengths to be considered identical)
    if not lengths_are_close(path1, path2):
        return False

    # Check both directions (normal and reversed)
    def check_forward():
        return points_are_close(path1.start, path2.start) and points_are_close(path1.end, path2.end)

    def check_reversed():
        return points_are_close(path1.start, path2.end) and points_are_close(path1.end, path2.start)

    # Handle reversed paths: Check both normal and reversed orientation
    if not (check_forward() or check_reversed()):
        return False

    # Additional checks for arcs (to handle radius, rotation, etc.)
    if isinstance(path1, svg.Arc) and isinstance(path2, svg.Arc):
        arc_attributes = ['radius', 'phi', 'theta', 'delta', 'rotation', 'center', 'large_arc', 'sweep']

        path1_vars = vars(path1)
        path2_vars = vars(path2)

        for attr in arc_attributes:
            if attr in path1_vars and attr in path2_vars:
                value1 = path1_vars[attr]
                value2 = path2_vars[attr]

                if attr == 'radius' or attr == 'rotation':
                    # Compare regular and inverted values for radius and rotation
                    if not (abs(value1 - value2) < tolerance or abs(value1 + value2) < tolerance):
                        return False
                else:
                    if abs(value1 - value2) > tolerance:
                        return False

    return True

def remove_duplicate_paths(paths, tolerance=0.01):
    """Remove paths that are identical to within the given positional and
    parameter tolerance limit, including similar but reversed paths."""
    cleaned_paths = []

    for path in paths:
        # Check if a similar path already exists in the cleaned list (either forward or reversed)
        if any(are_paths_similar(path, cleaned_path, tolerance) for cleaned_path in cleaned_paths):
            continue  # Skip this path if a similar one is already in the list
        cleaned_paths.append(path)

    return cleaned_paths


# Continue with your existing workflow

p = Path('~/src/keyboard_design/maizeless/pcb/build/maizeless-Edge_Cuts gerber.svg').expanduser()
# p = script_dir / "build/outline.svg"
p = Path('~/src/keeb_snakeskin/manual_outlines/ferris-base-0.1.svg').expanduser()

base_face = import_svg_as_face(p)
show_object(base_face, name="base_face")
