from pathlib import Path
import os

if "__file__" in globals():
    script_dir = Path(__file__).parent
else:
    script_dir = Path(os.getcwd())


default_params = {
    "output_dir": script_dir / "../build",
    "split": True,
    "carrycase": True,
    "flush_carrycase_lip": True,
    "honeycomb_base": True,
    "strap_loop": False,
    "tenting_stand": False,
    "tiny_edge_rounding": False,
    "output_filetype": ".stl",
    "base_z_thickness": 3,
    "wall_xy_thickness": 2.81,
    "wall_z_height": 4.0,
    "z_space_under_pcb": 1,
    "wall_xy_bottom_tolerance": -0.2,
    "wall_xy_top_tolerance": 0.3,
    "cutout_position": 10,
    "cutout_width": 15,
    "additional_cutouts": [],
    "chamfer_len": 1,
    "honeycomb_radius": 6,
    "honeycomb_thickness": 2,
    "strap_loop_thickness": 4,
    "strap_loop_end_offset": 0,
    "strap_loop_gap": 5,
    "carrycase_tolerance_xy": 0.4,
    "carrycase_tolerance_z": 0.5,
    "carrycase_wall_xy_thickness": 3,
    "carrycase_z_gap_between_cases": 9 + 1,
    "carrycase_cutout_position": -90,
    "carrycase_cutout_xy_width": 20,
    "lip_len": 1.3,
    "lip_position_angles": [32, 158],
    "magnet_position": -90.0,
    "magnet_separation_distance": 0.81,
    "magnet_spacing": 10,
    "magnet_count": 10,
    "tent_legs": [[30, 50, 0]],
    "tent_hinge_width": 5,
    "tent_hinge_bolt_d": 3,  # M3
    "tent_hinge_bolt_l": 50,
    "tent_hinge_bolt_head_d": 6.94,
    "tent_hinge_nut_l": 2.4,
    "tent_hinge_nut_d": 5.5,
}
