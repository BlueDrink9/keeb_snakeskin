import build123d as bd
from build123d import Align, Rot
from build123d import *
import math

Loc = bd.Location

# TODO:
# * Align multiple magnets
# * Parameterise magnet number? or area, with fixed intervals? But ensure all
# within a certain angle of one another??
# * Change position on wire system to angle system - create a line from center, intersect
# it with the line, and set the location to that intersection.
#
# TODO: Documentation: PositionMode enum: Length is supposed to be actual length like "mm",
# parameter is where the start is zero and end is one.
#
# location_at / ^ symbol, to match % and @
#
# TODO: Testing:
# * Unmirror the carrycase
# * Cut to just the square end
# * test case fit (confident here)
# * test carrycase entry and exit (having to slip it in on an angle will
# require tolerance/stretching in that direction, but I'm not sure how much).

default_params = {
    "base_z_thickness": 30,
    "wall_xy_thickness": 2.5,
    "wall_z_height": 3.4,
    "z_space_under_pcb": 1,
    "wall_xy_bottom_tolerance": -0.3,
    "wall_xy_top_tolerance": 0.3,
    "cutout_position": 0,
    "cutout_width": 15,
    "carrycase": True,
    "carrycase_tolerance": 0.3,
    "carrycase_wall_xy_thickness": 4,
    "carrycase_z_gap_between_cases": 9,
    "carrycase_cutout_position": 0.0,
    "carrycase_cutout_xy_width": 15,
    "lip_z_thickness": 1,
    "lip_position_angles": [160, 30],
    "magnet_position_centre": 0.0,
    "magnet_position_angle": 100.0,
}

magnet_height = 2
magnet_radius = 4 / 2

params = default_params
pcb_case_wall_height = params["z_space_under_pcb"] + params["wall_z_height"]

params["cutout_position"] = 0.97
params["carrycase_cutout_position"] = 0.39
params["z_space_under_pcb"] = 2.4
params["magnet_position_centre"] = 0.37

outline = bd.import_svg("build/outline.svg")
# For testing
# outline = bd.Rectangle(30,80).locate(bd.Location((40, 40, 0)))

# Round trip from outline to wires to face to wires to connect the disconnected
# edges that an svg gets imported with.
outline = bd.make_face(outline.wires()).wires()[0]
base_face = bd.make_face(outline)


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
    shells = ShapeList([Shell(faces) for faces in connected_faces]).sort_by(SortBy.AREA)
    return shells[0].faces()


def generate_pcb_case(base_face, wall_height):
    base = bd.extrude(base_face, params["base_z_thickness"])
    wall_outer = bd.offset(
        base_face,
        params["wall_xy_thickness"],
    )

    # calculate taper angle. tan(x) = o/a
    opp = -params["wall_xy_bottom_tolerance"] + params["wall_xy_top_tolerance"]
    adj = wall_height
    taper = math.degrees(math.atan(opp / adj))

    inner_cutout = bd.extrude(base_face, wall_height, taper=-taper)
    inner_cutout.move(Loc((0, 0, params["base_z_thickness"])))
    # show_object(inner_cutout, name="inner")
    wall = (
        bd.extrude(wall_outer, wall_height + params["base_z_thickness"]) - inner_cutout
    )
    case = wall + base

    # Create finger cutout
    topf = case.faces().sort_by(sort_by=bd.Axis.Z).last
    top_inner_wire = topf.wires()[0]
    cutout_location = top_inner_wire ^ params["cutout_position"]
    cutout_box = __finger_cutout(
        cutout_location,
        params["wall_xy_thickness"],
        params["cutout_width"],
        pcb_case_wall_height,
    )

    case = case - cutout_box

    # Cut out a lip for the carrycase
    if params["carrycase"]:
        case -= __lip(base_face)

    show_object(case, name="case")
    return case


def generate_carrycase(base_face, pcb_case_wall_height):
    cutout_outline = bd.offset(
        base_face, params["wall_xy_thickness"] + params["carrycase_tolerance"]
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

    # Part that blocks the pcb case from going all the way through
    blocker_face = bd.offset(base_face, params["wall_xy_thickness"]) - base_face
    # Locate the blocker at the top of the pcb case wall
    blocker = bd.extrude(blocker_face, amount=2).moved(
        Loc((0, 0, wall_height - params["carrycase_z_gap_between_cases"]))
    )

    case = wall + blocker

    # Add lip to hold board in
    case += __lip(base_face)

    # Create finger cutout for removing boards
    botf = case.faces().sort_by(sort_by=bd.Axis.Z).first
    bottom_inner_wire = botf.wires()[0]
    cutout_location = bottom_inner_wire ^ params["carrycase_cutout_position"]
    cutout_box = __finger_cutout(
        cutout_location,
        params["carrycase_wall_xy_thickness"],
        params["carrycase_cutout_xy_width"],
        (pcb_case_wall_height + params["base_z_thickness"]) - magnet_height - 1,
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
    ).located(cutout_location)
    return cutout_box


def __magnet_cutout(angle):
    hole = (
        bd.Plane.XY
        * bd.Circle(
            radius=magnet_radius,
        )
    )
    # Add a little extra to the height to ensure there is space for the pcb to slide past the
    # board hole
    cutout = bd.extrude(hole, magnet_height + 0.1)
    # Get second largest face parallel to XY plane - i.e., the inner case face
    inner_case_face = sorted(case.faces().filter_by(bd.Plane.XY), key=lambda x: x.area)[-2]
    inner_wire = inner_case_face.wires()[0]
    # magnet_start = inner_wire ^ position
    # cutout.orientation = magnet_start.orientation
    # cutout = cutout.rotate(bd.Axis.Z, -90)
    # cutout.position = magnet_start.position
    # cutout.position += (0, 0, magnet_radius)
    # return cutout
    # Calculate the direction vector based on the specified angle
    direction = bd.Vector(math.cos(math.radians(angle)), math.sin(math.radians(angle)), 0)

    # Project a line from the center of the face along the specified angle
    face_center = inner_case_face.center()
    line = bd.Axis(face_center, direction)
    show_object(bd.Line(face_center, direction * 1000), name="line")
    # show_object(inner_wire, name="inner_wire")
    return cutout



    # Find the intersection point between the line and the wire
    intersection = inner_wire.edges().sort_by(line)[-1]
    show_object(intersection, "edge")
    # .intersect(line)

    # if intersection:
    #     magnet_start = intersection[0]
    #     cutout.orientation = magnet_start.orientation
    #     cutout = cutout.rotate(bd.Axis.Z, -90)
    #     cutout.position = magnet_start.position
    #     cutout.position += (0, 0, magnet_radius)
    #     return cutout
    # # else:
    # #     print("No intersection found between the line and the wire.")
    # #     return None
    #
def __lip(base_face):
    lip = bd.offset(base_face, params["wall_xy_thickness"] + params["carrycase_tolerance"]) - base_face
    lip = lip.intersect(__arc_sector_ray(base_face, params["lip_position_angles"][0], params["lip_position_angles"][1]))
    lip = bd.extrude(lip, params["lip_z_thickness"])
    # show_object(lip, name="lip")
    return lip


def __arc_sector_ray(obj, angle1, angle2):
    triangle = bd.Triangle(
        A=abs(angle1 - angle2),
        b=500,
        c=500,
        align=[Align.CENTER, Align.MAX],
    )
    rotation_angle = (angle1 + angle2) / 2
    location = Loc(obj.center()) * Rot(Z=90) * Rot(Z=rotation_angle)
    triangle.location = location
    return triangle


class Sector(bd.Shape):
    """Sector of a circle with tip at location, between angle1 and angle2 in degrees, where 0 is the X axis and -90 is the negative Y axis."""
    def __init__(self, radius, angle1, angle2, location=(0,0)):
        return (
            bd.Plane('XY')
            .ThreePointArc(radius, radius, angle1, angle2, startAtCurrent=False)
            .lineTo(0,0)
            .close()
        ).located(Loc(location))

# show_object(Sector(100, 0, 45), "sector")

#
# if __name__ in ["__cq_main__", "temp"]:
#     # For testing via cq-editor
#     pass
#     # object = generate_case("build/outline.svg")
#     # show_object(object)
#     case = generate_pcb_case(base_face, pcb_case_wall_height)
#
#     # if params["carrycase"]:
#     #     carry = generate_carrycase(base_face, pcb_case_wall_height)
#
#
# cutout_outline = bd.offset(
#     base_face, params["wall_xy_thickness"] + params["carrycase_tolerance"]
# )
# wall_outline = bd.offset(cutout_outline, params["carrycase_wall_xy_thickness"])
# wall_outline -= cutout_outline
#
# wall_height = params["base_z_thickness"] + params["carrycase_z_gap_between_cases"]
# wall = bd.extrude(wall_outline, wall_height)
# # cutout = bd.extrude(cutout_outline, wall_height)
#
# base = bd.extrude(base_face, params["base_z_thickness"])
# wall_outer = bd.offset(
#     base_face,
#     params["wall_xy_thickness"],
# )
#
#
# # shape = vert_faces.filter_by(lambda x: bd.Shape.closest_points(vert_faces[0], inner_wires)==0)
# # cutout = __magnet_cutout(params["magnet_position_centre"])
# cutout = __magnet_cutout(params["magnet_position_angle"])
# show_object(cutout, name="magnet cutout")
# angle = params["magnet_position_angle"]
# hole = (
#     bd.Plane.XY
#     * bd.Circle(
#         radius=magnet_radius,
#     )
# )
# # Add a little extra to the height to ensure there is space for the pcb to slide past the
# # board hole
# cutout = bd.extrude(hole, magnet_height + 0.1)
# # Get second largest face parallel to XY plane - i.e., the inner case face
# inner_case_face = sorted(case.faces().filter_by(bd.Plane.XY), key=lambda x: x.area)[-2]
# inner_wire = inner_case_face.wires()[0]
# # magnet_start = inner_wire ^ position
# # cutout.orientation = magnet_start.orientation
# # cutout = cutout.rotate(bd.Axis.Z, -90)
# # cutout.position = magnet_start.position
# # cutout.position += (0, 0, magnet_radius)
# # return cutout
# # Calculate the direction vector based on the specified angle
# direction = bd.Vector(math.cos(math.radians(angle)), math.sin(math.radians(angle)), 0)
# show_object(inner_case_face, name="inner_case_face")
#
# # Project a line from the center of the face along the specified angle
# face_center = inner_case_face.center()
# line = bd.Plane(inner_case_face).shift_origin(face_center) * bd.PolarLine(
#     start=0, length=1000, angle=angle
# )
# ax = bd.Axis(bd.Wire(line).edge())
# show_object(line, name="line")
# target_face = case.faces().sort_by(ax)
# show_object(target_face[-1], name="face")
# # p = bd.Plane.XZ * bd.Rot((0, angle, 0))
# # p.origin = face_center
# # p = p * bd.Rectangle(500, 10)
# # show_object(inner_wire, name="inner_wire")
# # show_object(p, name="p")
#
#
# # Find the intersection point between the line and the wire
# target_line = inner_wire.fix_degenerate_edges(30).edges().sort_by(ax)[-1]
# show_object(target_line, "target_line")
# dir = line.orientation.normalized()
# # bd.IntersectingLine(face_center, dir, target_line)
# # i = p.intersect(intersection)
# # show_object(i.children[0], name="i")
# # intersection.intersect(line)

# TODO: Instead of wire, create a wall to intersect with. See if that works
# bett.r Make the wall same height as wall, get center of intersection,
# hopefuly that works. Hmph

#
# # Minimum test examples
# angle = 45
# f = bd.Rot(13,15,12) * bd.Pos(9, 7, 5) * bd.Box(40, 30, 10).faces()[0]
# show_object(f, name="face")
# face_center = f.center()
# line = bd.Plane(f).shift_origin(face_center) * bd.PolarLine(
#     start=0, length=1000, angle=angle
# )
# show_object(line, name="line")
# ax = bd.Axis(bd.Wire(line).edge())
# target_edge = f.edges().sort_by(ax)[-1]
# show_object(target_edge, name="target_edge")
#
# new_f = bd.extrude(f.offset(0.1), 10)
# # show_object(new_f, name="target_faces")
# int_fs = new_f.find_intersection(ax)
# # show_object(int_fs, name="intersected faces")
# # show_object(f.wires()[0], name="wire")
# # i = bd.IntersectingLine(start=face_center, direction=(1, 1), other=f.wires()[0])
# # show_object(i, name="intersected line")
#
# f = bd.Pos(12, 12, 12) * bd.Rectangle(10, 10)
# show_object(f, name="face")
# face_center = f.center()
# plane = bd.Plane(f.faces()[0])
# l = plane * bd.Line(-10, 10)
# show_object(l, name="line")
# # Not coplanar!?
# # i = bd.IntersectingLine(start=plane.origin, direction=(1, 1), other=plane * f.wires()[0])
# # show_object(i, name="intersected line")

# # Creating a 'catcher' rectangle to intersect with the line/face
# f = bd.Pos(12, 12, 12) * bd.Rectangle(10, 10)
# wall_c = f.edges()[0].center()
# new_plane = bd.Plane(f, origin = wall_c, y_dir=f.face().normal_at(), z_dir = 1)
# catcher = new_plane * bd.Rectangle(10, 10, align=Align.CENTER)
# show_object(catcher, name="catcher")
# f.position -= (1,0,0)
# show_object(f, name="f")
# i = catcher.intersect(f)
# print(len(i.children)) # 0
