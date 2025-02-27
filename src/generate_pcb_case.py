import copy
import math
import os
from functools import cache
from pathlib import Path

from build123d import *
import OCP

try:
    from default_params import default_params
    from import_svg import import_svg_as_forced_outline
except ImportError:
    from .default_params import default_params
    from .import_svg import import_svg_as_forced_outline


cfg = default_params

Loc = Location

tent_leg_cutout_tolerance = 0.3
misc_tol = 0.2

test_print = False
fast_render = False
# For test prints, slice off the end. Tweak this by hand to get what you want.
if test_print:
    slice = Loc((-55, 0, 0)) * Box(
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

    if __name__ == "__main__":
        import ocp_vscode as ocp
        from ocp_vscode import show

        ocp.set_port(3939)
        ocp.set_defaults(reset_camera=ocp.Camera.KEEP)
        show_object = lambda *args, **__: ocp.show(args)


test_overrides = {
    "base_z_thickness": 1.5,
    "magnet_position": -180 + 22,
    "magnet_count": 1,
}

magnet_height = 2
magnet_radius = 4 / 2
magnet_radius_y = magnet_radius + 0.3


def import_svg_as_face(path):
    """Import SVG as paths and convert to build123d face. Although build123d has a native SVG import, it doesn't create clean wire connections from kicad exports of some shapes (in my experience), causing some more advanced operations to fail (e.g. tapers).
    This is how I used to do it, using b123d import:
    # Round trip from outline to wires to face to wires to connect the disconnected
    # edges that an svg gets imported with.
    outline = import_svg(script_dir / "build/outline.svg")
    outline = make_face(outline.wires()).wire().fix_degenerate_edges(0.01)
    """
    face = import_svg_as_forced_outline(
        path, extra_cleaning=False, simplify_beziers=cfg["simplify_beziers"]
    )
    # face = make_face(wire)
    # face = _fix_face_edges(face)

    # import tempfile
    # # Try to reduce small facets by exporting it and re-importing face.
    # remade = make_face(face.face().outer_wire())
    # shape = extrude(remade, 3)
    # with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as temp_file:
    #     temp_file_path = temp_file.name
    #     exporter = ExportSVG(precision=2)
    #     exporter.add_shape(shape)
    #     exporter.write(temp_file_path)
    #     imported = import_svg_as_forced_outline(temp_file_path, extra_cleaning=False)
    #     # projected_shape = section(imported, section_by=Plane.XY, height=0.5)
    #     # projected_shape = project(imported_shape, Plane.XY)
    #     face = projected_shape.fuse().face()

    # Going through a round of offset out, then back in, rounds off
    # internally projecting corners just a little, and seems to help reduce the
    # creation of invalid shapes.
    # This won't prevent objects from fitting within the outline, just place tiny gaps in some small concave (from the perspective of the gap) corners.
    face_orig = copy.copy(face)
    if cfg["tiny_edge_rounding"]:
        for off in [1.0, -0.01]:
            try:
                face = offset(offset(face, off), -off)
            except RuntimeError:
                pass
    return face


def generate_cases(svg_file, user_params=None):
    if not user_params:
        user_params = {}
    cfg.update(user_params)
    if test_print:
        cfg.update(test_overrides)

    pcb_case_wall_height = cfg["z_space_under_pcb"] + cfg["wall_z_height"]

    base_face = import_svg_as_face(svg_file)

    def output_path(shape):
        p = Path(cfg["output_dir"] / svg_file.stem / shape).with_suffix(
            cfg["output_filetype"]
        )
        p.parent.mkdir(parents=True, exist_ok=True)
        return str(p)

    print("Generating PCB case...")
    case = generate_pcb_case(base_face, pcb_case_wall_height)
    case_output = output_path("case")
    _export(case, case_output, "PCB case")

    if cfg["split"] and not test_print:
        case_output = output_path("case_mirrored")
        _export(
            mirror(case, about=Plane.YZ), case_output, "mirrored half of the PCB case"
        )

    if cfg["carrycase"]:
        print("Generating carrycase...")
        carry = generate_carrycase(base_face, pcb_case_wall_height)

        case_output = output_path("carrycase")
        _export(carry, case_output, "carry case")

    if cfg["tenting_stand"]:
        print("Generating tenting legs...")
        try:
            from tenting_stand import _calc_leg_open_angle, tenting_legs
        except ImportError:
            from .tenting_stand import _calc_leg_open_angle, tenting_legs


        wall_height = pcb_case_wall_height + cfg["base_z_thickness"]
        case_len = _calc_case_len(base_face)
        flaps = tenting_legs(
            cfg["tent_legs"], case_len, cfg["tent_hinge_bolt_d"], wall_height
        )
        for i, flap in enumerate(flaps):
            output = output_path(f"tenting_flap_{i+1}")
            _export(flap, output, f"tenting flap {i+1}")
            output = output_path(f"tenting_flap_mirrored_{i+1}")
            _export(
                mirror(flap, about=Plane.YZ), output, f"mirrored tenting flap {i+1}"
            )

    return


def _do_wall_cutouts(case, pcb_case_wall_height):
    topf = case.faces().sort_by(sort_by=Axis.Z).last
    top_inner_wire = topf.wires().sort_by(SortBy.LENGTH)[0]

    to_do = [[cfg["cutout_position"], cfg["cutout_width"]], *cfg["additional_cutouts"]]
    for angle, width in to_do:
        location, rotation, _ = _wire_location_at_angle(top_inner_wire, angle)
        cutout_box = _finger_cutout(
            location,
            rotation,
            cfg["wall_xy_thickness"],
            width,
            pcb_case_wall_height,
        )
        case -= cutout_box

    return case


@cache
def generate_pcb_case(base_face, pcb_case_wall_height):
    base = extrude(base_face, cfg["base_z_thickness"])
    total_wall_height = (
        cfg["z_space_under_pcb"] + cfg["wall_z_height"] + cfg["base_z_thickness"]
    )

    wall_outer = offset(
        base_face,
        cfg["wall_xy_thickness"],
    )

    inner_cutout = _friction_fit_cutout(
        base_face.face().move(Loc((0, 0, cfg["base_z_thickness"])))
    )
    # show_object(inner_cutout, name="inner")
    wall = extrude(wall_outer, pcb_case_wall_height + cfg["base_z_thickness"])

    wall -= inner_cutout
    wall = _poor_mans_chamfer(wall, cfg["chamfer_len"], top=True)
    wall -= base

    if cfg["honeycomb_base"]:
        # Create honeycomb by subtracting it from the top face of the base.
        hc = _create_honeycomb_tile(
            cfg["base_z_thickness"], base.faces().sort_by(Axis.Z).last
        )
        base -= hc

    case = wall + base

    case = _poor_mans_chamfer(case, cfg["chamfer_len"])

    case = _do_wall_cutouts(case, pcb_case_wall_height)

    if cfg["carrycase"]:
        if cfg["flush_carrycase_lip"]:
            # Cut out a lip for the carrycase
            case -= _lip(base_face)
        # Cut out magnet holes
        case -= _magnet_cutout(base_face, cfg["magnet_position"])

    if cfg["strap_loop"]:
        strap_loop = _strap_loop(
            base_face,
            pcb_case_wall_height + cfg["base_z_thickness"] - cfg["chamfer_len"] * 2,
        ).moved(Loc((0, 0, cfg["chamfer_len"])))
        edges = strap_loop.edges()
        # Filter out edges that touches the case to avoid sharp angle on
        # the chamfer
        edges = edges.group_by(Axis.X)[:2]
        strap_loop = chamfer(
            edges, min(1.5, cfg["chamfer_len"], cfg["strap_loop_thickness"] / 2)
        )
        case += strap_loop

    if cfg["tenting_stand"]:
        case += _tent_hinge(base_face, total_wall_height)
        case = _cutout_tenting_flaps(
            case,
            base_face,
            total_wall_height,
        )

    if test_print:
        case -= slice

    show_object(case, name="case", options={"color": (0, 255, 0)})
    return case


def generate_carrycase(base_face, pcb_case_wall_height):
    z_space_for_case = (
        cfg["base_z_thickness"] + pcb_case_wall_height + cfg["carrycase_tolerance_z"]
    )
    cutout_outline = offset(
        base_face, cfg["wall_xy_thickness"] + cfg["carrycase_tolerance_xy"]
    )
    wall_outline = offset(cutout_outline, cfg["carrycase_wall_xy_thickness"])
    wall_outline -= cutout_outline

    wall_height = (
        cfg["base_z_thickness"]
        + pcb_case_wall_height
        + cfg["carrycase_z_gap_between_cases"] / 2
    )
    wall = extrude(wall_outline, wall_height)
    # cutout = extrude(cutout_outline, wall_height)

    blocker = _carrycase_blocker(base_face, z_space_for_case)
    case = wall + blocker

    # Have to chamfer before cutout because cutout breaks the face
    case = _poor_mans_chamfer(case, cfg["chamfer_len"])

    # Create finger cutout for removing boards
    botf = case.faces().sort_by(sort_by=Axis.Z).first
    bottom_inner_wire = botf.wires()[0]
    location, rotation, location_percent = _wire_location_at_angle(
        bottom_inner_wire, cfg["carrycase_cutout_position"]
    )
    cutout_box = _finger_cutout(
        location,
        rotation,
        cfg["carrycase_wall_xy_thickness"],
        cfg["carrycase_cutout_xy_width"],
        # Use same thickness as base to avoid the magnets.
        # cfg["base_z_thickness"] - 0.2,
        # Actually, screw the magnet holes, better to have an easy to remvoe
        # board.
        z_space_for_case,
    )
    # show_object(cutout_box, name="carry case cutout box")

    case -= cutout_box

    if cfg["strap_loop"]:
        strap_loop = (
            _strap_loop(
                # Not using real height because we're cutting out a specific
                # amount.
                base_face,
                0.1,
            )
            .faces()
            .sort_by(sort_by=Axis.Z)
            .first
        )
        cutout_face = offset(
            make_hull(strap_loop.edges()), cfg["carrycase_tolerance_xy"]
        ).face()
        case -= extrude(cutout_face, z_space_for_case)

    if cfg["tenting_stand"]:
        # Cut out case hinge
        cutout_face = _flatten_to_faces(
            _tent_hinge(base_face, pcb_case_wall_height + cfg["base_z_thickness"])
        )
        cutout_face = offset(cutout_face, cfg["carrycase_tolerance_xy"]).face()
        case -= extrude(cutout_face, z_space_for_case)
        # Cut out leg hinges
        cutout_face = _get_tenting_flap_shadow(
            base_face, pcb_case_wall_height + cfg["base_z_thickness"]
        )
        cutout_face = offset(cutout_face, tent_leg_cutout_tolerance).face()
        case -= extrude(cutout_face, z_space_for_case)

    # Add lip to hold board in. Do after chamfer or chamfer breaks. If not
    # flush, changes the top face so do after finger cutout.
    case += _lip(base_face, carrycase=True)

    case -= _magnet_cutout(base_face, cfg["magnet_position"], carrycase=True)

    if test_print:
        case -= slice

    # Mirror on top face to create both sides
    topf = case.faces().sort_by(sort_by=Axis.Z).last
    if not test_print:
        case += mirror(case, about=Plane(topf))
    show_object(case, name="carry case", options={"color": (0, 0, 255)})
    return case


def _carrycase_blocker(base_face, z_space_for_case):
    """
    Part that blocks the pcb case from going all the way through.
    Blocker is made of 3 parts:
    1. a flat layer offset blocker_thickness_xy, extruded  2 * blocker_thickness_z
    from the base face,
    2. a subtracted layer starting at blocker_thickness_z that that tapers out
    to the carrycase wall, to create a printable overhang,
    3. a subtracted layer extruded blocker_thickness from base_face.
    """
    carrycase_inner_face = offset(
        base_face, cfg["wall_xy_thickness"] + cfg["carrycase_tolerance_xy"]
    ).face()
    # Half the wall thickness. Don't want too close to the keyboard because as
    # the keys tilt to get in, they might hit the blocker.
    blocker_thickness_xy = cfg["wall_xy_thickness"] / 2 + cfg["carrycase_tolerance_xy"]
    blocker_thickness_z = 1.5
    taper = 44
    overhang_thickness_z = (blocker_thickness_xy - 0.1) / math.tan(math.radians(taper))
    blocker_hull = extrude(
        carrycase_inner_face,
        amount=blocker_thickness_z + overhang_thickness_z,
    )
    inner_cutout_face = offset(carrycase_inner_face, -blocker_thickness_xy).face()
    inner_cutout = extrude(inner_cutout_face, amount=blocker_thickness_z)
    overhang = extrude(
        inner_cutout_face,
        overhang_thickness_z,
        taper=-taper,
    ).moved(Loc((0, 0, blocker_thickness_z)))
    blocker = blocker_hull - overhang - inner_cutout
    # Locate the blocker at the top of the pcb case wall
    blocker.move(Loc((0, 0, z_space_for_case)))
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

    wall_height_pcb_up = cfg["wall_z_height"]
    total_wall_height = wall_height_pcb_up + cfg["z_space_under_pcb"]
    # calculate taper angle to blend between bottom and top tolerance.
    # tan(x) = o/a, where o is the total taper distance change on the XY plane,
    # and opp is the change in the Z axis.
    opp = cfg["wall_xy_top_tolerance"] - cfg["wall_xy_bottom_tolerance"]
    # Adj is just the height between the top and bottom tolerances, where
    # top = top of the wall, and bottom = where the pcb should
    # sit (z_space_under_pcb above the case bottom).
    adj = cfg["wall_z_height"]
    taper = math.degrees(math.atan(opp / adj))

    # ## Taper only from pcb up
    # # We seem to be able to get away with small tapers/extrusions up smaller
    # # wall heights.
    # # So let's try having an untapered wall below the pcb, and only tapering
    # # where the bottom tolerance will come into play.
    # bottom_face = _safe_offset2d(base_face.face(), params["wall_xy_bottom_tolerance"])
    # under_pcb = extrude(bottom_face, amount=params["z_space_under_pcb"])
    # face_at_pcb = under_pcb.faces().sort_by(sort_by=Axis.Z).last
    # tapered_cutout = extrude(face_at_pcb, amount=params["wall_z_height"], taper=-taper)
    # case_inner_cutout = under_pcb + tapered_cutout

    T = math.tan(math.radians(taper))  # opp/adj
    # # We have two XY offsets from base_face - one at the bottom where the case
    # # should start (unknown), and one where the pcb starts (wall_xy_bottom_tolerance).
    case_bottom_offset = T * cfg["z_space_under_pcb"]
    bottom_offset = -case_bottom_offset + cfg["wall_xy_bottom_tolerance"]
    bottom_face = offset(base_face, bottom_offset).face()
    # bottom_face = _fix_face_edges(bottom_face)
    try:
        case_inner_cutout = extrude(bottom_face, amount=total_wall_height, taper=-taper)
    except (OCP.StdFail.StdFail_NotDone, ValueError):
        print(
            "Error: This SVG outline has too many small edges to do a friction fit cutout. Try reducing the top and bottom tolerances, reducing the wall height, or simplyfing the input SVG paths."
        )
        raise

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


def _finger_cutout(location, rotation, thickness, width, height):
    if fast_render:
        return Part()
    # Mutliplying x and y by ~2 because we're centering it on those axis, but
    # only cutting out of one side.
    # Centering because sometimes depending on the wire we get the location
    # from, it'll be flipped, so we can't just align to MAX.
    cutout_box = Box(
        width,
        # 2.1 to get some overlap, since we're centering
        thickness * 2.1,
        height * 2,
    )
    # Smooth the sides of the cutout
    cutout_box = fillet(
        cutout_box.edges().filter_by(Axis.Y), min(height / 2.1, width / 2.1)
    )
    # Smooth the wide sides too, just in case this is cutting out a corner (e.g. for ferris)
    cutout_box = fillet(
        cutout_box.edges().filter_by(Axis.X), min(height / 2.1, thickness / 2.1)
    )

    cutout_box = cutout_box.rotate(Axis.Z, rotation)
    cutout_box.position = location.position
    return cutout_box


def _magnet_cutout(main_face, angle, carrycase=False):
    if fast_render:
        return Part()
    assert (
        cfg["wall_xy_thickness"] - cfg["magnet_separation_distance"] >= magnet_height
    ), "Your wall thickness is too small for the magnets to fit."
    # Ellipse rather than circle to add a extra space at the top of the magnet radius, so that we can print
    # magnet holes without supports and account for the resulting droop.
    hole = (
        Plane.XZ
        * Ellipse(
            # A tiny bit bigger X than the radius to give fit tolerance. Doensn't need to be a super snug fit, since they'll be held in place by glue or the pcb.
            x_radius=magnet_radius + misc_tol / 2,
            y_radius=magnet_radius_y,
        ).face()
    )

    if carrycase:
        distance = (
            cfg["wall_xy_thickness"]
            + cfg["carrycase_tolerance_xy"]
            + magnet_height
            + 0.1
        )
    else:
        # Distance into main wall of case
        distance = cfg["wall_xy_thickness"] - cfg["magnet_separation_distance"]
    # Extend into the case too to ensure no overlap, e.g. due to taper
    # Need it to be centered on X axis so when it is positioned and rotated, it doesn't matter if it is 180 degrees backwards (which might happen on a flipped wire.)
    template = extrude(hole, distance)
    template += extrude(hole, -distance)
    # if not carrycase:
    #     template += extrude(hole, -(magnet_height))

    # Get second largest face parallel to XY plane - i.e., the inner case face
    # inner_case_face = sorted(case.faces().filter_by(Plane.XY), key=lambda x: x.area)[-2]
    inner_wire = main_face.wire()
    _, _, center_percent = _wire_location_at_angle(
        inner_wire, angle, origin=main_face.center()
    )
    center_at_mm = center_percent * inner_wire.length
    span = (cfg["magnet_count"] - 1) * cfg["magnet_spacing"]
    start = center_at_mm - span / 2

    cutouts = []
    position = start
    for _ in range(cfg["magnet_count"]):
        cutout = copy.copy(template)
        location = inner_wire.location_at(position, position_mode=PositionMode.LENGTH)
        # Rotation on wire can be tricky to get right, and may flip depending on the location on the wire.
        # All we know is that the wire's Z orientation is the wire tangent.
        rotation = inner_wire.tangent_angle_at(
            position, position_mode=PositionMode.LENGTH
        )
        # If the wire has flipped,
        # towards_center = Axis(origin=main_face.center(), edge=Line(main_face.center(), location.position).edge())

        cutout = cutout.rotate(Axis.Z, rotation)
        cutout.position = location.position
        # Add 0.01 to avoid overlap issue cutting into base slightly. Float error?
        cutout.position += (0, 0, magnet_radius_y + cfg["base_z_thickness"] + 0.01)
        cutouts.append(cutout)
        # show_object(cutout, f"magnet_cutout_{position}")
        position += cfg["magnet_spacing"]

    # show_object(cutouts, name=f"magnet_cutouts_{carrycase}", options={"alpha": 0.8})
    return cutouts


def _lip(base_face, carrycase=False):
    # Use same z len as total lip xy len so that chamfer is complete.
    lip_xy_len = cfg["lip_len"]
    lip_z_len = cfg["lip_len"] + cfg["carrycase_tolerance_xy"]
    if not carrycase:
        # A little extra tolerance for lip cutout so that it fits more
        # smoothly, even with a bit of residual support plastic or warping.
        lip_xy_len += 0.3
        lip_z_len += 0.3
    # Inner face of carrycase
    inner_face = offset(
        base_face, cfg["wall_xy_thickness"] + cfg["carrycase_tolerance_xy"]
    )
    # Outer is the full carrycase outer face
    outer_face = offset(
        inner_face,
        cfg["carrycase_wall_xy_thickness"]
        # minus chamfer to avoid interfering/drawing over it.
        - cfg["chamfer_len"],
    )
    case_outer_face = offset(base_face, cfg["wall_xy_thickness"])
    cutout_face = offset(base_face, cfg["wall_xy_thickness"] - lip_xy_len)
    # # Offsetting on wires rather than faces seems to help fix OCP edge issues
    # cutout_face = make_face(offset(base_face.face().outer_wire(), cfg["wall_xy_thickness"] - lip_xy_len))
    lip = outer_face - cutout_face

    # Intersect lip with sector/triangle between the two angles.
    bounds = case_outer_face.bounding_box()
    bound_max = max(bounds.size.X, bounds.size.Y) * 2
    boundary_lines = [
        PolarLine(base_face.center(), bound_max, cfg["lip_position_angles"][0]),
        PolarLine(base_face.center(), bound_max, cfg["lip_position_angles"][1]),
    ]
    lip_boundary = make_face(
        [*boundary_lines, Line(boundary_lines[0] @ 1, boundary_lines[1] @ 1)]
    )
    lip = lip.intersect(lip_boundary)

    lip = extrude(lip.face(), lip_z_len)

    if cfg["flush_carrycase_lip"]:
        # Poor man's chamfer of inner edge of lip
        # No point doing it with non-flush lip, because it would reduce the
        # catching surface.
        try:
            # cutout_face = _fix_face_edges(cutout_face.face())
            chamfer_cutout = extrude(cutout_face, lip_z_len, taper=-45)
            lip -= chamfer_cutout
        except OCP.StdFail.StdFail_NotDone:
            print(
                "Warning: Failed to chamfer carrycase lip; cutout will need supports and a higher tolerance"
            )
    else:
        lip.move(Loc((0, 0, -lip_z_len)))

    # show_object(lip, name="lip", options={"alpha": 0.8})
    return lip


def _strap_loop(base_face, case_height):
    """Create a loop for attaching a strap to the left side of the case."""
    outer_face = offset(base_face, cfg["wall_xy_thickness"])
    # Find the leftmost edge of the case
    bb = outer_face.bounding_box()
    end_range_size = 0.1
    case_end_range = Rectangle(
        end_range_size, bb.size.Y, align=(Align.MIN, Align.CENTER)
    ).located(Loc((bb.min.X, bb.center().Y)))
    case_end_face = case_end_range.intersect(outer_face)
    case_end = case_end_face.bounding_box()

    # How much ends of loop are pulled in from the case end (useful for
    # avoiding or merging with rounded corners)
    end_inset = cfg["strap_loop_end_offset"]
    loop_gap_size = cfg["strap_loop_gap"]
    loop_thickness = cfg["strap_loop_thickness"]
    outer_rect_args = {
        "width": loop_gap_size + loop_thickness,
        "height": case_end.size.Y - (2 * end_inset),
        "align": (Align.MAX, Align.CENTER),
    }
    inner_rect_args = copy.copy(outer_rect_args)
    inner_rect_args["width"] -= loop_thickness
    inner_rect_args["height"] -= 2*loop_thickness
    strap_loop = Rectangle(**outer_rect_args) - Rectangle(**inner_rect_args)
    strap_loop = strap_loop.located(Loc(case_end.center())) - outer_face
    strap_loop = extrude(strap_loop, case_height)
    # show_object(strap_loop, name="strap_loop")
    return strap_loop


def _create_honeycomb_tile(depth, face):
    if fast_render:
        return Part()
    radius = cfg["honeycomb_radius"]
    cell_thickness = cfg["honeycomb_thickness"]
    d_between_centers = radius + cell_thickness
    area = face.bounding_box()
    n_hexes = [round(size / d_between_centers) for size in (area.size.X, area.size.Y)]
    locs = HexLocations(d_between_centers, *n_hexes, major_radius=True).local_locations
    h = RegularPolygon(radius, 6)
    h = extrude(h, -depth)
    hs = Plane(face) * locs * h
    return hs


def _tent_hinge(base_face, wall_height):
    """Attach hinge for quick-tenting system to right side of case."""
    try:
        from tenting_stand import case_hinge
    except ImportError:
        from .tenting_stand import case_hinge

    hinge = case_hinge(wall_height, cfg["tent_hinge_bolt_d"], cfg["tent_hinge_bolt_l"])
    reposition = _find_hinge_reposition(base_face, hinge)
    hinge = reposition * hinge
    # hinge = hinge.move(
    #     Loc((params["tent_hinge_position_adjustment"]))
    # )
    return hinge


@cache
def _find_hinge_reposition(base_face, hinge) -> None:
    """Find the Location to move the created hinge or flaps so that it
    perfectly mates with the rightmost side of the case."""
    outer_face = offset(base_face, cfg["wall_xy_thickness"])
    # Find the leftmost edge of the case
    bb = outer_face.bounding_box()
    end_range_size = 1
    case_end_range = Rectangle(
        end_range_size, bb.size.Y, align=(Align.MAX, Align.CENTER)
    ).located(Loc((bb.max.X, bb.center().Y)))
    case_end_face = case_end_range.intersect(outer_face)
    case_end = case_end_face.bounding_box()

    left_hinge_face = hinge.faces().sort_by(Axis.X).first
    bot_hinge_face = hinge.faces().sort_by(Axis.Z).first
    mating_face_X = case_end.max.X - cfg["chamfer_len"] / math.cos(math.radians(44))
    reposition = Loc(
        (
            mating_face_X - left_hinge_face.center().X,
            cfg["tent_hinge_position_offset"],
            -bot_hinge_face.center().Z,
        )
    )
    return reposition


def _cutout_tenting_flaps(case, base_face, wall_height):
    shadow = _get_tenting_flap_shadow(base_face, wall_height)
    shadow = offset(shadow, tent_leg_cutout_tolerance)
    outer_case_face = offset(base_face, cfg["wall_xy_thickness"]).face()
    shadow_within_walls = shadow.intersect(outer_case_face).face()
    # Create plastic outline for flaps to fold into. Only really needed if
    # using honeycomb base, but may as well include it jic. Extra offset for inner cutout to give a bit of tolerance for the flap.
    flap_slot = offset(shadow_within_walls, cfg["wall_xy_thickness"]) - shadow
    flap_slot = extrude(flap_slot, cfg["base_z_thickness"])
    case -= extrude(shadow, cfg["base_z_thickness"])
    case += flap_slot
    return case


@cache
def _get_tenting_flap_shadow(base_face, wall_height):
    # Import it after updating cnf, because it uses the cnf values on import.
    try:
        from tenting_stand import _calc_leg_open_angle, tenting_legs
    except ImportError:
        from .tenting_stand import _calc_leg_open_angle, tenting_legs

    case_len = _calc_case_len(base_face)
    # Avoiding filleting the end is important until b123d fixes the bug
    # preventing rounded faces from projecting to plane successfully. Once that
    # is fixed, change project_to_face to not filter to those faces, and remove
    # the fillet_end parameter from this call chain.
    flaps = tenting_legs(
        cfg["tent_legs"],
        case_len,
        cfg["tent_hinge_bolt_d"],
        wall_height,
        fillet_end=False,
    )

    # Reposition to same place as hinge.
    hinge = _tent_hinge(base_face, wall_height)
    for i, f in enumerate(flaps):
        # Show full generated flaps in rotated/open position, to check blockers
        # and for showcase images.
        show_object(
            flaps[i]
            .rotate(
                Axis.Y,
                -_calc_leg_open_angle(
                    _calc_case_len(base_face), f.bounding_box().size.X - wall_height
                ),
            )
            .move(hinge.location),
            name=f"flap_open_{i}",
            options={"color": (255 - 20 * i, 40 * i, 40 * i)},
        )
        flaps[i] = f.move(hinge.location)
        show_object(
            flaps[i],
            name=f"flap_closed_{i}",
            options={"color": (255 - 20 * i, 40 * i, 40 * i)},
        )

    shadow = _flatten_to_faces(flaps)
    # Ensure we get the outline of the largest face, otherwise might get inversion from little ridge face.
    shadow = make_face(shadow.faces().sort_by(SortBy.AREA).last.outer_wire()).face()
    return shadow


def _calc_case_len(base_face):
    case_len = offset(base_face, cfg["wall_xy_thickness"]).bounding_box().size.X
    if cfg["strap_loop"]:
        case_len += cfg["strap_loop_thickness"] + cfg["strap_loop_gap"]
    return case_len


def _poor_mans_chamfer(shape, size, top=False):
    """Chamfers the bottom or top outer edge of a shape by subtracting a tapered extrusion"""
    faces = shape.faces().sort_by(sort_by=Axis.Z)
    if top:
        face = faces.last
    else:
        face = faces.first
    face = make_face(face.outer_wire()).face()
    if top:
        face = -face
    else:
        face = face
    outer = extrude(face, size)
    inner_f = offset(face, -size).face()
    try:
        inner = extrude(inner_f, size, taper=-44)
    except (OCP.StdFail.StdFail_NotDone, ValueError):
        print(
            "Error: This SVG outline has too many small edges to chamfer the top and bottom. Skipping"
        )
        return shape
    cutout = outer - inner
    out = shape - cutout
    # show_object(inner_f, name="inner_f")
    # show_object(outer, name="outer")
    # show_object(inner, name="inner")
    return out


def _export(shape, path, name):
    path = Path(path).expanduser()
    if test_print:
        git_head_hash = os.popen("git rev-parse HEAD").read().strip()[:6]
        path = path.with_stem(path.stem + "_test_" + git_head_hash)
    print(f"Exporting {name} as {path}...")
    pathstr = str(path)
    if path.suffix == ".stl":
        export_stl(shape, pathstr)
    elif path.suffix == ".step":
        export_step(shape, pathstr)
    else:
        print(f"Invalid export suffix: '{path.suffix}' Must be .stl or .step")


def _flatten_to_faces(shape):
    faces = shape.faces().filter_by(Axis.Z)
    shadow = project(faces, Plane.XY).fuse()
    # Unify the faces and ensure their orientation is all the same.
    with BuildSketch() as bd_s:
        for f in shadow.faces():
            add(f)
    shadow = bd_s.sketch.face()
    return shadow


def _wire_location_at_angle(wire, angle, origin=None):
    """Find the location of a wire at a certail polar angle from the given origin.polar location of a wire relative to a central origin."""
    if not origin:
        origin = wire.center(CenterOf.BOUNDING_BOX)
    # Form a ray in the direction of angle. Has to be a face, because 1D objects currently won't intersect.
    polar_length = wire.bounding_box().diagonal * 2
    projection = PolarLine(origin, polar_length, angle)
    # Ensure ray has thickness regardless of angle.
    ray = make_face(SlotArc(projection, 1.1))
    face = make_face(wire)
    # Sometimes projection has a rotation, so the ray isn't coplanar with the face.
    projected_ax = Axis(origin=origin, edge=projection.edge())
    # Have to do this multiple times to ensure coplanar, for some reason. Floats, presumably.
    while ray.face().normal_at().Z != 1:
        ray_normal = Axis(origin=origin, direction=ray.face().normal_at())
        angle_correction = ray_normal.angle_between(Axis.Z)
        ray = ray.rotate(projected_ax, angle_correction)
    # ensure it isn't upside down
    if ray.face().normal_at().Z < 0.99:
        ray = ray.rotate(projected_ax, 180)
    sect = ray.intersect(face)
    furthest_edge = sect.edges().sort_by(SortBy.DISTANCE)[-1]
    location = furthest_edge ^ 0.5
    tangent = furthest_edge.tangent_angle_at(0.5)
    location_percent = wire.param_at_point(location.position)
    return location, tangent, location_percent


if test_print:
    cfg.update(test_overrides)

# Code for debugging
if __name__ in ["temp", "__cq_main__", "__main__"]:
    p = Path(script_dir / "../preset_outlines/maizeless.svg")
    # p = Path(
    #     "~/src/keyboard_design/maizeless/pcb/build/maizeless-Edge_Cuts gerber.svg"
    # ).expanduser()
    config = Path(script_dir / "../preset_configs/maizeless.json")

    # p = script_dir / "../preset_outlines/ferris.svg"
    # config = Path(script_dir / "../preset_configs/ferris.json")

    import json

    param_overrides = json.loads(config.read_text())
    cfg = default_params
    cfg.update(param_overrides)
    if test_print:
        cfg.update(test_overrides)

    pcb_case_wall_height = cfg["z_space_under_pcb"] + cfg["wall_z_height"]

    base_face = import_svg_as_face(p)
    show_object(base_face, name="base_face")
    # bf = make_face(base_face).face()
    # show_object(bf)

    case = generate_pcb_case(base_face, pcb_case_wall_height)
    carry = generate_carrycase(base_face, pcb_case_wall_height)
