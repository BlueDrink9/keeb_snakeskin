from build123d import *
from generate_pcb_case import default_params
def xp(f, name):
    export_stl(f.face().thicken(0.5), "build/" + name + ".stl")

case_w = 56.8
case_h = 8
case = Rectangle(case_w, case_h)

cc_wall = 2
tol = 2*default_params["carrycase_tolerance_xy"]
cc_w = case_w + tol + cc_wall
cc_h = 8
cc = Rectangle(cc_w, cc_h) + Rectangle(cc_w, cc_h/2 + 2, align=(Align.CENTER, Align.MAX))
cc -= Rectangle(case_w + tol, case_h)
top_edge = cc.edges().group_by(Axis.Y)[-1].sort_by(Axis.X).first

lip_h = default_params["lip_z_thickness"]
anchor_loc = Location(top_edge @ 0)
lip_anchor = Rectangle(top_edge.length, lip_h, align=Align.MIN).located(anchor_loc)
cc += lip_anchor

lip_w = default_params["lip_xy_len"]
lip_loc = top_edge @ 0 + Vector(top_edge.length, 0)
lip = Rectangle(lip_w, lip_h, align=Align.MIN)

lip = lip.located(Location(lip_loc))

cc -= case

cc = cc + lip

case.move(Location((tol/2, 0, 0)))

# show_object(case, name="case")
# show_object(cc, name="cc")
test_name = "tol_test_lip_above"
xp(case, test_name + "_case")
xp(cc, test_name + "_cc")

cc = cc - lip
lip = lip.located(Location(lip_loc - Vector(0, lip_h, 0)))
cc = cc + lip
case = case - cc
show_object(case, name="case_2")
show_object(cc, name="cc_2")
test_name = "tol_test_lip_inside"
xp(case, test_name + "_case")
xp(cc, test_name + "_cc")

