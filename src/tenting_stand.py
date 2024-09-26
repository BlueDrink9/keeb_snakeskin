import math
from dataclasses import dataclass
from build123d import *
Loc = Location

if __name__ not in ["__cq_main__", "temp"]:
    from ocp_vscode import show, show_object, reset_show, set_port, set_defaults, get_defaults
    set_port(3939)
    show_object = lambda *args, **__: show(args)

# case_end = Rectangle(10, wall_height).bounding_box()

blocker_zlen = 1
# More than 90 so that the mating face on the flap hinges can be well above
# 0/not point down.
case_blocker_angle = 120


@dataclass
class Flap:
    """Represents a tenting flap.
    len is the X length of the flap.
    width is the width of the far end (away from the hinge) of the tenting flap.
    tenting_angle is the angle from 0 that the keyboard will be rotated
    clockwise when looking in the direction of the X axis (i.e. angle it will
    tilt the board face towards the user).
    """
    width: int
    len: int
    tent_angle: int = 0

def case_hinge(bolt_d, wall_height, countersunk=True):
    """Countersink covers whether both to countersink and create nut holes"""
    _, hinge_face, outer = _base_faces(bolt_d, wall_height)

    case_connector = Rectangle(outer.radius*1.5, outer.radius*2, align=(Align.MAX, Align.CENTER))
    outer_block = case_connector - outer

    blocker_face = _hinge_blocker(outer)
    blocker = extrude(Plane.XZ * blocker_face, bolt_l/2)
    botf = blocker.faces().sort_by(Axis.Z).first
    blocker.edges().group_by(Axis.Z)[0].filter_by(Axis.Y)
    # Chamfer bottom to reduce support material needed
    blocker = chamfer(blocker.edges().group_by(Axis.Z)[0].filter_by(Axis.Y), botf.length*0.40)

    case_hinge_face = outer_block + blocker_face + hinge_face

    # Just blocker through the center (to block the flaps), then hinges at each end.
    hinge = extrude(Plane.XZ * (case_hinge_face), hinge_width_y)
    out = blocker + hinge
    out.move(Loc((0, bolt_l/2,)))
    out += mirror(out, Plane.XZ)
    end_faces = out.faces().sort_by(Axis.Y)
    # Bolt hole is still centered around Y axis, moving planes to the origin.
    end_plane = Plane(end_faces.first).move(Loc((-end_faces.first.center().X, 0)))
    start_plane = Plane(end_faces.last).move(Loc((-end_faces.last.center().X, 0)))
    if countersunk:
        countersink = end_plane * CounterSinkHole(
            bolt_d / 2, bolt_head_d / 2, hinge_width_y, counter_sink_angle=90
        )
        out -= countersink
        nut_hole = start_plane * extrude(RegularPolygon(nut_d/2, 6), -nut_l)
        out -= nut_hole

    show_object(out, name="case_hinge")

    return out


def tenting_flaps(flaps: list[tuple[int, int, int]], bolt_d, wall_height):
    flaps = [Flap(*f) for f in flaps]
    bolthole, hinge_face, outer = _base_faces(bolt_d, wall_height)
    flaps.sort(key=lambda f: f.len, reverse=True)
    out = []
    for i, f in enumerate(flaps):
        offset = hinge_width_y*(i+1) + 0.2*(i+1)
        flap_hinge_width = bolt_l - offset*2
        flap_hinge = extrude(Plane.XZ * _flap_hinge_face(f.len), hinge_width_y)
        flap_hinge.move(Loc((0, -offset)))
        flap_hinge.move(Loc((0, bolt_l/2)))
        flap_hinge += mirror(flap_hinge, Plane.XZ)
        near_len = flap_hinge.bounding_box().size.Y
        flap = -Plane.YX * _flap(
            f, near_len, inner=i+1==len(flaps)
        )
        flap = flap.move(Loc((0, 0, -outer.radius)))
        flap += flap_hinge
        out.append(flap)

    case_hinge_ = case_hinge(bolt_d, wall_height, countersunk=False)
    bolthole_cutout = _bolthole_cutout(bolthole)
    # Cut smaller flaps out of the larger ones.
    for i, flap in enumerate(out):
        for inner in out[i+1:]:
            out[i] -= inner
            # out[i] -= offset(inner, 0.2)
        # Cutting this out before the scaled inner causes invalid geom.
        out[i] -= bolthole_cutout
        show_object(out[i], name=f"flaps{i}")

        # show_object(out[i].rotate(Axis.Y, -110), name=f"flaps{i}")

    return out


def _base_faces(bolt_d, wall_height):
    outer = Circle(radius=(wall_height)/2 - blocker_zlen/2)
    # Ellipes to give extra tolerance if printing without supports.
    bolthole = Ellipse(bolt_d/2, bolt_d/2*1.1)
    # Add a 45 slope on the bottom of the loop to print better without supports.
    pnt_45 = outer.wire() @ (1-1/8)
    support_slope = -Polygon(
        pnt_45,
        PolarLine(pnt_45, (outer.radius + pnt_45.Y) / math.cos(math.radians(45)), -180 + 45) @ 1,
        (0, -outer.radius),
        align=None,
    ).face()
    hinge_face = outer - bolthole + support_slope
    return bolthole, hinge_face, outer


def _bolthole_cutout(bolthole):
    bolthole_cutout = extrude(Plane.XZ * (bolthole), mechanism_length/2)
    bolthole_cutout.move(Loc((0, mechanism_length/2,)))
    bolthole_cutout += mirror(bolthole_cutout, Plane.XZ)
    return bolthole_cutout


def _flap_hinge_face(length):
    _, hinge_face, outer = _base_faces(bolt_d, wall_height)
    # Angle above 90 when open so that it holds itself open and won't
    # collapse.
    open_angle = 110
    blocker_angle = case_blocker_angle - open_angle
    blocker = [PolarLine((0, 0), outer.radius + blocker_zlen, blocker_angle)]
    blocker += [
        SagittaArc(
            (0, -outer.radius),
            blocker[0] @ 1,
            -Vertex(blocker[0] @ 1).distance_to((0, -outer.radius)) / 6,
        )
    ]
    blocker = make_face([*blocker, Line(blocker[0] @ 0, blocker[-1] @ 0)])
    # blocker -= outer

    flap_hinge_face = hinge_face + blocker
    # show_object(flap_hinge_face)
    return flap_hinge_face

def _flap(f: Flap, width_near, inner=True):
    thickness = flap_t
    pts = [
        # bl, br, tr, tl
        (0, 0),
        (width_near, 0),
        (f.width + (width_near - f.width) / 2, f.len),
        ((width_near - f.width) / 2, f.len),
    ]

    if f.tent_angle:
        hypot = f.width / math.cos(math.radians(f.tent_angle))
        if f.tent_angle < 0:
            end_slope = PolarLine(pts[2], hypot, 180 + f.tent_angle)
            pts[3] = end_slope @ 1
        else:
            end_slope = PolarLine(pts[3], hypot, f.tent_angle)
            pts[2] = end_slope @ 1

    face = Polygon(
        *pts,
        align=(Align.CENTER, Align.MIN),
    )
    flap = extrude(face, thickness)

    if inner:
        # Add a ridge to hold the next flap out in place when closed. Innermost
        # flap should have velcro to the PCB to hold it in place.
        edge = face.edges().sort_by(Axis.X).first
        # Create a plane such that the flap edge is X.
        plane = Plane(origin = edge @ 0.5, x_dir=edge % 0.5, y_dir=Axis.Y.direction)
        ridge_width = edge.length/6
        # Thick enough for chamfer to not fail, and pegged to width for that same reason.
        ridge_len = thickness*0.25*ridge_width
        # Arbitrary edge length ratio.
        ridge_face = Ellipse(ridge_width, ridge_len)
        # Remove half to form semicircle
        ridge_face = plane * split(ridge_face)
        ridge = extrude(ridge_face, thickness/2)
        top_curve = ridge.edges().group_by(Axis.Z)[-1].sort_by(SortBy.LENGTH)[-1]
        ridge = chamfer(top_curve, thickness/2 - 0.1)
        flap += ridge


    return flap


def _hinge_blocker(outer):
    lines = [
        PolarLine((0, 0), outer.radius + blocker_zlen, case_blocker_angle),
        Line((0, 0), (-outer.radius, 0)),
    ]
    # Close to form a triangle sort of shape
    blocker = make_face([*lines, Line(lines[0] @ 1, lines[-1] @ 1)])
    # Add a rectangle base from the left that merges with the case and makes things
    # more solid.
    tip = lines[0] @ 1
    blocker += Polygon(
        (tip.X, 0), tip, (-outer.radius*1.5, tip.Y), (-outer.radius*1.5, 0), align=None
    )
    # Offset to get some extra space for tolerance in the rotational component.
    blocker -= offset(outer, 0.2)
    return blocker


bolt_d = 3 # M3
bolt_l = 50 # Includes head, assuming countersunk
bolt_head_d = 6.94  # https://engineersbible.com/countersunk-socket-metric/
nut_d = 5.50  # https://amesweb.info/Fasteners/Metric_Hex_Nuts/Metric-Hex-Nut-Dimensions.aspx
nut_l = 2.4
wall_height = 6.4 + 1
mechanism_length = 60
hinge_width_y = 5
flap_t = 2
flaps = [[40, 90, 10], [30, 30, 30]]

# tenting_fraps(flaps, bolt_d, wall_height)
# case_hinge(bolt_d, wall_height)
