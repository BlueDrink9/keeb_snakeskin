import copy
import math
import os
from collections import defaultdict
from pathlib import Path
import build123d as bd
from build123d import Align, Rot
from build123d import *
import svgpathtools as svg

Loc = bd.Location
if "__file__" in globals():
    script_dir = Path(__file__).parent
else:
    script_dir = Path(os.getcwd())

# TODO:
# * Change bottom tolerance to account for z space underneath pcb
# * Try flipping the cutout to get a negative tolerance on the bottom.
# * reduce overhangs. Chamfer carrycase blocker X nvm, this is going to be too
# hard with current version. Ah, but what if I do it before subtracting center?
# Can extrude with taper outwards, so maybe I can apply that.
# * Stand, attachments for straps. Separate module?
#
# TODO: Testing:
# * Unmirror the carrycase
# * Cut to just the square end
# * test case fit (confident here)
# * test carrycase entry and exit (having to slip it in on an angle will
# require tolerance/stretching in that direction, but I'm not sure how much).

default_params = {
    "base_z_thickness": 3,
    "wall_xy_thickness": 3,
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
    "carrycase_tolerance_xy": 0.8,
    "carrycase_tolerance_z": 0.5,
    "carrycase_wall_xy_thickness": 4,
    "carrycase_z_gap_between_cases": 9 + 1,
    "carrycase_cutout_position": -90,
    "carrycase_cutout_xy_width": 15,
    "lip_z_thickness": 2,
    "lip_xy_len": 1.5,
    "lip_position_angles": [160, 30],
    "magnet_position": -90.0,
    "magnet_separation_distance": 1,
    "magnet_spacing": 12,
    "magnet_count": 6,
}
params = default_params # TODO: merge this with user params

# TODO: Move these to my personal maizeless build script
params["cutout_position"] = -34
params["carrycase_cutout_position"] = 105
params["z_space_under_pcb"] = 2.4
params["magnet_position"] = 100
params["honeycomb_base"] = True
params["wall_z_height"] = 2.6
params["lip_position_angles"] = [-160, -30]

magnet_height = 2
magnet_radius = 4 / 2

polar_position_maps = defaultdict(dict)

test_print = False
# For test prints, slice off the end
if test_print:
    slice = Loc((30, 0, 0)) * bd.Box(300, 300, 200, align=(Align.MIN, Align.CENTER, Align.CENTER))

pcb_case_wall_height = params["z_space_under_pcb"] + params["wall_z_height"]

def import_svg(path):
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
    with BuildPart() as bd_p:
        with BuildSketch() as bd_s:
            with BuildLine() as bd_l:
                line_start = point(paths[0].start)
                # Add first path to the end again, to ensure the loop is closed
                paths.append(paths[0])
                for i, p in enumerate(paths):
                    # Filter out tiny edges that may cause issues with OCCT ops
                    if p.length() < 0.3:
                        continue
                    if isinstance(p, svg.Line):
                        l = bd.Line(line_start, point(p.end))
                    elif isinstance(p, svg.Arc):
                        # Seems all the arcs have same value for real + imag, so just use real
                        r = p.radius.real
                        l = bd.RadiusArc(line_start, point(p.end), radius=r)
                        # This approximates the arc with a spline. It's slow
                        # and doesn't seem to help anything.
                        # l = bd.RadiusArc(line_start, point(p.end), radius=r, mode=bd.Mode.PRIVATE)
                        # l = bd.RadiusArc((p.start.real, p.start.imag), (p.end.real, p.end.imag), radius=r)
                    else:
                        log("Unknown path type for ", p)
                    # log(f"path_{i}\n{str(p)}  len={p.length}")
                    # show_object(l, name=f"path_{i}")
                    line_start = l @ 1

            # show_object(bd_l.line, name="line")
            make_face()

    face = bd_s.sketch.face()
    face.move(Loc(-face.center()))
    # show_object(face, "imported face")
    return face

# Function to calculate Euclidean distance between two points
def euclidean_distance(p1, p2):
    return math.sqrt((p1.real - p2.real)**2 + (p1.imag - p2.imag)**2)

def sort_paths(lines):
    """Return list of paths sorted and flipped so that they are connected end to end as the list iterates."""
    if not lines:
        return []

    # Start with the first line
    sorted_lines = [lines.pop(0)]

    while lines:
        last_line = sorted_lines[-1]
        last_end = last_line.end

        # Find the closest line to the last end point
        closest_line, closest_distance, flip = None, float('inf'), False
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

outline = bd.import_svg(script_dir / "build/outline.svg")

# outline = bd.import_svg(script_dir / "build/simplified/outline.svg")

# Round trip from outline to wires to face to wires to connect the disconnected
# edges that an svg gets imported with.
outline = bd.make_face(outline.wires()).wire().fix_degenerate_edges(0.01)
# show_object(outline, name="raw_import_outline")
base_face = bd.make_face(outline)
base_face.move(Loc(-base_face.center()))
base_face = bd.mirror(base_face, about=bd.Plane.XZ)
show_object(base_face, name="raw_import_base_face")

# base_face = import_svg(script_dir / "build/outline.svg")

# For testing
# base_face = bd.Rectangle(30,80).locate(bd.Location((40, 40, 0)))
# base_face = bd.import_svg(script_dir / "build/test_outline_drawn.svg")


# show_object(base_face, name="base_face", options={"alpha":0.5, "color": (0, 155, 55)})


def generate_cases(svg_file, params=None):
    if not params:
        params = {}
    default_params.update(params)
    params = default_params

    outline = bd.import_svg(svg_file)
    return


def generate_pcb_case(base_face, wall_height):
    base = bd.extrude(base_face, params["base_z_thickness"])

    wall_outer = bd.offset(
        base_face,
        params["wall_xy_thickness"],
    )

    inner_cutout = _friction_fit_cutout(base_face.face().move(Loc((0, 0, params["base_z_thickness"]))))
    # show_object(inner_cutout, name="inner")
    wall = (
        bd.extrude(wall_outer, wall_height + params["base_z_thickness"]) - inner_cutout - base
    )

    # if params["honeycomb_base"]:
    #     # Create honeycomb by subtracting it from the top face of the base.
    #     hc = _create_honeycomb_tile(
    #         params["base_z_thickness"], base.faces().sort_by(bd.Axis.Z).last
    #     )
    #     base -= hc

    case = wall + base

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

    case = case - cutout_box

    if params["carrycase"]:
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


    # Part that blocks the pcb case from going all the way through
    # Blocker is made of 3 parts:
    # 1. a flat layer offset blocker_thickness_xy, extruded  2 * blocker_thickness_z
    # from the base face,
    # 2. a subtracted layer starting at blocker_thickness_z that that tapers out
    # to the carrycase wall, to create a printable overhang,
    # 3. a subtracted layer extruded blocker_thickness from base_face.
    blocker_thickness_xy = params["wall_xy_thickness"] + params["carrycase_tolerance_xy"]
    blocker_thickness_z = 2
    taper = 50
    overhang_thickness_z = (blocker_thickness_xy - 0.1) / math.tan(math.radians(taper))
    blocker_hull = bd.extrude(
        bd.offset(base_face, blocker_thickness_xy), amount=blocker_thickness_z + overhang_thickness_z
    )
    overhang = bd.extrude(
        base_face.moved(Loc((0, 0, blocker_thickness_z))),
        overhang_thickness_z, taper=-taper
    )
    blocker_inner_cutout = bd.extrude(
        base_face, amount=blocker_thickness_z
    )
    blocker = blocker_hull - overhang - blocker_inner_cutout
    # Locate the blocker at the top of the pcb case all
    blocker.move(
        Loc((0, 0, (wall_height + params["carrycase_tolerance_z"] - params["carrycase_z_gap_between_cases"])))
    )
    # show_object(blocker, name="blocker")

    case = wall + blocker

    # Add lip to hold board in
    case += _lip(base_face, carrycase=True)

    # Create finger cutout for removing boards
    botf = case.faces().sort_by(sort_by=bd.Axis.Z).first
    bottom_inner_wire = botf.wires()[0]
    polar_map = PolarWireMap(bottom_inner_wire, botf.center())
    cutout_location, _ = polar_map.get_polar_location(params["carrycase_cutout_position"])
    cutout_box = _finger_cutout(
        cutout_location,
        params["carrycase_wall_xy_thickness"],
        params["carrycase_cutout_xy_width"],
        pcb_case_wall_height - magnet_height - 0.3,
    )
    # show_object(cutout_box, name="carry case cutout box")

    case -= cutout_box

    case -= _magnet_cutout(base_face, params["magnet_position"], carrycase=True)

    if test_print:
        case -= slice

    # Mirror on top face to create both sides
    topf = case.faces().sort_by(sort_by=bd.Axis.Z).last
    if not test_print:
        case += bd.mirror(case, about=bd.Plane(topf))
    show_object(case, name="carry case", options={"color": (0, 0, 255)})
    return case


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
    total_wall_height  = wall_height_pcb_up + params["z_space_under_pcb"]
    # calculate taper angle to blend between bottom and top tolerance.
    # tan(x) = o/a, where o is the total taper distance change on the XY plane,
    # and opp is the change in the Z axis.
    opp = params["wall_xy_top_tolerance"] - params["wall_xy_bottom_tolerance"]
    # Adj is just the height between the top and bottom tolerances, where
    # top = top of the wall, and bottom = where the pcb should
    # sit (z_space_under_pcb above the case bottom).
    adj = params["wall_z_height"]
    taper = math.degrees(math.atan(opp / adj))

    # # We seem to be able to get away with small tapers/extrusions up smaller
    # # wall heights.
    # # So let's try having an untapered wall below the pcb, and only tapering
    # # where the bottom tolerance will come into play.
    # # bottom_face = _safe_offset2d(base_face.face(), params["wall_xy_bottom_tolerance"])
    # under_pcb = bd.extrude(bottom_face, amount=params["z_space_under_pcb"])
    # face_at_pcb = under_pcb.faces().sort_by(sort_by=bd.Axis.Z).last
    # tapered_cutout = bd.extrude(face_at_pcb, amount=params["wall_z_height"], taper=-taper)
    # case_inner_cutout = under_pcb + tapered_cutout

    T = math.tan(math.radians(taper))  # opp/adj
    # # We have two XY offsets from base_face - one at the bottom where the case
    # # should start (unknown), and one where the pcb starts (wall_xy_bottom_tolerance).
    case_bottom_offset = T * params["z_space_under_pcb"]
    bottom_offset = -case_bottom_offset + params["wall_xy_bottom_tolerance"]
    bottom_face = _size_scale(base_face, bottom_offset)
    case_inner_cutout = bd.extrude(bottom_face, amount=total_wall_height, taper=-taper)

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


def _size_scale(obj, size_change):
    """Scale an object by a size, such that the new size bounding box is be
    size_change smaller in the x, y and z axis."""
    import build123d as bd
    obj = obj.copy()
    center = obj.center()
    bb = obj.bounding_box()
    zchange = 0
    if bb.size.Z > 0:
        zchange = size_change/bb.size.Z
    factor = (
        1 + (size_change/bb.size.X),
        1 + (size_change/bb.size.Y),
        1 + zchange
    )
    # log(factor)
    # log(obj)
    # Scaling by a vector changes the object too much, messes things up.
    # We'll have to scale by a scalar. Picking the smallest of the factors to
    # minimise change on the tightest axis.
    # obj = bd.scale(obj, by=factor).face()
    obj = bd.scale(obj, by=min(factor)).face()
    # show_object(obj, name="scaled")
    # log(obj)
    # extruded = bd.extrude(obj, amount=2, taper=-19, dir=(0,0,1))
    obj.move(Loc(center - obj.center()))

    # bb = obj.bounding_box()
    # xlen_new = bb.max.X - bb.min.X
    # ylen_new = bb.max.Y - bb.min.Y
    # print(xlen, xlen_new, xlen_new - xlen)
    # print(ylen, ylen_new, ylen_new - ylen)

    return obj

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
    cutout_box = bd.fillet(
        cutout_box.edges()
        .filter_by(bd.Axis.X)
        , height/2
    )
    cutout_box.locate(cutout_location)
    return cutout_box


def _magnet_cutout(main_face, angle, carrycase=False):
    # Adding a bit of extra space around the radius, so that we can print
    # magnet holes without supports and account for the resulting droop.
    magnet_radius_y = magnet_radius + 0.2
    # Get second largest face parallel to XY plane - i.e., the inner case face
    # inner_case_face = sorted(case.faces().filter_by(bd.Plane.XY), key=lambda x: x.area)[-2]
    inner_wire = main_face.wires()[0]
    # show_object(inner_wire, name="inner_wire")
    polar_map = PolarWireMap(inner_wire, main_face.center())
    _, center_percent = polar_map.get_polar_location(angle)
    center_at_mm = center_percent * inner_wire.length
    span = params["magnet_count"] * params["magnet_spacing"]
    start = center_at_mm - span / 2
    end = center_at_mm + span / 2

    hole = (
        bd.Plane.XY
        * bd.Ellipse(
            x_radius=magnet_radius,
            y_radius=magnet_radius_y,
        )
    )

    if carrycase:
        distance = (params["wall_xy_thickness"] + params["carrycase_tolerance_xy"] + magnet_height)
    else:
        # Distance into main wall of case
        distance = params["wall_xy_thickness"] - params["magnet_separation_distance"]
    template = bd.extrude(hole, distance)
    if not carrycase:
        # Extend into the case too to ensure no overlap, e.g. due to taper
        template += bd.extrude(hole, -(magnet_height))

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
        cutout.position += (0, 0, magnet_radius_y + params["base_z_thickness"] + 0.01)
        cutouts.append(cutout)
        # show_object(cutout, f"magnet_cutout_{position}")

    # show_object(cutouts, name=f"magnet_cutouts_{carrycase}", options={"alpha": 0.8})
    return cutouts


def _lip(base_face, carrycase=False):
    outer_face = bd.offset(base_face, params["wall_xy_thickness"])
    lip = bd.offset(outer_face, params["carrycase_tolerance_xy"]) - bd.offset(outer_face, -params["lip_xy_len"])
    lip = lip.intersect(__arc_sector_ray(base_face, params["lip_position_angles"][0], params["lip_position_angles"][1]))
    lip_z_len = params["lip_z_thickness"]
    if not carrycase:
        # A little extra tolerance for lip cutout so that it fits more
        # smoothly, even with a bit of residual support plastic or warping.
        lip_z_len += 0.3
    lip = bd.extrude(lip, params["lip_z_thickness"])
    # show_object(lip, name="lip", options={"alpha": 0.8})
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
    # case = generate_pcb_case(base_face, pcb_case_wall_height)

    if params["carrycase"]:
        carry = generate_carrycase(base_face, pcb_case_wall_height)

# # Export
if "__file__" in locals():
    show_object = lambda *a, **kw: None
    log = lambda x: print(x)
    script_dir = Path(__file__).parent
    bd.export_stl(case, str(script_dir / "build/case.stl"))
    bd.export_stl(carrycase, str(script_dir / "build/carrycase.stl"))

# bd.export_stl(x, str(script_dir / "build/test.stl"))
