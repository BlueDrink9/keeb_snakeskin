import math
from dataclasses import dataclass
from functools import cache

from build123d import *

# Operating under the assumption that the other script will end up directly
# updating this dict for user preferences.
from default_params import default_params as cfg

# If I wanted to make this more modular, I could probably put the default
# params for this module here, and add them to the main dict on import...

Loc = Location
blocker_zlen = 2
# More than 90 so that the mating face on the flap hinges can be well above
# 0/not point down.
case_blocker_angle = 90 + 45
tenting_stability_angle = 20
velcro_width = 15
hole_tolerance = 0.2

if __name__ not in ["__main__", "__cq_main__", "temp"]:
    show_object = lambda *_, **__: None
if __name__ == "__main__":
    from ocp_vscode import (get_defaults, reset_show, set_defaults, set_port,
                            show, show_object)

    set_port(3939)

# case_end = Rectangle(10, wall_height).bounding_box()


@dataclass
class _Flap:
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


@cache
def case_hinge(wall_height, bolt_d, countersunk=True):
    """Countersink covers whether both to countersink and create nut holes"""
    _, hinge_face, outer = _base_faces(bolt_d, wall_height)

    case_connector = Rectangle(
        outer.radius * 1.5, outer.radius * 2, align=(Align.MAX, Align.CENTER)
    )
    outer_block = case_connector - outer

    blocker_face = _hinge_blocker(outer)
    blocker = extrude(Plane.XZ * blocker_face, bolt_l / 2)
    botf = blocker.faces().sort_by(Axis.Z).first
    blocker.edges().group_by(Axis.Z)[0].filter_by(Axis.Y)
    # Chamfer bottom to reduce support material needed
    blocker = chamfer(
        blocker.edges().group_by(Axis.Z)[0].filter_by(Axis.Y), botf.length * 0.40
    )

    case_hinge_face = outer_block + blocker_face + hinge_face

    # Just blocker through the center (to block the flaps), then hinges at each end.
    hinge = extrude(Plane.XZ * (case_hinge_face), hinge_width_y)
    out = blocker + hinge
    out.move(
        Loc(
            (
                0,
                bolt_l / 2,
            )
        )
    )
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
        hexagon = offset(RegularPolygon(nut_d / 2, 6, major_radius=False), hole_tolerance)
        nut_hole = start_plane * extrude(hexagon, -nut_l)
        out -= nut_hole
    h = outer.radius
    show_object(out, name="case_hinge")

    out.__hash__ = lambda: hash(id(hash))
    return out


def tenting_legs(flaps_: list[tuple[int, int, int]], case_len, bolt_d, wall_height, fillet_end=True):
    """Create legs and hinges for tenting the keyboard. case_len is the X length of the case, and is used to calculate the optimal angle for the leg to open to so that it is 20 degrees past vertical on the desk."""
    flaps = [_Flap(*f) for f in flaps_]
    bolthole, _, outer = _base_faces(bolt_d, wall_height)
    # Go through from longest to shortest
    flaps.sort(key=lambda f: f.len, reverse=True)
    out = []
    for i, f in enumerate(flaps):
        hinge_y_offset = hinge_width_y * (i + 1) + 0.2 * (i + 1)
        # flap_hinge_width = bolt_l - hinge_y_offset*2
        flap_hinge = extrude(
            Plane.XZ * _flap_hinge_face(case_len, f.len, wall_height, bolt_d),
            hinge_width_y,
        )
        flap_hinge.move(Loc((0, -hinge_y_offset)))
        flap_hinge.move(Loc((0, bolt_l / 2)))
        flap_hinge += mirror(flap_hinge, Plane.XZ)
        near_len = flap_hinge.bounding_box().size.Y
        flap = -Plane.YX * _flap(
            f,
            near_len,
            outer.radius + cfg["wall_xy_thickness"],
            inner=i > 0,
            innermost=(i + 1 == len(flaps)),
            outermost=i == 0,
            fillet_end=fillet_end,
        )
        flap = flap.move(Loc((0, 0, -outer.radius)))
        flap += flap_hinge
        out.append(flap)

    case_hinge_ = case_hinge(wall_height, bolt_d, countersunk=False)
    bolthole_cutout = _bolthole_cutout(bolthole)
    # Cut smaller flaps out of the larger ones.
    for i, flap in enumerate(out):
        for inner in out[i + 1 :]:
            # out[i] -= inner
            out[i] -= offset(inner, 0.2)
        # Cutting this out before the scaled inner causes invalid geom.
        out[i] -= bolthole_cutout

        finger_ridge = _finger_opening_ridge(flap)
        # show_all()
        out[i] -= finger_ridge

        if i + 1 < len(out):  # From all but shortest
            # Ensure the innermost divot isn't being left out as a floating square
            d = ((-Plane.YX * _velcro_divot(flaps[-1]))).move(
                Loc((0, 0, -outer.radius))
            )
            out[i] -= d

        show_object(out[i], name=f"flaps{i}")

        # show_object(out[i].rotate(Axis.Y, -70), name=f"flaps{i}")

    return ShapeList(out)


@cache
def _base_faces(bolt_d, wall_height):
    outer = Circle(radius=(wall_height) / 2)
    # Ellipes to give extra tolerance if printing without supports.
    bolthole = offset(Ellipse(bolt_d / 2, bolt_d / 2 * 1.1), hole_tolerance).face()
    # Add a 45 slope on the bottom of the loop to print better without supports.
    pnt_45 = outer.wire() @ (1 - 1 / 8)
    support_slope = -Polygon(
        pnt_45,
        PolarLine(
            pnt_45, (outer.radius + pnt_45.Y) / math.cos(math.radians(45)), -180 + 45
        )
        @ 1,
        (0, -outer.radius),
        align=None,
    ).face()
    hinge_face = outer - bolthole + support_slope
    return bolthole, hinge_face, outer


def _bolthole_cutout(bolthole):
    bolthole_cutout = extrude(Plane.XZ * (bolthole), mechanism_length / 2)
    bolthole_cutout.move(
        Loc(
            (
                0,
                mechanism_length / 2,
            )
        )
    )
    bolthole_cutout += mirror(bolthole_cutout, Plane.XZ)
    return bolthole_cutout


def _calc_leg_open_angle(case_len, flap_len):
    # The calculation gets the angle such that the leg is perpendicular to the desk if the end of the case is also sitting on it. Then add extra to make the leg more stable, so it doesn't collapse back in.
    # The sloped case acts as the hypotenuse, with flap length as the adjacent side.
    return math.degrees(math.acos(flap_len / case_len)) + tenting_stability_angle


def _finger_opening_ridge(flap) -> None:
    # Cut out a ridge for finger to open the flap
    topright_edge = (
        flap.faces()
        .filter_by(Axis.Z)
        .sort_by(Axis.Z)
        .last.edges()
        .sort_by(Axis.Y)
        .last
    )
    ridge_len = 15
    # edge_width = left_edge.length/10
    plane = Plane(
        # Origin just before the end. Edge goes from end to start, so -ve position
        origin=topright_edge.location_at(
            topright_edge.length - ridge_len/2 - 10, position_mode=PositionMode.LENGTH
        ).position,
        x_dir=(topright_edge % 0.5),
        y_dir=topright_edge.normal(),
        z_dir=-Axis.Z.direction,
    )
    finger_ridge = _ridge(
        ridge_len,
        # Tiny bit less than max thickness, to exploit the fact that the projection subtracted from the case will be complete, but the slice will have a gap for the finger.
        cfg["base_z_thickness"] * 0.99,
    )
    finger_ridge = plane * finger_ridge
    finger_ridge = finger_ridge.move(Loc((0, -2, 0)))
    return finger_ridge


@cache
def _flap_hinge_face(case_len, flap_len, wall_height, bolt_d):
    _, hinge_face, outer = _base_faces(bolt_d, wall_height)
    open_angle = _calc_leg_open_angle(case_len, flap_len)
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


def _flap(f: _Flap, width_near, hinge_size, inner=True, innermost=False, outermost=False, fillet_end=True):
    thickness = cfg["base_z_thickness"]
    # Extend straight until the edge of hinge_size, then trapezoid to the end
    pts = [
        # ml, bl, br, mr, tr, tl
        (0, hinge_size),
        (0, 0),
        (width_near, 0),
        (width_near, hinge_size),
        (f.width + (width_near - f.width) / 2, f.len),
        ((width_near - f.width) / 2, f.len),
    ]

    if f.tent_angle:
        hypot = f.width / math.cos(math.radians(f.tent_angle))
        if f.tent_angle < 0:
            end_slope = PolarLine(pts[-2], hypot, 180 + f.tent_angle)
            pts[-1] = end_slope @ 1
        else:
            end_slope = PolarLine(pts[-1], hypot, f.tent_angle)
            pts[-2] = end_slope @ 1

    face = Polygon(
        *pts,
        align=(Align.CENTER, Align.MIN),
    )
    flap = extrude(face, thickness)

    if innermost:
        flap -= _velcro_divot(f)

    if inner:
        # Add a ridge to hold the next flap out in place when closed. Innermost
        # flap should have velcro to the PCB to hold it in place.
        edge = face.edges().sort_by(Axis.X).first
        ridge_len = 5
        plane = Plane(
            # Origin just before the end. Edge goes from end to start, so -ve position
            origin=edge.location_at(
                ridge_len + 5, position_mode=PositionMode.LENGTH
            ).position,
            x_dir=edge % 0.5,
            y_dir=edge.normal(),
        )
        ridge = _ridge(
            ridge_len,
            thickness / 2,
        )
        ridge = plane * ridge
        flap += ridge

    end_edges = flap.edges().filter_by(Plane.XY).group_by(Axis.Y)[-1]
    if fillet_end:
        flap = fillet(end_edges, thickness / 2.1)

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
        (tip.X, 0),
        tip,
        (-outer.radius * 1.5, tip.Y),
        (-outer.radius * 1.5, 0),
        align=None,
    )
    # Offset to get some extra space for tolerance in the rotational component.
    blocker -= offset(outer, 0.3)
    return blocker


def _ridge(ridge_width, thickness) -> None:
    """Width = size along the edge it's on"""
    # Thick enough for chamfer to not fail, and pegged to width for that same
    # reason.
    ridge_len = 3
    ridge_face = Rectangle(ridge_width, ridge_len * 2)
    # Remove half to form half
    # ridge_face = split(ridge_face)
    ridge = extrude(ridge_face, thickness)
    top_curve = (
        ridge.edges().group_by(Axis.Z)[-1].filter_by(Axis.X).sort_by(Axis.Y).first
    )
    ridge = chamfer(top_curve, min(ridge_len, thickness) - 0.1)

    return ridge


def _velcro_divot(flap):
    # Cut out a divot to allow velcro to sit without affecting closing of the
    # case
    divot = Rectangle(velcro_width, velcro_width, align=(Align.CENTER, Align.MAX)).move(
        Loc((0, flap.len - 2.5, cfg["base_z_thickness"]))
    )
    return extrude(divot, -cfg["base_z_thickness"] * 0.5)


bolt_l = cfg["tent_hinge_bolt_l"]  # Includes head, assuming countersunk
bolt_d = cfg["tent_hinge_bolt_d"]
bolt_head_d = cfg[
    "tent_hinge_bolt_head_d"
]  # https://engineersbible.com/countersunk-socket-metric/
nut_d = cfg[
    "tent_hinge_nut_d"
]  # https://amesweb.info/Fasteners/Metric_Hex_Nuts/Metric-Hex-Nut-Dimensions.aspx
nut_l = cfg["tent_hinge_nut_l"]
mechanism_length = bolt_l

hinge_width_y = cfg["tent_hinge_width"]

if __name__ in ["temp", "__cq_main__", "__main__"]:
    tenting_legs([[40, 90, 10], [30, 60, 30], [20, 30, 30]], 144.4, 3, 7.4)
    case_hinge(7.4, 3)
