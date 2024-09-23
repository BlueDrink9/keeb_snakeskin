import copy
import math
import os
from pathlib import Path

import build123d as bd
import svgpathtools as svg
from build123d import *
from build123d import Align, Rot
Loc = bd.Location

test_print = True
# For test prints, slice off the end. Tweak this by hand to get what you want.
if test_print:
    slice = Loc((-55, 0, 0)) * bd.Box(
        300, 300, 200, align=(Align.MIN, Align.CENTER, Align.CENTER)
    )

if "__file__" in globals():
    script_dir = Path(__file__).parent
else:
    script_dir = Path(os.getcwd())

# For debugging/viewing in cq-editor or vscode's ocp_vscode plugin.
if __name__ not in ["__cq_main__", "temp"]:
    show_object = lambda *_, **__: None
    log = lambda x: print(x)
    # show_object = lambda *_, **__: None

    import ocp_vscode as ocp
    from ocp_vscode import show
    ocp.set_port(3939)
    ocp.set_defaults(reset_camera=ocp.Camera.KEEP)
    show_object = lambda *args, **__: ocp.show(args)

# TODO:
# * Stand, attachments for straps. Separate module/plugin?

default_params = {
    "output_dir": script_dir / "../build",
    "split": True,
    "carrycase": True,
    "flush_carrycase_lip": False,
    "output_filetype": ".stl",
    "base_z_thickness": 3,
    "wall_xy_thickness": 3,
    "wall_z_height": 4.0,
    "z_space_under_pcb": 1,
    "wall_xy_bottom_tolerance": -0.3,
    "wall_xy_top_tolerance": 0.3,
    "cutout_position": 10,
    "cutout_width": 15,
    "honeycomb_base": True,
    "honeycomb_radius": 6,
    "honeycomb_thickness": 2,
    "chamfer_len": 1,
    "carrycase_tolerance_xy": 0.2,
    "carrycase_tolerance_z": 0.4,
    "carrycase_wall_xy_thickness": 4,
    "carrycase_z_gap_between_cases": 9 + 1,
    "carrycase_cutout_position": -90,
    "carrycase_cutout_xy_width": 15,
    "lip_len": 1.3,
    "lip_position_angles": [32, 158],
    "magnet_position": -90.0,
    "magnet_separation_distance": 0.8,
    "magnet_spacing": 12,
    "magnet_count": 8,
}
params = default_params
if test_print:
    params["base_z_thickness"] = 1.5

magnet_height = 2
magnet_radius = 4 / 2

def import_svg_as_face(path):
    # step = bd.import_step(str(Path('~/src/keyboard_design/maizeless/pcb/maizeless.step').expanduser()))
    # top = bd.project(step.faces().sort_by(Axis.Z)[-1], Plane.XY)
    # # show_object(top, name="STEP top")
    # base_face = bd.Face(top.face().outer_wire())
    # base_face.move(Loc(-base_face.center()))
    # base_face = -bd.mirror(base_face, about=bd.Plane.XZ).face()
    # show_object(base_face, name="STEP _base_face")
    #
    # with BuildPart() as part:
    #     offset(base_face, amount=-4)
    #     extrude(amount=8, taper=-15)
    # show_object(part, name="taper extrude test step")
    # return base_face


    # script, object_name = bd.import_svg_as_buildline_code(path)
    # outline = bd.import_svg(path)

    # # outline = bd.import_svg(script_dir / "build/simplified/outline.svg")
    # show_object(outline, name="raw_import_outline")
    # # return outline
    # # Round trip from outline to wires to face to wires to connect the disconnected
    # # edges that an svg gets imported with.
    # # outline = bd.make_face(outline)
    # # base_face = bd.make_face(outline.wires()).wire().fix_degenerate_edges(0.01)
    # # log(bd.Shape.mesh(outline.wires(), tolerance=0.01))
    # # outline = bd.Sketch([f for f in outline.edges() if f.length > 0.0001])
    # # What if we make the face from the trace, then filter the wires by
    # # length and fix degen edges?
    # bb = bd.Compound(outline).bounding_box()
    # # Offset bounding box to ensure it is larger than the outline.
    # sheet = bd.Rectangle(bb.size.X * 3, bb.size.Y * 3, align=None).located(Loc(bb.center()))
    # # Stamp out a slightly thickened outline that will hopefully cover up any gaps in the SVG paths/wires.
    # stamp = bd.trace(outline, line_width=0.001)
    # # stamp = bd.Sketch([f for f in stamp.faces() if f.area > 0.0001])
    # log(stamp)
    # # log([e.length for e in outline.edges()])
    # show_object(stamp, name="stamp")
    # # return
    # base_face = sheet - stamp
    # # Get the 2nd largest face, which should be the face created by the svg outline (since we've ensured the bounding box is at least area bigger.
    # base_face = sorted(base_face, key=lambda x: x.area)[-2]
    # show_object(base_face, name="sheet")
    # edges = [e for e in base_face.edges() if e.length > 0.0001]
    # # show(bd.make_face(edges).face())
    # base_face = bd.make_face(edges).face()
    # show_object(base_face, name="sheet")
    # return
    # # base_face = bd.make_face(base_face.outer_wire().fix_degenerate_edges(0.1)).face()
    # off = 0.5
    # # base_face = bd.offset(bd.offset(base_face, -off), off)
    # # base_face = _safe_offset2d(_safe_offset2d(base_face, -off), off)
    # base_face = bd.offset(base_face, -off).face()
    # base_face = _safe_offset2d(base_face, 5*off).face()
    # # log(len(base_face.faces()))
    # show_object(base_face, name="raw_import_base_face")
    # return base_face
    # base_face.move(Loc(-base_face.center()))
    # # base_face = bd.mirror(base_face, about=bd.Plane.XZ)

    # base_face = import_svg(path)

    # For testing
    # base_face = bd.Rectangle(30,80).locate(bd.Location((40, 40, 0)))
    # base_face = bd.import_svg(script_dir / "build/test_outline_drawn.svg")


    # show_object(base_face, name="base_face", options={"alpha":0.5, "color": (0, 155, 55)})
    # return base_face

    # script, object_name = bd.import_svg_as_buildline_code(path)
    # exec(script)
    # with BuildSketch() as general_import:
    #     exec("add("+object_name+".line)")
    #     make_face()
    # # exec("line = "+object_name+".line")
    # # show_object(line, name="general_import_line")
    # show_object(general_import.sketch.face(), name="general_import_face")
    # log(script)
    # return general_import.sketch.face()

    """Import SVG as paths and convert to build123d face. Although build123d has a native SVG import, it doesn't create clean wire connections from kicad exports of some shapes (in my experience), causing some more advanced operations to fail (e.g. tapers).
    This is how I used to do it, using b123d import:
    # Round trip from outline to wires to face to wires to connect the disconnected
    # edges that an svg gets imported with.
    outline = bd.import_svg(script_dir / "build/outline.svg")
    outline = bd.make_face(outline.wires()).wire().fix_degenerate_edges(0.01)
    """

    def point(path_point):
        return (path_point.real, path_point.imag)

    paths, attributes = svg.svg2paths(path)
    paths = [p[0] for p in paths]
    # paths.sort(key=lambda x: x.start)
    paths = sort_paths(paths)
    lines = []
    first_line = paths[0]
    with BuildPart() as bd_p:
        with BuildSketch() as bd_s:
            with BuildLine() as bd_l:
                line_start = point(first_line.start)
                for i, p in enumerate(paths):
                    # Filter out tiny edges that may cause issues with OCCT ops
                    if p.length() < 0.1:
                        continue
                    line_end = point(p.end)
                    # Forcefully reconnect the end to the start
                    if i == len(paths) - 1:
                        line_end = point(first_line.start)
                    # else:
                    #     if bd.Vertex(line_end).distance(bd.Vertex(line_start)) < 0.7:
                            # Skip this path if it's really short, just go
                            # straight to the next one.
                            # continue
                    if isinstance(p, svg.Line):
                        l = bd.Line(line_start, line_end)
                    elif isinstance(p, svg.Arc):
                        # Seems all the arcs have same value for real + imag radius, so just use real
                        r = p.radius.real
                        l = bd.RadiusArc(line_start, line_end, radius=r)
                    else:
                        log("Unknown path type for ", p)
                        raise ValueError
                    # log(f"path_{i}\n{str(p)}  len={p.length}")
                    # show_object(l, name=f"path_{i}")
                    line_start = l @ 1

            # show_object(bd_l.line, name="line")
            make_face()

    face = bd_s.sketch.face()
    face.move(Loc(-face.center()))

    # Going through a round of offset out then back in rounds off
    # internally projecting corners just a little, and seems to help reduce the creation of invalid shapes. This won't prevent a case from fitting in, just place tiny gaps in some small concave (from the perspective of the gap) corners.
    off = 1.0
    face = bd.offset(bd.offset(face, off), -off)

    # Flip the face because SVG import seems to be upside down
    face = bd.mirror(face, about=bd.Plane.XZ).face()
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


def generate_cases(svg_file, user_params=None):
    if not user_params:
        user_params = {}
    params.update(user_params)

    pcb_case_wall_height = params["z_space_under_pcb"] + params["wall_z_height"]

    base_face = import_svg_as_face(svg_file)

    def output_path(name):
        return str(Path(params["output_dir"] / name).with_suffix(params["output_filetype"]))

    print("Generating PCB case...")
    case = generate_pcb_case(base_face, pcb_case_wall_height)
    case_output = output_path("case")
    _export(case, case_output, "PCB case")

    if params["split"]:
        case_output = output_path("case_mirrored")
        _export(bd.mirror(case, about=bd.Plane.YZ), case_output, "mirrored half of the PCB case")

    if params["carrycase"]:
        print("Generating carrycase...")
        carry = generate_carrycase(base_face, pcb_case_wall_height)

        case_output = output_path("carrycase")
        _export(carry, case_output, "carry case")

    return


def generate_pcb_case(base_face, pcb_case_wall_height):
    base = bd.extrude(base_face, params["base_z_thickness"])

    wall_outer = bd.offset(
        base_face,
        params["wall_xy_thickness"],
    )

    inner_cutout = _friction_fit_cutout(
        base_face.face().move(Loc((0, 0, params["base_z_thickness"])))
    )
    # show_object(inner_cutout, name="inner")
    wall = (
        bd.extrude(wall_outer, pcb_case_wall_height + params["base_z_thickness"])
    )

    wall -= inner_cutout
    wall = _poor_mans_chamfer(wall, params["chamfer_len"], top=True)
    wall -= base


    if params["honeycomb_base"]:
        # Create honeycomb by subtracting it from the top face of the base.
        hc = _create_honeycomb_tile(
            params["base_z_thickness"], base.faces().sort_by(bd.Axis.Z).last
        )
        base -= hc

    case = wall + base

    case = _poor_mans_chamfer(case, params["chamfer_len"])


    # Create finger cutout
    topf = case.faces().sort_by(sort_by=bd.Axis.Z).last
    top_inner_wire = topf.wires()[0]
    polar_map = PolarWireMap(top_inner_wire, topf.center())
    cutout_location, _ = polar_map.get_polar_location(params["cutout_position"])
    cutout_box = _finger_cutout(
        cutout_location,
        params["wall_xy_thickness"],
        params["cutout_width"],
        pcb_case_wall_height,
    )

    case -= cutout_box

    if params["carrycase"]:
        if params["flush_carrycase_lip"]:
            # Cut out a lip for the carrycase
            case -= _lip(base_face)
        # Cut out magnet holes
        case -= _magnet_cutout(base_face, params["magnet_position"])

    if test_print:
        case -= slice

    show_object(case, name="case", options={"color": (0, 255, 0)})
    return case


def generate_carrycase(base_face, pcb_case_wall_height):
    cutout_outline = bd.offset(
        base_face, params["wall_xy_thickness"] + params["carrycase_tolerance_xy"]
    )
    wall_outline = bd.offset(cutout_outline, params["carrycase_wall_xy_thickness"])
    wall_outline -= cutout_outline

    wall_height = (
        pcb_case_wall_height
        + params["base_z_thickness"]
        + params["carrycase_z_gap_between_cases"]
    )
    wall = bd.extrude(wall_outline, wall_height)
    # cutout = bd.extrude(cutout_outline, wall_height)

    blocker = _carrycase_blocker(base_face, wall_height)
    case = wall + blocker

    # Have to chamfer before cutout because cutout breaks the face
    case = _poor_mans_chamfer(case, params["chamfer_len"])

    # Create finger cutout for removing boards
    botf = case.faces().sort_by(sort_by=bd.Axis.Z).first
    bottom_inner_wire = botf.wires()[0]
    polar_map = PolarWireMap(bottom_inner_wire, botf.center())
    cutout_location, _ = polar_map.get_polar_location(
        params["carrycase_cutout_position"]
    )
    cutout_box = _finger_cutout(
        cutout_location,
        params["carrycase_wall_xy_thickness"],
        params["carrycase_cutout_xy_width"],
        pcb_case_wall_height - magnet_height - 0.3,
    )
    # show_object(cutout_box, name="carry case cutout box")

    case -= cutout_box

    # Add lip to hold board in. Do after chamfer or chamfer breaks. If not
    # flush, changes the top face so do after finger cutout.
    case += _lip(base_face, carrycase=True)


    case -= _magnet_cutout(base_face, params["magnet_position"], carrycase=True)

    if test_print:
        case -= slice

    # Mirror on top face to create both sides
    topf = case.faces().sort_by(sort_by=bd.Axis.Z).last
    if not test_print:
        case += bd.mirror(case, about=bd.Plane(topf))
    show_object(case, name="carry case", options={"color": (0, 0, 255)})
    return case


def _carrycase_blocker(base_face, wall_height):
    """
    Part that blocks the pcb case from going all the way through.
    Blocker is made of 3 parts:
    1. a flat layer offset blocker_thickness_xy, extruded  2 * blocker_thickness_z
    from the base face,
    2. a subtracted layer starting at blocker_thickness_z that that tapers out
    to the carrycase wall, to create a printable overhang,
    3. a subtracted layer extruded blocker_thickness from base_face.
    """
    blocker_thickness_xy = (
        params["wall_xy_thickness"] + params["carrycase_tolerance_xy"]
    )
    blocker_thickness_z = 2
    taper = 44
    overhang_thickness_z = (blocker_thickness_xy - 0.1) / math.tan(math.radians(taper))
    overhang = bd.extrude(
        base_face,
        overhang_thickness_z,
        taper=-taper,
    ).moved(Loc((0, 0, blocker_thickness_z)))
    blocker_hull = bd.extrude(
        bd.offset(base_face, blocker_thickness_xy),
        amount=blocker_thickness_z + overhang_thickness_z,
    )
    blocker_inner_cutout = bd.extrude(base_face, amount=blocker_thickness_z)
    blocker = blocker_hull - overhang - blocker_inner_cutout
    # Locate the blocker at the top of the pcb case all
    blocker.move(
        Loc(
            (
                0,
                0,
                (
                    wall_height
                    + params["carrycase_tolerance_z"]
                    - params["carrycase_z_gap_between_cases"]
                ),
            )
        )
    )
    # show_object(blocker, name="blocker")
    return blocker


def _friction_fit_cutout(base_face):
    """Create a shape representing the inner case space, within the walls, to
    be cut out of the overall base shape.

    b123d engine has bizare problems with tapers on tiny -ve offsets from the
    face, which we need for the bottom tolerance.
    To work around this, we are offsetting a fixed, 'working' distance first,
    then tapering up such that it passes through the bottom tolerance size at
    the appropriate height (and continues to the top tolerance size).
    This does have a slight side effect in that the larger negative offset
    perverts the pcb outline shape a little more.
    We then cut off the extra bottom bit at the bottom of the case inner."""

    wall_height_pcb_up = params["wall_z_height"]
    total_wall_height = wall_height_pcb_up + params["z_space_under_pcb"]
    # calculate taper angle to blend between bottom and top tolerance.
    # tan(x) = o/a, where o is the total taper distance change on the XY plane,
    # and opp is the change in the Z axis.
    opp = params["wall_xy_top_tolerance"] - params["wall_xy_bottom_tolerance"]
    # Adj is just the height between the top and bottom tolerances, where
    # top = top of the wall, and bottom = where the pcb should
    # sit (z_space_under_pcb above the case bottom).
    adj = params["wall_z_height"]
    taper = math.degrees(math.atan(opp / adj))

    # ## Taper only from pcb up
    # # We seem to be able to get away with small tapers/extrusions up smaller
    # # wall heights.
    # # So let's try having an untapered wall below the pcb, and only tapering
    # # where the bottom tolerance will come into play.
    # bottom_face = _safe_offset2d(base_face.face(), params["wall_xy_bottom_tolerance"])
    # under_pcb = bd.extrude(bottom_face, amount=params["z_space_under_pcb"])
    # face_at_pcb = under_pcb.faces().sort_by(sort_by=bd.Axis.Z).last
    # tapered_cutout = bd.extrude(face_at_pcb, amount=params["wall_z_height"], taper=-taper)
    # case_inner_cutout = under_pcb + tapered_cutout

    T = math.tan(math.radians(taper))  # opp/adj
    # # We have two XY offsets from base_face - one at the bottom where the case
    # # should start (unknown), and one where the pcb starts (wall_xy_bottom_tolerance).
    case_bottom_offset = T * params["z_space_under_pcb"]
    bottom_offset = -case_bottom_offset + params["wall_xy_bottom_tolerance"]
    bottom_face = bd.offset(base_face, bottom_offset).face()
    case_inner_cutout = bd.extrude(bottom_face, amount=total_wall_height, taper=-taper)

    # Check tightness where pcb should sit
    # pcb_face = base_face.face().thicken(0.01).moved(Loc((0, 0, params["z_space_under_pcb"])))
    # case_inner_cutout -= pcb_face

    # show_object(case_inner_cutout, name="case_inner_cutout")
    return case_inner_cutout


def _safe_offset2d(face: Face, offset: float):
    """2D offset that is less likely to create invalid geometry.
    "the regular offset function fails when I do an inward offset where the
    enlarged inner wires overlap the new outer wire. If I instead reconstruct
    the face by subtracting the holes, I get what I want"
    https://discord.com/channels/964330484911972403/1074840524181217452/1285681009240838174
    """
    outer = face.outer_wire().offset_2d(offset)
    inners = [inner.offset_2d(-offset) for inner in face.inner_wires()]
    new_face = Face(outer)
    for inner in inners:
        new_face -= Face(inner)
    return new_face


def _finger_cutout(location, thickness, width, height):
    cutout_location = location * Rot(X=-90)
    # Mutliplying x and y by ~2 because we're centering it on those axis, but
    # only cutting out of one side.
    # Centering because sometimes depending on the wire we get the location
    # from, it'll be flipped, so we can't just align to MAX.
    cutout_box = bd.Box(
        # 2.1 to get some overlap
        thickness * 2.1,
        width,
        height * 2,
    )
    # Smooth the sides of the cutout
    cutout_box = bd.fillet(cutout_box.edges().filter_by(bd.Axis.X), height / 2)
    cutout_box.locate(cutout_location)
    return cutout_box


def _magnet_cutout(main_face, angle, carrycase=False):
    # Adding a bit of extra space around the radius, so that we can print
    # magnet holes without supports and account for the resulting droop.
    magnet_radius_y = magnet_radius + 0.2
    hole = bd.Plane.XY * bd.Ellipse(
        x_radius=magnet_radius,
        y_radius=magnet_radius_y,
    ).face()

    if carrycase:
        distance = (
            params["wall_xy_thickness"]
            + params["carrycase_tolerance_xy"]
            + magnet_height
        )
    else:
        # Distance into main wall of case
        distance = params["wall_xy_thickness"] - params["magnet_separation_distance"]
    template = bd.extrude(hole, distance)
    if not carrycase:
        # Extend into the case too to ensure no overlap, e.g. due to taper
        template += bd.extrude(hole, -(magnet_height))

    # Get second largest face parallel to XY plane - i.e., the inner case face
    # inner_case_face = sorted(case.faces().filter_by(bd.Plane.XY), key=lambda x: x.area)[-2]
    inner_wire = main_face.wires()[0]
    # show_object(inner_wire, name="inner_wire")
    polar_map = PolarWireMap(inner_wire, main_face.center())
    _, center_percent = polar_map.get_polar_location(angle)
    center_at_mm = center_percent * inner_wire.length
    span = (params["magnet_count"] - 1) * params["magnet_spacing"]
    start = center_at_mm - span / 2

    cutouts = []
    position = start
    for _ in range(params["magnet_count"]):
        cutout = copy.copy(template)
        location = inner_wire.location_at(
            position, position_mode=bd.PositionMode.LENGTH
        )
        cutout.orientation = location.orientation
        cutout = cutout.rotate(bd.Axis.Z, -90)
        cutout.position = location.position
        # Add 0.01 to avoid overlap issue cutting into base slightly. Float error?
        cutout.position += (0, 0, magnet_radius_y + params["base_z_thickness"] + 0.01)
        cutouts.append(cutout)
        # show_object(cutout, f"magnet_cutout_{position}")
        position += params["magnet_spacing"]

    # show_object(cutouts, name=f"magnet_cutouts_{carrycase}", options={"alpha": 0.8})
    return cutouts


def _lip(base_face, carrycase=False):
    # Use same z len as total lip xy len so that chamfer is complete.
    lip_xy_len = params["lip_len"]
    lip_z_len = params["lip_len"] + params["carrycase_tolerance_xy"]
    if not carrycase:
        # A little extra tolerance for lip cutout so that it fits more
        # smoothly, even with a bit of residual support plastic or warping.
        lip_xy_len += 0.3
        lip_z_len += 0.3
    # Inner face of carrycase
    inner_face = bd.offset(
        base_face,
        params["wall_xy_thickness"]
        + params["carrycase_tolerance_xy"]
    )
    # Outer is the full carrycase outer face
    outer_face = bd.offset(
        inner_face,
        params["carrycase_wall_xy_thickness"]
        # minus chamfer to avoid interfering/drawing over it.
        - params["chamfer_len"],
    )
    case_outer_face = bd.offset(base_face, params["wall_xy_thickness"])
    cutout_face = bd.offset(base_face, params["wall_xy_thickness"] - lip_xy_len)
    lip = outer_face - cutout_face

    # Intersect lip with sector/triangle between the two angles.
    bounds = case_outer_face.bounding_box()
    bound_max = max(bounds.size.X, bounds.size.Y) * 2
    boundary_lines = [
        bd.PolarLine(
            base_face.center(),
            bound_max,
            params["lip_position_angles"][0]
        ),
        bd.PolarLine(
            base_face.center(),
            bound_max,
            params["lip_position_angles"][1]
        )
    ]
    lip_boundary = bd.make_face(
        [*boundary_lines, bd.Line(boundary_lines[0] @ 1, boundary_lines[1] @ 1)]
    )
    lip = lip.intersect(lip_boundary)

    lip = bd.extrude(lip.face(), lip_z_len)

    if params["flush_carrycase_lip"]:
        # Poor man's chamfer of inner edge of lip
        # No point doing it with non-flush lip, because it would reduce the
        # catching surface.
        chamfer_cutout = bd.extrude(cutout_face.face(), lip_z_len, taper=-45)
        lip -= chamfer_cutout
    else:
        lip.move(Loc((0, 0, -lip_z_len)))

    # show_object(lip, name="lip", options={"alpha": 0.8})
    return lip


def _find_nearest_key(d, target_int):
    """Find the nearest existing key in a dict to a target integer"""
    nearest = min(d, key=lambda x: abs(x - target_int))
    return nearest


def _create_honeycomb_tile(depth, face):
    radius = params["honeycomb_radius"]
    cell_thickness = params["honeycomb_thickness"]
    d_between_centers = radius + cell_thickness
    locs = bd.HexLocations(d_between_centers, 50, 50, major_radius=True).local_locations
    h = bd.RegularPolygon(radius, 6)
    h = bd.extrude(h, -depth)
    hs = bd.Plane(face) * locs * h
    return hs


def _poor_mans_chamfer(shape, size, top=False):
    """Chamfers the bottom or top outer edge of a shape by subtracting a tapered extrusion"""
    faces = shape.faces().sort_by(sort_by=bd.Axis.Z)
    if top:
        face = faces.last
    else:
        face = faces.first
    face = bd.make_face(face.outer_wire()).face()
    if top:
        face = -face
    else:
        face = face
    outer = bd.extrude(face, size)
    inner_f = bd.offset(face, -size).face()
    inner = bd.extrude(inner_f, size, taper=-44)
    cutout = outer - inner
    out = shape - cutout
    return out


def _export(shape, path, name):
    path = Path(path).expanduser()
    if test_print:
        git_head_hash = os.popen("git rev-parse HEAD").read().strip()[:6]
        path = path.with_stem(path.stem + "_test_" + git_head_hash)
    print(f"Exporting {name} as {path}...")
    pathstr = str(path)
    if path.suffix == ".stl":
        bd.export_stl(shape, pathstr)
    elif path.suffix == ".step":
        bd.export_step(shape, pathstr)
    else:
        print(f"Invalid export suffix: '{path.suffix}' Must be .stl or .step")


class PolarWireMap:
    """Maps between polar locations of a wire relative to a central origin,
    where the resulting map is a dict of angle to location for
    use with wire ^ location (`wire.at_location`). Angle is calculated
    from the provide origin (intended to be the center of the closed
    wire)."""

    def __init__(self, wire, origin):
        self.wire, self.origin = wire, origin
        self.map_ = {}
        self.__map_polar_locations()

    def get_polar_location(self, angle):
        """return the wire's intersection location at `angle`."""
        angle = _find_nearest_key(self.map_, angle)
        at = self.map_[angle]
        return self.wire ^ at, at

    def __map_polar_locations(self):
        """Populate map with the polar location of
        a wire, where the resulting map is a dict of angle to location for
        use with wire ^ location (`wire.at_location`). Angle is calculated
        from the provide origin (intended to be the center of the closed
        wire)."""
        n_angles = 360
        at_position = 0
        iter = 1 / n_angles
        while at_position <= 1:
            location = self.wire ^ at_position
            at_position += iter
            ax1 = bd.Axis.X
            ax2 = bd.Wire(bd.Line(self.origin, location.position)).edge()
            ax2 = bd.Axis(edge=ax2)
            angle = round(ax1.angle_between(ax2))
            if ax2.direction.Y < 0:
                # Angle between gives up to 180 as a positive value, so we need to
                # flip it for -ve angles.
                angle = -angle
            self.map_[angle] = at_position


if __name__ in ["temp", "__cq_main__", "__main__"]:
    p = script_dir / "build/outline.svg"
    p = Path('~/src/keyboard_design/maizeless/pcb/build/maizeless-Edge_Cuts export.svg').expanduser()
    # p = Path('~/src/keyboard_design/maizeless/pcb/build/maizeless-Edge_Cuts gerber.svg').expanduser()
    # TODO: Move these to my personal maizeless build script
    import json
    config = Path(script_dir / "../preset_configs/maizeless.json")
    param_overrides = json.loads(config.read_text())
    params = default_params
    params.update(param_overrides)
    pcb_case_wall_height = params["z_space_under_pcb"] + params["wall_z_height"]


    base_face = import_svg_as_face(p)
    show_object(base_face, name="base_face")
    # bf = bd.make_face(base_face).face()
    # show_object(bf)

    carry = generate_carrycase(base_face, pcb_case_wall_height)
    # case = generate_pcb_case(base_face, pcb_case_wall_height)
