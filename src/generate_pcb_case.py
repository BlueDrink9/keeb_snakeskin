import build123d as bd
from build123d import *
import math
loc = bd.Location

default_params = {
    "base_z_thickness": 3,
    "wall_xy_thickness": 2,
    "wall_z_height": 1.6,
    "z_space_under_pcb": 1.6,
    "wall_xy_bottom_tolerance": -0.3,
    "wall_xy_top_tolerance": 0.3,
    "cutout_angle": 0,
    "cutout_width": 5,
    "carrycase_tolerance": 0.3,
    "carrycase_wall_xy_thickness": 4,
    "carrycase_z_gap_between_pcbs": 11,
    "carrycase_cutout_angle": 0,
    "carrycase_cutout_width": 5,
}

magnet_height = 2
magnet_radius = 4/2

params = default_params

outline = bd.import_svg("build/outline.svg")

# For testing
outline = bd.Rectangle(30,80).locate(bd.Location((40, 40, 0)))

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
        params["carrycase_z_gap_between_pcbs"]
)
wall = bd.extrude(wall_outline, wall_height)
# cutout = bd.extrude(cutout_outline, wall_height)

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

def generate_carrycase(base_face, pcb_case_wall_height):
    cutout_outline = bd.offset(base_face,
                            params["wall_xy_thickness"] +
                            params["carrycase_tolerance"]
                            )
    wall_outline = bd.offset(cutout_outline, params["carrycase_wall_xy_thickness"])
    wall_outline -= cutout_outline

    wall_height = (
        params["base_z_thickness"] +
            params["carrycase_z_gap_between_pcbs"]
    )
    wall = bd.extrude(wall_outline, wall_height)
    # cutout = bd.extrude(cutout_outline, wall_height)

    # Part that blocks the pcb case from going all the way through
    blocker = bd.offset(base_face, params["wall_xy_thickness"]) - base_face
    blocker = bd.extrude(blocker, amount=2).moved(loc((0,0,pcb_case_wall_height)))

    case = wall + blocker

    # Mirror on top face to create both sides
    topf = case.faces().sort_by(sort_by=bd.Axis.Z).last
    case += bd.mirror(case, about=bd.Plane(topf))
    show_object(case, name="carry case")
    return case

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
    # show_object(case, name="case")
    return case


def generate_cases(svg_file, params=None):
    if not params:
        params = {} 
    default_params.update(params)
    params = default_params

    outline = bd.import_svg(svg_file)
    return

if __name__ in ["__cq_main__", "temp"]:
    # For testing via cq-editor
    pass
    # object = generate_case("build/outline.svg")
    # show_object(object)
    # object = generate_pcb_case(base_face, pcb_case_wall_height)
    # object = generate_carrycase(base_face, pcb_case_wall_height)
    # show_object(object)
