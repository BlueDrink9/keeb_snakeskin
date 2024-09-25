import math
from typing import Iterable
from dataclasses import dataclass
from build123d import *
Loc = Location

if __name__ not in ["__cq_main__", "temp"]:
    from ocp_vscode import show, show_object, reset_show, set_port, set_defaults, get_defaults
    set_port(3939)
    show_object = lambda *args, **__: show(args)


bolt_d = 3 # M3
bolt_l = 50 # Doesn't include head
wall_height = 6.4
mechanism_length = 80
hinge_width_y = 5
flap_t = 2
blocker_zlen = 1
# More than 90 so that the mating face on the flap hinges can be well above
# 0/not point down.
case_blocker_angle = 120

case_end = Rectangle(10, wall_height).bounding_box()
outer = Circle(radius=bolt_d/2 + (wall_height-bolt_d)/2 - blocker_zlen/2)
case_connector = Rectangle(20, outer.radius*2, align=(Align.MAX, Align.CENTER))
outer_block = case_connector - outer
bolthole = Circle(radius=bolt_d/2)

def _hinge_blocker():
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

blocker = _hinge_blocker()
hinge_face = outer - bolthole
case_hinge_face = outer_block + blocker + hinge_face
#  # class CounterSinkHole(radius: float, counter_sink_radius: float, depth: Optional[float] = None, counter_sink_angle: float = 82, mode: Mode = Mode.SUBTRACT)[source]
# # .extrude(bold_d)


case_hinge = extrude(Plane.XZ * (blocker), mechanism_length/2)
case_hinge += extrude(Plane.XZ * (outer_block + case_hinge_face), hinge_width_y)
case_hinge.move(Loc((0, mechanism_length/2,)))
case_hinge += mirror(case_hinge, Plane.XZ)
show_object(case_hinge, name="case_hinge")

bolthole_cutout = extrude(Plane.XZ * (bolthole), mechanism_length/2)
bolthole_cutout.move(Loc((0, mechanism_length/2,)))
bolthole_cutout += mirror(bolthole_cutout, Plane.XZ)


def _flap_hinge_face(length):
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

@dataclass
class Flap:
    """Represents a tenting flap.
    len is the X length of the flap.
    width is the width of the far end (away from the hinge) of the tenting flap.
    tenting_angle is the angle from 0 that the keyboard will be rotated
    clockwise when looking in the direction of the X axis (i.e. angle it will
    tilt the board face towards the user).
    """
    len: int
    width: int
    tent_angle: int = 0

def _flap(f: Flap, width_near, inner=True):
    thickness = flap_t
    # TODO: add tenting angle front/back at the end.
    top_left_point = ((width_near - f.width) / 2, f.len),
    face = Polygon(
        (0, 0),
        (width_near, 0),
        (f.width + (width_near - f.width) / 2, f.len),
        top_left_point,
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


def tenting_flaps(flaps: Iterable[Flap]):
    flaps.sort(key=lambda f: f.len, reverse=True)
    out = []
    for i, f in enumerate(flaps):
        offset = hinge_width_y*(i+1) + 0.2*(i+1)
        flap_hinge_width = mechanism_length - offset*2
        flap_hinge = extrude(Plane.XZ * _flap_hinge_face(f.len), hinge_width_y)
        flap_hinge.move(Loc((0, -offset)))
        flap_hinge.move(Loc((0, mechanism_length/2)))
        flap_hinge += mirror(flap_hinge, Plane.XZ)
        flap = -Plane.YX * _flap(
            f, flap_hinge_width, inner=i+1==len(flaps)
        )
        flap = flap.move(Loc((0, 0, -outer.radius)))
        flap += flap_hinge
        # show_object(bolthole_cutout, name="bolthole_cutout")
        out.append(flap)

    # Cut smaller flaps out of the larger ones.
    for i, flap in enumerate(out):
        for inner in out[i+1:]:
            out[i] -= scale(inner, ((1.01, 1.01, 1)))
        # Cutting this out before the scaled inner causes invalid geom.
        out[i] -= bolthole_cutout
        # show_object(flaps[i], name=f"flaps{i}")

        show_object(out[i].rotate(Axis.Y, -110), name=f"flaps{i}")

    return out

tenting_flaps([Flap(90, 40), Flap(30, 50, 35)])
