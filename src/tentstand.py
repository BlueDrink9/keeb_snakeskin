import math
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
# Pairs of length, width (where width is the width of the far end of the
# tenting flap), in order of len
# TODO: add tenting angle front/back at the end.
flap_lens = [(90, 40), (30, 50)]
flap_t = 2

case_end = Rectangle(10, wall_height).bounding_box()
blocker_zlen = 1
outer = Circle(radius=bolt_d/2 + (wall_height-bolt_d)/2 - blocker_zlen/2)
case_connector = Rectangle(20, outer.radius*2, align=(Align.MAX, Align.CENTER))
outer_block = case_connector - outer
bolthole = Circle(radius=bolt_d/2)
blocker_base = Rectangle(outer.radius, outer.radius*2, align=(Align.MAX, Align.CENTER))
case_blocker_angle = 120
blocker = [
    PolarLine((0, 0), blocker_zlen, case_blocker_angle),
    Line((0, 0), (-outer.radius, 0)),
]
blocker = make_face([*blocker, Line(blocker[0] @ 1, blocker[-1] @ 1)])
blocker.move(Loc((0, outer.radius)))

hinge_face = outer - bolthole
case_hinge_face = outer_block + blocker + hinge_face
#  # class CounterSinkHole(radius: float, counter_sink_radius: float, depth: Optional[float] = None, counter_sink_angle: float = 82, mode: Mode = Mode.SUBTRACT)[source]
# # .extrude(bold_d)

def _flap_hinge_face(length):
    # Angle above 90 when open so that it holds itself open and won't
    # collapse.
    open_angle = 110
    blocker_angle = case_blocker_angle - open_angle
    blocker = [Loc((outer.radius, 0)) * PolarLine((0, 0), blocker_zlen, blocker_angle)]
    blocker += [
        SagittaArc(
            (0, -outer.radius),
            blocker[0] @ 1,
            -Vertex(blocker[0] @ 1).distance_to((0, -outer.radius)) / 6,
        )
    ]
    blocker = make_face([*blocker, Line(blocker[0] @ 0, blocker[-1] @ 0)])

    flap_hinge_face = hinge_face + blocker
    # show_object(flap_hinge_face)
    return flap_hinge_face

def _flap(length, width_end, width_near, thickness, inner=True):
    top_left_point = ((width_near - width_end) / 2, length),
    face = Polygon(
        (0, 0),
        (width_near, 0),
        (width_end + (width_near - width_end) / 2, length),
        top_left_point,
        align=(Align.CENTER, Align.MIN),
    )
    flap = extrude(face, thickness)
    show_object(flap, name="flap")

    if inner:
        # Add a ridge to hold the next flap out in place when closed. Innermost
        # flap should have velcro to the PCB to hold it in place.
        edge = face.edges().sort_by(Axis.X).first
        ax = Axis(origin=edge @ 0, edge=edge)
        # Wire(Line(self.origin, location.position)).edge()
        # Create a plane such that the flap edge is X.
        plane = Plane(origin = edge @ 0.5, x_dir=ax.direction, y_dir=Axis.Y.direction)
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


case_hinge = extrude(Plane.XZ * (blocker), mechanism_length/2)
case_hinge += extrude(Plane.XZ * (outer_block + case_hinge_face), hinge_width_y)
case_hinge.move(Loc((0, mechanism_length/2,)))
case_hinge += mirror(case_hinge, Plane.XZ)
show_object(case_hinge)

bolthole_cutout = extrude(Plane.XZ * (bolthole), mechanism_length/2)
bolthole_cutout.move(Loc((0, mechanism_length/2,)))
bolthole_cutout += mirror(bolthole_cutout, Plane.XZ)

flaps = []
for i, (length, width) in enumerate(flap_lens):
    offset = hinge_width_y*(i+1) + 0.2*(i+1)
    flap_hinge_width = mechanism_length - offset*2
    flap_hinge = extrude(Plane.XZ * _flap_hinge_face(length), hinge_width_y)
    flap_hinge.move(Loc((0, -offset)))
    flap_hinge.move(Loc((0, mechanism_length/2)))
    flap_hinge += mirror(flap_hinge, Plane.XZ)
    # show_object(flap_hinge)
    flap = -Plane.YX * _flap(
        length, width, flap_hinge_width, flap_t, inner=i+1==len(flap_lens)
    )
    flap = flap.move(Loc((0, 0, -outer.radius)))
    flap += flap_hinge
    flap -= bolthole_cutout
    flaps.append(flap + flap_hinge)

# Cut smaller flaps out of the larger ones.
for i, flap in enumerate(flaps):
    for inner in flaps[i+1:]:
        flaps[i] -= scale(inner, ((1.01, 1.01, 1)))
    show_object(flaps[i], name=f"flaps{i}")
