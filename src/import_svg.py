import copy
from functools import cache, reduce
import math
import os
from pathlib import Path
from typing import TextIO, Union, Optional

import svgpathtools as svg
from build123d import *

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


def import_svg_as_forced_outline(
    svg_file: Union[str, Path, TextIO],
    reorient: bool = True,
    ignore_visibility: bool = False,
    tolerance: float = 0.01,
    extra_cleaning=False,
) -> ShapeList[Wire]:
    """Import an SVG and apply cleaning operations to return a closed wire outline, if possible. Useful for SVG outlines that are actually made of thin shapes or slightly disconnected paths. May fail on more complex shapes.

    * Removes duplicate lines, including ones that are reverses of the other, within a tolerance level (useful for 'outlines' that are actually very thin shapes)
    * Sorts paths such that they are end to start in order of distance, flipping them if needed to line up start to end
    * Goes through each path and creates the next one such that it starts at the end of the last one
    * Ensures the last and first paths are connected


    Args:
        svg_file (Union[str, Path, TextIO]): svg file
        reorient (bool, optional): Center result on origin by bounding box, and
        flip objects to compensate for svg orientation (so the resulting wire
        is the same way up as it looks when opened in an SVG viewer). Defaults
        to True.
        tolerance (float, optional): Amount of tolerance to use for comparing paths. Defaults to 0.01.
        extra_clean (bool, optional): Do some extra cleaning, including skipping tiny paths and some slight rounding off of corners, which may help smooth out tiny features in the outline. Defaults to False.

    Raises:
        ValueError: If an unknown path type is encountered.
        FileNotFoundError: the input file cannot be found.

    Returns:
        Wire: Forcefully connected SVG paths as a wire.
    """

    def point(path_point):
        return (path_point.real, path_point.imag)

    paths, attributes = svg.svg2paths(svg_file)
    curves = []
    for p in paths:
        curves.extend(p)
    curves = _remove_duplicate_paths(curves, tolerance=tolerance)
    curves = _sort_curves(curves)
    lines = []
    first_line = curves[0]
    with BuildLine() as bd_l:
        line_start = point(first_line.start)
        for i, p in enumerate(curves):
            if extra_cleaning and p.length() < tolerance:
                # Filter out tiny edges that may cause issues with OCCT ops
                continue
            line_end = point(p.end)
            if i == len(curves) - 1:
                # Forcefully reconnect the end to the start.
                # Note: This won't quite work if the last path is an arc,
                # but make_face should still sort it out. Once
                # EllipticalStartArc is released in build123d, this can be
                # fixed.
                line_end = point(first_line.start)
            else:
                if (
                    extra_cleaning
                    and Vertex(line_end).distance(Vertex(line_start)) < tolerance
                ):
                    # Skip this path if it's really short, just go straight
                    # to the next one.
                    continue
            if isinstance(p, svg.Line):
                l = Line(line_start, line_end)
                l_end = l @ 1
                l_strt = l @ 0
                pass
            elif isinstance(p, svg.Arc):
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
                    x_radius=p.radius.real,
                    y_radius=p.radius.imag,
                    start_angle=start,
                    end_angle=end,
                    rotation=math.degrees(p.phi),
                    angular_direction=dir_,
                    mode=Mode.PRIVATE,
                )
                add(l.move(Location(line_start - l @ 0)))

            else:
                print("Unknown path type for ", p)
                raise ValueError
            line_start = l @ 1

    wire = bd_l.wire()
    if reorient:
        wire = wire.move(Location(-wire.center(center_of=CenterOf.BOUNDING_BOX)))
        wire = mirror(wire)

    if extra_cleaning:
        # Going through a round of offset out, then back in, rounds off
        # internally projecting corners just a little, and seems to help reduce the
        # creation of invalid shapes.
        # This won't prevent objects from fitting within the outline, just place tiny gaps in some small concave (from the perspective of the gap) corners.
        off = 1.0
        wire = offset(offset(wire, off), -off)
    return wire


def _sort_curves(curves):
    """Return list of paths sorted and flipped so that they are connected end to end as the list iterates."""
    if not curves:
        return []

    def euclidean_distance(p1, p2):
        return math.sqrt((p1.real - p2.real) ** 2 + (p1.imag - p2.imag) ** 2)

    # Start with the first curve
    sorted_curves = [curves.pop(0)]

    while curves:
        last_curve = sorted_curves[-1]
        last_end = last_curve.end

        # Find the closest curve to the previous end point.
        closest_curve, closest_distance, flip = None, float("inf"), False
        for curve in curves:
            dist_start = euclidean_distance(last_end, curve.start)
            dist_end = euclidean_distance(last_end, curve.end)
            # If end is closer than start, flip the curve right way around.
            if dist_start < closest_distance:
                closest_curve, closest_distance, flip = curve, dist_start, False
            if dist_end < closest_distance:
                closest_curve, closest_distance, flip = curve, dist_end, True

        # Flip the curve if necessary
        if flip:
            flipped = _reverse_svg_curve(closest_curve)
            sorted_curves.append(flipped)
        else:
            sorted_curves.append(closest_curve)
        curves.remove(closest_curve)

    return sorted_curves


def _remove_duplicate_paths(paths, tolerance=0.01):
    """Remove paths that are identical to within the given positional and
    parameter tolerance limit, including similar but reversed paths."""
    cleaned_paths = []

    for path in paths:
        # Check if a similar path already exists in the cleaned list (either
        # forward or reversed)
        if any(
            _are_paths_similar(path, cleaned_path, tolerance)
            for cleaned_path in cleaned_paths
        ):
            # Skip this path if a similar one is already in the list
            continue
        cleaned_paths.append(path)

    return cleaned_paths


def _are_paths_similar(path1, path2, tolerance=0.01):
    """Compares two SVG paths, handling reversed paths, based on type, start/end points, length, and other attributes."""

    if type(path1) != type(path2):
        return False

    def lengths_are_close(p1, p2):
        return (
            abs(p1.length() - p2.length()) / max(p1.length(), p2.length()) < tolerance
        )

    if not lengths_are_close(path1, path2):
        return False

    def points_are_close(p1, p2):
        return abs(p1.real - p2.real) < tolerance and abs(p1.imag - p2.imag) < tolerance

    def check_forward():
        return points_are_close(path1.start, path2.start) and points_are_close(
            path1.end, path2.end
        )

    def check_reversed():
        return points_are_close(path1.start, path2.end) and points_are_close(
            path1.end, path2.start
        )

    # Handle reversed paths by checking both normal and reversed orientation
    if not (check_forward() or check_reversed()):
        return False

    # Additional checks for arcs (to handle radius, rotation, etc.)
    if isinstance(path1, svg.Arc) and isinstance(path2, svg.Arc):
        arc_attributes = [
            "radius",
            "phi",
            "theta",
            "delta",
            "rotation",
            "center",
            "large_arc",
            "sweep",
        ]


        for attr in arc_attributes:
            if attr in vars(path1) and attr in vars(path2):
                value1 = vars(path1)[attr]
                value2 = vars(path2)[attr]

                if attr == "radius" or attr == "rotation":
                    # Compare regular and inverted values for radius and rotation
                    # This may not be quite right for identifying reversed arcs
                    if not (
                        abs(value1 - value2) < tolerance
                        or abs(value1 + value2) < tolerance
                    ):
                        return False
                else:
                    if abs(value1 - value2) > tolerance:
                        return False

    return True


def _reverse_svg_curve(c):
    c = copy.deepcopy(c)
    t = c.start
    c.start = c.end
    c.end = t
    if isinstance(c, svg.Arc):
        # Flipping ElipticalArcs is a bit more complicated.
        # Calculate the new theta as the original end angle.
        new_theta = c.theta + c.delta
        # Reverse the delta.
        c.delta = -c.delta
        # Set theta to the new start angle.
        c.theta = new_theta
    return c


p = Path(
    "~/src/keyboard_design/maizeless/pcb/build/maizeless-Edge_Cuts gerber.svg"
).expanduser()
# p = script_dir / "build/outline.svg"
p = Path("~/src/keeb_snakeskin/manual_outlines/ferris-base-0.1.svg").expanduser()

base_face = make_face(import_svg_as_forced_outline(p))
show_object(base_face, name="base_face")
