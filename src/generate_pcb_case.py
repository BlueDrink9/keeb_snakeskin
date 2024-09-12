import copy
import math
import os
from collections import defaultdict
from pathlib import Path
import build123d as bd
from build123d import Align, Rot
from build123d import *

Loc = bd.Location
if "__file__" in globals():
    script_dir = Path(__file__).parent
else:
    script_dir = Path(os.getcwd())

# TODO:
# * reduce overhangs. Chamfer carrycase blocker X nvm, this is going to be too
# hard with current version.
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
    "wall_z_height": 4.0,
    "z_space_under_pcb": 1,
    "wall_xy_bottom_tolerance": -0.3,
    "wall_xy_top_tolerance": 0.3,
    "cutout_position": 10,
    "cutout_width": 15,
    "honeycomb_base": False,
    "honeycomb_radius": 6,
    "honeycomb_thickness": 2,
    "carrycase": True,
    "carrycase_tolerance": 0.3,
    "carrycase_wall_xy_thickness": 4,
    "carrycase_z_gap_between_cases": 9,
    "carrycase_cutout_position": -90,
    "carrycase_cutout_xy_width": 15,
    "lip_z_thickness": 1,
    "lip_position_angles": [160, 30],
    "magnet_position": -90.0,
    "magnet_separation_distance": 0.4,
    "magnet_spacing": 12,
    "magnet_count": 6,
}

magnet_height = 2
# Adding a bit of extra space around the radius, so that we can print magnet
# holes without supports and account for the resulting droop.
magnet_radius = 4 / 2 + 0.3

polar_position_maps = defaultdict(dict)

slice = Loc((30, 0, 0)) * bd.Box(300, 300, 200, align=(Align.MIN, Align.CENTER, Align.CENTER))

params = default_params # TODO: merge this with user params
pcb_case_wall_height = params["z_space_under_pcb"] + params["wall_z_height"]

params["cutout_position"] = 32
params["carrycase_cutout_position"] = -108
params["z_space_under_pcb"] = 2.4
params["magnet_position"] = -132
params["honeycomb_base"] = True

outline = bd.import_svg(script_dir / "build/outline.svg")
# For testing
# outline = bd.Rectangle(30,80).locate(bd.Location((40, 40, 0)))

# Round trip from outline to wires to face to wires to connect the disconnected
# edges that an svg gets imported with.
outline = bd.make_face(outline.wires()).wire().fix_degenerate_edges(0.01)
base_face = bd.make_face(outline)
# show_object(base_face, name="base_face")


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

    # inner_face = bd.offset(base_face, -params["wall_xy_bottom_tolerance"])
    # Seem to only be able to offset the bottom a small amount before freezing
    # things... might not be worth the risk.
    # inner_face = bd.offset(base_face, -0.05)
    inner_face = base_face
    inner_cutout = bd.extrude(inner_face, wall_height, taper=-taper)
    inner_cutout.move(Loc((0, 0, params["base_z_thickness"])))
    # show_object(inner_cutout, name="inner")
    wall = (
        bd.extrude(wall_outer, wall_height + params["base_z_thickness"]) - inner_cutout - base
    )

    if params["honeycomb_base"]:
        # Create honeycomb by subtracting it from the top face of the base.
        hc = _create_honeycomb_tile(
            params["base_z_thickness"], base.faces().sort_by(bd.Axis.Z).last
        )
        base -= hc

    case = wall + base

    # Create finger cutout
    topf = case.faces().sort_by(sort_by=bd.Axis.Z).last
    top_inner_wire = topf.wires()[0]
    polar_map = PolarWireMap(top_inner_wire, topf.center())
    cutout_location, _ = polar_map.get_polar_location(params["cutout_position"])
    cutout_box = __finger_cutout(
        cutout_location,
        params["wall_xy_thickness"],
        params["cutout_width"],
        pcb_case_wall_height,
    )

    case = case - cutout_box

    if params["carrycase"]:
        # Cut out a lip for the carrycase
        case -= __lip(base_face)
        # Cut out magnet holes
        case -= _magnet_cutout(base_face, params["magnet_position"])

    # For test prints
    # case -= slice

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
    blocker_thickness = 2
    base_blocker_face = bd.offset(
        base_face, (params["wall_xy_thickness"] + params["carrycase_tolerance"])
    )
    blocker_face = base_blocker_face - base_face
    blocker = bd.extrude(blocker_face, amount=blocker_thickness)
    # Locate the blocker at the top of the pcb case wall
    blocker.move(
        Loc((0, 0, (wall_height - params["carrycase_z_gap_between_cases"])))
    )
    case = wall + blocker

    # Add lip to hold board in
    case += __lip(base_face)

    # Create finger cutout for removing boards
    botf = case.faces().sort_by(sort_by=bd.Axis.Z).first
    bottom_inner_wire = botf.wires()[0]
    polar_map = PolarWireMap(bottom_inner_wire, botf.center())
    cutout_location, _ = polar_map.get_polar_location(params["carrycase_cutout_position"])
    cutout_box = __finger_cutout(
        cutout_location,
        params["carrycase_wall_xy_thickness"],
        params["carrycase_cutout_xy_width"],
        pcb_case_wall_height - magnet_height - 0.3,
    )
    # show_object(cutout_box, name="carry case cutout box")

    case -= cutout_box

    case -= _magnet_cutout(cutout_outline, params["magnet_position"])

    # For test prints
    # case -= slice

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
    )
    # Smooth the sides of the cutout
    cutout_box = bd.fillet(
        cutout_box.edges()
        .filter_by(bd.Axis.X)
        , height/2
    )
    cutout_box.locate(cutout_location)
    return cutout_box


def _magnet_cutout(base_face, angle):
    # Get second largest face parallel to XY plane - i.e., the inner case face
    # inner_case_face = sorted(case.faces().filter_by(bd.Plane.XY), key=lambda x: x.area)[-2]
    inner_wire = base_face.wires()[0]
    # show_object(inner_wire, name="inner_wire")
    polar_map = PolarWireMap(inner_wire, base_face.center())
    _, center_percent = polar_map.get_polar_location(angle)
    center_at_mm = center_percent * inner_wire.length
    span = params["magnet_count"] * params["magnet_spacing"]
    start = center_at_mm - span / 2
    end = center_at_mm + span / 2

    hole = (
        bd.Plane.XY
            # TODO: Make this a teardrop? At least a shallow one?
        * bd.Circle(
            radius=magnet_radius,
        )
    )
    template = bd.extrude(hole, params["wall_xy_thickness"] - params["magnet_separation_distance"])
    # Extend a bit futher into the case to ensure no overlap, e.g. due to taper
    template += bd.extrude(hole, -(magnet_height + 0.2))

    cutouts = []
    position = start - params["magnet_spacing"]
    while position <= end:
        position += params["magnet_spacing"]
        cutout = copy.copy(template)
        location = inner_wire.location_at(position, position_mode=bd.PositionMode.LENGTH)
        cutout.orientation = location.orientation
        cutout = cutout.rotate(bd.Axis.Z, -90)
        cutout.position = location.position
        # Add 0.01 to avoid overlap issue cutting into base slightly. Float
        # error??
        cutout.position += (0, 0, magnet_radius + params["base_z_thickness"] + 0.01)
        cutouts.append(cutout)
        # show_object(cutout, f"magnet_cutout_{position}")

    return cutouts


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


class PolarWireMap():
    """Maps between polar locations of a wire relative to a central origin, where the resulting map is a dict of angle to location for
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
        iter = 1/n_angles
        while at_position <= 1:
            location = self.wire ^ at_position
            at_position += iter
            ax1 = bd.Axis.X
            ax2 = bd.Wire(bd.Line(self.origin, location.position)).edge()
            ax2 = bd.Axis(edge = ax2)
            angle = round(ax1.angle_between(ax2))
            if ax2.direction.Y < 0:
                # Angle between gives up to 180 as a positive value, so we need to
                # flip it for -ve angles.
                angle = -angle
            self.map_[angle] = at_position


def _find_nearest_key(d, target_int):
    """Find the nearest existing key in a dict to a target integer"""
    nearest = min(d, key=lambda x: abs(x - target_int))
    return nearest


def _create_honeycomb_tile(depth, face):
    radius = params["honeycomb_radius"]
    cell_thickness = params["honeycomb_thickness"]
    d_between_centers = radius + cell_thickness
    locs = HexLocations(d_between_centers, 50, 50, major_radius=True).local_locations
    h = bd.RegularPolygon(radius, 6)
    h = bd.extrude(h, -depth)
    hs = Plane(face) * locs * h
    return hs




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
    case = generate_pcb_case(base_face, pcb_case_wall_height)

    # if params["carrycase"]:
    #     carry = generate_carrycase(base_face, pcb_case_wall_height)

# Export
if "__file__" in locals():
    script_dir = Path(__file__).parent
    bd.export_stl(case, str(script_dir / "build/case.stl"))
    bd.export_stl(carrycase, str(script_dir / "build/carrycase.stl"))


# hds = _create_honeycomb_tile(8, 2, params["base_z_thickness"])
# # show_object(hds)
# x = bd.Box(100,100,10).intersect(bd.Compound(hds))
# show_object(x)

# b = bd.Box(100,100,10, align=(Align.CENTER, Align.CENTER, Align.CENTER))
# radius = 8
# cell_thickness = 2
# depth = 2
# d_between_centers = radius + cell_thickness
# locs = HexLocations(d_between_centers, 50, 50, major_radius=True).local_locations
# h = bd.RegularPolygon(radius, 6)
# hs = bd.extrude(h, -depth)
# hc = Plane(b.faces().sort_by().first) * locs * hs
# show_object(hc, name="hc")
# b -= hc
# show_object(b, name="b")

# f = bd.make_face(bd.Polyline((0, 0), (-5, 0), (0, -5), (0,0)))
