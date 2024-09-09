import build123d as bd
from build123d import *
import math
loc = bd.Location

# TODO: Documentation: PositionMode enum: Length is supposed to be actual length like "mm",
# parameter is where the start is zero and end is one.
#
# location_at / ^ symbol, to match % and @

default_params = {
    "base_z_thickness": 3,
    "wall_xy_thickness": 2,
    "wall_z_height": 1.6,
    "z_space_under_pcb": 1,
    "wall_xy_bottom_tolerance": -0.3,
    "wall_xy_top_tolerance": 0.3,
    "cutout_position": 0,
    "cutout_width": 15,
    "carrycase_tolerance": 0.3,
    "carrycase_wall_xy_thickness": 4,
    "carrycase_z_gap_between_cases": 11,
    "carrycase_cutout_position": 0.0,
    "carrycase_cutout_width": 15,
}

magnet_height = 2
magnet_radius = 4/2

params = default_params
params["cutout_position"] = 0.97
params["carrycase_cutout_position"] = 0.89
params["z_space_under_pcb"] = 2.4

outline = bd.import_svg("build/outline.svg")

# For testing
# outline = bd.Rectangle(30,80).locate(bd.Location((40, 40, 0)))

# Round trip from outline to wires to face to wires to connect the disconnected
# edges that an svg gets imported with.
outline = bd.make_face(outline.wires()).wires()[0]
base_face = bd.make_face(outline)


pcb_case_wall_height = params["z_space_under_pcb"] +  \
    params["wall_z_height"]

cutout_outline = bd.offset(base_face,
                        params["wall_xy_thickness"] +
                        params["carrycase_tolerance"]
                        )
wall_outline = bd.offset(cutout_outline, params["carrycase_wall_xy_thickness"])
wall_outline -= cutout_outline

wall_height = (
    params["base_z_thickness"] +
        params["carrycase_z_gap_between_cases"]
)
wall = bd.extrude(wall_outline, wall_height)
# cutout = bd.extrude(cutout_outline, wall_height)

base = bd.extrude(base_face, params["base_z_thickness"])
wall_outer = bd.offset(
    base_face,
    params["wall_xy_thickness"],
)


hole_cutout = bd.Plane.XY * bd.Rot(0,90,0) * bd.Cylinder(
    radius=magnet_radius,
    height=magnet_height*2 + params["carrycase_tolerance"]
)
hole_cutouts = hole_cutout
# hole_cutouts = inner_face
# show_object(wall.edges().sort_by(bd.SortBy.LENGTH)[-1])

show_object(hole_cutouts, name="magnets")

def is_wire_for_face(face, wire):
    inter = face.intersect(wire)
    try:
        # If they intersect, this returns a Vector. If they don't, it throughs
        # an AttributeError about compound not having IsNull
        inter.center()
        return True
    except AttributeError:
        return False


def get_inner_faces(aligned_faces):
    """Gets the innermost face of a series of concentric faces"""
    connected_faces = Face.sew_faces(aligned_faces)
    # Which is "inside" - sort by Shell area
    shells = ShapeList([Shell(faces) for faces in
        connected_faces]).sort_by(
        SortBy.AREA
    )
    return shells[0].faces()
# inner_faces = vert_faces.filter_by(lambda x: is_wire_for_face(x, inner_wire))

vert_faces = wall.faces().filter_by(Axis.Z, reverse=True)
inner_faces = get_inner_faces(vert_faces)
f = inner_faces
shape = f
show_object(shape, name="shape")

# shape = vert_faces.filter_by(lambda x: bd.Shape.closest_points(vert_faces[0], inner_wires)==0)

def generate_pcb_case(base_face, wall_height):
    base = bd.extrude(base_face, params["base_z_thickness"])
    wall_outer = bd.offset(
        base_face,
        params["wall_xy_thickness"],
    )

    # calculate taper angle. tan(x) = o/a
    opp = -params["wall_xy_bottom_tolerance"] + params["wall_xy_top_tolerance"]
    adj = wall_height
    taper = math.degrees(math.atan(opp/adj))

    inner_cutout = bd.extrude(base_face, wall_height, taper=-taper)
    inner_cutout.move(loc((0,0,params["base_z_thickness"])))
    # show_object(inner_cutout, name="inner")
    wall = bd.extrude(wall_outer, wall_height + params["base_z_thickness"]) - inner_cutout
    case = wall + base

    # Create finger cutout
    topf = case.faces().sort_by(sort_by=bd.Axis.Z).last
    top_inner_wire = topf.wires()[0]
    cutout_location = top_inner_wire ^ params["cutout_position"]
    cutout_box = __finger_cutout(cutout_location, params["wall_xy_thickness"], params["cutout_width"], pcb_case_wall_height)


    case = case - cutout_box
    show_object(case, name="case")
    return case


def generate_carrycase(base_face, pcb_case_wall_height):
    cutout_outline = bd.offset(base_face,
                            params["wall_xy_thickness"] +
                            params["carrycase_tolerance"]
                            )
    wall_outline = bd.offset(cutout_outline, params["carrycase_wall_xy_thickness"])
    wall_outline -= cutout_outline

    wall_height = (
        pcb_case_wall_height +
            params["base_z_thickness"] +
            params["carrycase_z_gap_between_cases"]
    )
    wall = bd.extrude(wall_outline, wall_height)
    # cutout = bd.extrude(cutout_outline, wall_height)

    # Part that blocks the pcb case from going all the way through
    blocker_face = bd.offset(base_face, params["wall_xy_thickness"]) - base_face
    # Locate the blocker at the top of the pcb case wall
    blocker = bd.extrude(blocker_face, amount=2).moved(
        loc((0,0,wall_height - params["carrycase_z_gap_between_cases"])))

    case = wall + blocker

    # Create finger cutout for removing boards
    botf = case.faces().sort_by(sort_by=bd.Axis.Z).first
    bottom_inner_wire = botf.wires()[0]
    cutout_location = bottom_inner_wire ^ params["carrycase_cutout_position"]
    cutout_box = __finger_cutout(
        cutout_location,
        params["carrycase_wall_xy_thickness"],
        params["carrycase_cutout_width"],
        pcb_case_wall_height + params["base_z_thickness"],
    )
    # show_object(cutout_box, name="carry case cutout box")

    case -= cutout_box

    # Mirror on top face to create both sides
    topf = case.faces().sort_by(sort_by=bd.Axis.Z).last
    case += bd.mirror(case, about=bd.Plane(topf))
    show_object(case, name="carry case")
    return case


def generate_cases(svg_file, params=None):
    if not params:
        params = {}
    default_params.update(params)
    params = default_params

    outline = bd.import_svg(svg_file)
    return


def __finger_cutout(location, thickness, width, height):
    cutout_location = location * bd.Rot(X=-90)
    # Mutliplying x and y by ~2 because we're centering it on those axis, but
    # only cutting out of one side.
    # Centering because sometimes depending on the wire we get the location
    # from, it'll be flipped, so we can't just align to MAX.
    cutout_box = bd.Box(
        # 2.1 to get some overlap
        thickness*2.1,
        width,
        height * 2,
    ).located(cutout_location)
    return cutout_box


if __name__ in ["__cq_main__", "temp"]:
    # For testing via cq-editor
    pass
    # object = generate_case("build/outline.svg")
    # show_object(object)
    case = generate_pcb_case(base_face, pcb_case_wall_height)
    carry = generate_carrycase(base_face, pcb_case_wall_height)
