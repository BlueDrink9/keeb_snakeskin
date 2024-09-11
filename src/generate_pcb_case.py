import build123d as bd
from build123d import Align, Rot
from build123d import *
import math
from collections import defaultdict

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
    "base_z_thickness": 3,
    "wall_xy_thickness": 2.5,
    "wall_z_height": 3.4,
    "z_space_under_pcb": 1,
    "wall_xy_bottom_tolerance": -0.3,
    "wall_xy_top_tolerance": 0.3,
    "cutout_position": 10,
    "cutout_width": 15,
    "carrycase": True,
    "carrycase_tolerance": 0.3,
    "carrycase_wall_xy_thickness": 4,
    "carrycase_z_gap_between_cases": 9,
    "carrycase_cutout_position": -90,
    "carrycase_cutout_xy_width": 15,
    "lip_z_thickness": 1,
    "lip_position_angles": [160, 30],
    "magnet_position_centre": 0.0,
    "magnet_position_angle": 100.0,
}

magnet_height = 2
magnet_radius = 4 / 2

polar_position_maps = defaultdict(dict)

params = default_params # TODO: merge this with user params
pcb_case_wall_height = params["z_space_under_pcb"] + params["wall_z_height"]

params["cutout_position"] = 32
params["carrycase_cutout_position"] = -108
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
    _map_polar_locations(top_inner_wire, topf.center())
    cutout_location = _get_polar_location(top_inner_wire, params["cutout_position"])
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
    _map_polar_locations(bottom_inner_wire, botf.center())
    cutout_location = _get_polar_location(bottom_inner_wire, params["carrycase_cutout_position"])
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


def _map_polar_locations(wire, origin):
    n_angles = 360
    at_position = 0
    iter = 1/n_angles
    while at_position <= 1:
        location = wire ^ at_position
        at_position += iter
        ax1 = bd.Axis.X
        ax2 = bd.Wire(bd.Line(origin, location.position)).edge()
        ax2 = bd.Axis(edge = ax2)
        angle = round(ax1.angle_between(ax2))
        if ax2.direction.Y < 0:
            # Angle between gives up to 180 as a positive value, so we need to
            # flip it for -ve angles.
            angle = -angle
        polar_position_maps[id(wire)][angle] = at_position


def _get_polar_location(wire, angle):
    try:
        map = polar_position_maps[id(wire)]
    except KeyError:
        print("Wire not yet mapped, this is a dev error")
        raise
    angle = _find_nearest_key(map, angle)
    return wire ^ map[angle]


def _find_nearest_key(d, target_int):
    nearest = min(d, key=lambda x: abs(x - target_int))
    return nearest

class Sector(bd.Shape):
    """Sector of a circle with tip at location, between angle1 and angle2 in degrees, where 0 is the X axis and -90 is the negative Y axis."""
    def __init__(self, radius, angle1, angle2, location=(0,0)):
        return (
            bd.Plane('XY')
            .ThreePointArc(radius, radius, angle1, angle2, startAtCurrent=False)
            .lineTo(0,0)
            .close()
        ).located(Loc(location))
    # JernArc(start, startTangent, radius, angle) is altenrative

# show_object(Sector(100, 0, 45), "sector")


if __name__ in ["__cq_main__", "temp"]:
    # For testing via cq-editor
    pass
    # object = generate_case("build/outline.svg")
    # show_object(object)
    # case = generate_pcb_case(base_face, pcb_case_wall_height)

    if params["carrycase"]:
        carry = generate_carrycase(base_face, pcb_case_wall_height)
