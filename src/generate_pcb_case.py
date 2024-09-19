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

magnet_height = 2
magnet_radius = 4 / 2

polar_position_maps = defaultdict(dict)

# For test prints, slice off the end
slice = Loc((30, 0, 0)) * bd.Box(300, 300, 200, align=(Align.MIN, Align.CENTER, Align.CENTER))

params = default_params # TODO: merge this with user params
pcb_case_wall_height = params["z_space_under_pcb"] + params["wall_z_height"]

# TODO: Move these to my personal maizeless build script
params["cutout_position"] = 32
params["carrycase_cutout_position"] = -108
params["z_space_under_pcb"] = 2.4
params["magnet_position"] = -132
params["honeycomb_base"] = True


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
                    log(f"path_{i}\n{str(p)}  len={p.length}")
                    show_object(l, name=f"path_{i}")
                    line_start = l @ 1

            show_object(bd_l.line, name="line")
            make_face()

    face = bd_s.sketch.face()
    show_object(face, "imported face")
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

# outline = bd.import_svg(script_dir / "build/outline.svg")

# outline = bd.import_svg(script_dir / "build/simplified/outline.svg")

# For testing
# outline = bd.Rectangle(30,80).locate(bd.Location((40, 40, 0)))
# outline = bd.import_svg(script_dir / "build/test_outline_drawn.svg")

# Round trip from outline to wires to face to wires to connect the disconnected
# edges that an svg gets imported with.
# outline = bd.make_face(outline.wires()).wire().fix_degenerate_edges(0.01)
# base_face = bd.mirror(bd.make_face(outline), about=bd.Plane.XZ.offset(-outline.center().X-3.5))
# show_object(base_face, name="raw_import_base_face")
base_face = import_svg(script_dir / "build/outline.svg")
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

    inner_cutout = _friction_fit_cutout(base_face, wall_height)
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
        case -= __lip(base_face)
        # Cut out magnet holes
        case -= _magnet_cutout(base_face, params["magnet_position"])

    # For test prints
    # case -= slice

    show_object(case, name="case")
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
    blocker_thickness = 2
    base_blocker_face = bd.offset(
        base_face, (params["wall_xy_thickness"] + params["carrycase_tolerance_xy"])
    )
    blocker_face = base_blocker_face - base_face
    blocker = bd.extrude(blocker_face, amount=blocker_thickness)
    # Locate the blocker at the top of the pcb case wall
    blocker.move(
        Loc((0, 0, (wall_height + params["carrycase_tolerance_z"] - params["carrycase_z_gap_between_cases"])))
    )
    case = wall + blocker

    # Add lip to hold board in
    case += __lip(base_face, carrycase=True)

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

    # For test prints
    # case -= slice

    # Mirror on top face to create both sides
    topf = case.faces().sort_by(sort_by=bd.Axis.Z).last
    case += bd.mirror(case, about=bd.Plane(topf))
    show_object(case, name="carry case")
    return case


def _friction_fit_cutout(base_face, wall_height):
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

    # calculate taper angle to blend between bottom and top tolerance.
    # tan(x) = o/a, where o is the total taper distance change on the XY plane,
    # and opp is the change in the Z axis.
    opp = -params["wall_xy_bottom_tolerance"] + params["wall_xy_top_tolerance"]
    adj = wall_height - params["z_space_under_pcb"]
    taper = math.degrees(math.atan(opp / adj))
    # taper = 45
    # With the maizeness, above 1 mm seemed to not cause problems. Going to 1.5
    # to be safe.
    safe_offset = 0.3

    log(taper)
    T = math.tan(math.radians(90 - taper))
    log(T)
    offset_bottom_drop = T * safe_offset
    # offset_bottom = bd.offset(base_face, -safe_offset)
    # offset_bottom = bd.offset(base_face, 3)
    log(wall_height + offset_bottom_drop)
    # top_face = bd.Plane(base_face).offset(offset_bottom_drop) * base_face
    top_face = base_face.moved(Loc((0,0,wall_height)))
    log(top_face)
    top_face = bd.offset(top_face, params["wall_xy_top_tolerance"])
    top_face = bd.offset(top_face, 0.0)
    # top_face = bd.offset(base_face.moved(Loc((0,0,wall_height))), 0.3, min_edge_length=0.3)
    show_object(top_face, name="top_face")
    # inner_cutout = bd.offset(base_face, params["wall_xy_bottom_tolerance"])
    # inner_cutout = bd.offset(base_face, -2.4, min_edge_length=0.3)
    # offset_bottom = bd.offset(base_face, -0.3)
    offset_bottom = bd.scale(base_face, 0.95)
    # inner_cutout = bd.loft(bd.Sketch() + [offset_bottom, top_face])
    # show_object(inner_cutout, name="inner_cutout")
    extruded = bd.extrude(offset_bottom, amount=wall_height, taper=-taper)
    # extruded = bd.extrude(base_face, amount=wall_height, taper=0)
    show_object(extruded, name="extruded")
    # return extruded
    # inner_cutout = overkill_cutout

    # inner_face = bd.offset(base_face, -params["wall_xy_bottom_tolerance"])
    # Seem to only be able to offset the bottom a small amount before freezing
    # things... might not be worth the risk.
    # inner_face = bd.offset(base_face, -0.05)
    # inner_face = base_face
    # inner_cutout = bd.extrude(inner_face, wall_height, taper=-taper)
    # inner_cutout.move(Loc((0, 0, params["base_z_thickness"])))
    # show_object(inner_cutout, name="inner_cutout")
    # return inner_cutout


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

    # show_object(cutouts, name=f"magnet_cutouts_{carrycase}")
    return cutouts


def __lip(base_face, carrycase=False):
    outer_face = bd.offset(base_face, params["wall_xy_thickness"])
    lip = bd.offset(outer_face, params["carrycase_tolerance_xy"]) - bd.offset(outer_face, -params["lip_xy_len"])
    lip = lip.intersect(__arc_sector_ray(base_face, params["lip_position_angles"][0], params["lip_position_angles"][1]))
    lip_z_len = params["lip_z_thickness"]
    if not carrycase:
        # A little extra tolerance for lip cutout so that it fits more
        # smoothly, even with a bit of residual support plastic or warping.
        lip_z_len += 0.3
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
    # case = generate_pcb_case(base_face, pcb_case_wall_height)

    # if params["carrycase"]:
    #     carry = generate_carrycase(base_face, pcb_case_wall_height)

# # Export
if "__file__" in locals():
    show_object = lambda *a, **kw: None
    log = lambda x: print(x)
#     script_dir = Path(__file__).parent
#     bd.export_stl(case, str(script_dir / "build/case.stl"))
#     bd.export_stl(carrycase, str(script_dir / "build/carrycase.stl"))

x = _friction_fit_cutout(base_face, pcb_case_wall_height)

# bd.export_stl(x, str(script_dir / "build/test.stl"))

#     # calculate taper angle. tan(x) = o/a
# wall_height = pcb_case_wall_height
# opp = -params["wall_xy_bottom_tolerance"] + params["wall_xy_top_tolerance"]
# wall_height = params["wall_z_height"]
# adj = wall_height
# taper = math.degrees(math.atan(opp / adj))
# log(taper)
# inner_face = base_face
# inner_face = bd.offset(base_face, -1.5)
# # inner_face = bd.offset(base_face, -1)
# # inner_face = bd.offset(base_face, params["wall_xy_bottom_tolerance"])
# show_object(inner_face, name="inner_face")

# # # inner_cutout = bd.extrude(inner_face, wall_height, taper=-1.1)
# inner_cutout = bd.extrude(inner_face, wall_height + 5, taper=-taper)
# # # inner_cutout = bd.extrude(inner_face, wall_height)
# show_object(inner_cutout, name="inner")

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

# import cadquery as cq
# b3d_solid = bd.Solid.make_box(1,1,1)
# cq_solid = cq.Solid.makeBox(1,1,1)
# cq_solid.wrapped = base_face.wrapped
# log(cq_solid.faces())
# # cq_solid = cq_solid.wires().close().extrude(1)
# # cq_solid = cq.Workplane(cq_solid.faces()).faces().wires().toPending().extrude(until=5)
# cq_solid = cq_solid.extrudeLinear(cq_solid.faces(), cq.Vector((0,0,10)), taper=-1)
# # cq_solid = cq_solid.extrudeLinear(cq.Sketch().rect(1,1), vecNormal=cq.Vector((0,0,1)), taper=0)
# # cq_solid = cq.Workplane().circle(2.0).rect(0.5, 0.75).extrude(0.5).findSolid()
# b3d_solid.wrapped = cq_solid.wrapped
# show_object(b3d_solid)

# edges =sorted(base_face.edges(), key=lambda e: e.length)
# log([e.length for e in edges])
# show_object(edges[0], name=f"edge_0")
# for i, edge in enumerate(edges):
#     # if edge.length < 5:
#     #     show_object(edge, name=f"edge_{i}")
#     show_object(edge, name=f"edge_{i}")


# from svgpathtools import parse_path, Line, Path, wsvg
# def offset_curve(path, offset_distance, steps=1000):
#     """Takes in a Path object, `path`, and a distance,
#     `offset_distance`, and outputs an piecewise-linear approximation
#     of the 'parallel' offset curve."""
#     nls = []
#     for seg in path:
#         ct = 1
#         for k in range(steps):
#             t = k / steps
#             offset_vector = offset_distance * seg.normal(t)
#             nl = Line(seg.point(t), seg.point(t) + offset_vector)
#             nls.append(nl)
#     connect_the_dots = [Line(nls[k].end, nls[k+1].end) for k in range(len(nls)-1)]
#     if path.isclosed():
#         connect_the_dots.append(Line(nls[-1].end, nls[0].end))
#     offset_path = Path(*connect_the_dots)
#     return offset_path
