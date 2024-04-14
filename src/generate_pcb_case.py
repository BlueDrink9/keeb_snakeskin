import cadquery as cq

default_params = {
        "base_z": 3,
        "wall_xy_thickness": 2,
        "wall_z_height": 1.6,
        "z_space_under_pcb": 1,
        "wall_xy_bottom_tolerance": -0.3,
        "wall_xy_top_tolerance": 0.3,
        "cutout_angle": 0,
        "cutout_width": 5
}


def generate_case(dxf_file, params=None):
    if not params:
        params = {} 
    params = default_params.update(params)
    outline = cq.importers.importDXF(dxf_file)


    return outline

if __name__ == "__cq_main__":
    # For testing via cq-editor
    object = generate_case("test.dxf")

