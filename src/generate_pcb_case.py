import build123d as bd

default_params = {
        "base_z_thickness": 3,
        "wall_xy_thickness": 2,
        "wall_z_height": 1.6,
        "z_space_under_pcb": 1.6,
        "wall_xy_bottom_tolerance": -0.3,
        "wall_xy_top_tolerance": 0.3,
        "cutout_angle": 0,
        "cutout_width": 5
}

params = default_params

outline = bd.import_svg("build/outline.svg")

# For testing
# outline = bd.Rectangle(30,30).locate(bd.Location((40, 40, 0)))

# Round trip from outline to wires to face to wires to connect the disconnected
# edges that an svg gets imported with.
outline = bd.make_face(outline.wires()).wires()[0]
base_face = bd.make_face(outline)

wall_height = params["base_z_thickness"] + \
    params["z_space_under_pcb"] +  \
    params["wall_z_height"]

base = bd.extrude(base_face, params["base_z_thickness"])
wall_outer = bd.offset(
    base_face,
    params["wall_xy_thickness"],
)
inner_cutout = bd.extrude(base_face, wall_height, taper=-9.9)
wall = bd.extrude(wall_outer, wall_height) - inner_cutout
shape = wall + base
show_object(shape)


def generate_case(svg_file, params=None):
    if not params:
        params = {} 
    default_params.update(params)
    params = default_params

    outline = bd.import_svg(svg_file)
    return

if __name__ in ["__cq_main__", "temp"]:
    # For testing via cq-editor
    # object = generate_case("build/outline.svg")
    pass
    # show_object(object)
