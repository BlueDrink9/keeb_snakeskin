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

# Create the walls
wall_outline = bd.offset(
    base_face,
    params["wall_xy_thickness"],
) - base_face


    # # Extrude the base face to create the bottom of the case
    # bottom = bd.extrude(base_face, params["base_z_thickness"])

def hollow_loft(faces):
    def bisecting_plane(f):
        return bd.Plane(origin=f.center()).rotated((0,-90,0))
    return (
            bd.loft([f.split(bisecting_plane(f)) for f in faces]) +
            bd.loft([f.split(bisecting_plane(f), keep=bd.Keep.BOTTOM) for f in faces])
    )

def weighted_avg(a, b, percent):
    """Average 'a' and 'b', weighted towards 'a' and away from 'b' by 'percent'"""
    return a*percent + b*(1-percent)

def slice_loft(start, end, start_offset, end_offset):
    wall_slices = [bd.offset(start, start_offset)]
    for i in range(10,0,-1):
        slice = (
            bd.Pos(0, 0, wall_height/i) *
                bd.offset(
                    end,
                    weighted_avg(
                        end_offset,
                        start_offset,
                        1/i
                    )
                )
        )
        wall_slices.append(slice)

# wall_outline_top = (
#     bd.Pos(0, 0, wall_height) *
#         bd.offset(wall_outline, params["wall_xy_top_tolerance"])
# )

# wall = hollow_loft(wall_slices)
base = bd.extrude(base_face, params["base_z_thickness"])
wall = bd.extrude(wall_outline, wall_height, taper=0)

# # show_object(wall_outline_top)
# # show_object(wall)
# shape = base + wall
# # f = shape.faces().sort_by()[-1].edges()[:-4].group_by(bd.Axis.Z)[-1]
# f = shape.faces().group_by(bd.Axis.Z)[-1].edges().group_by(bd.Axis.Z)[-1]
# # f = shape.edges().group_by(bd.Axis.Z)[-1]  # working chamfer
# # shape = bd.chamfer(f, length=0.5)
# # shape = bd.chamfer(shape.faces().sort_by().first.edges(), 1)
# show_object(shape)
# show_object(f)


with bd.BuildPart(bd.Plane.XY) as case:
    with bd.BuildSketch() as base_face:
        wires = outline.wires()
        bd.make_face(wires)

    with bd.BuildSketch() as wall_outline:
        bd.add(base_face)
        bd.offset(
            base_face.sketch,
            params["wall_xy_thickness"],
            mode=bd.Mode.SUBTRACT
        )
        # bd.add(base_face, mode=bd.Mode.SUBTRACT)
        # bd.make_face(wall_outline.sketch)
    print(wall_outline)
    # show_object(wall_outline.faces())

    wall_height = params["base_z_thickness"] + \
        params["z_space_under_pcb"] +  \
        params["wall_z_height"]
    # Extrude the base face to create the bottom of the case
    bottom = bd.extrude(amount= wall_height) #params["base_z_thickness"])

    # topf = case.faces().sort_by(bd.Axis.Z)[-1]
    # wall_outline_top = (
    #     bd.Plane.XY *
    #         bd.Pos(0, 0, wall_height) *
    #         bd.offset(wall_outline, params["wall_xy_top_tolerance"])
    # )
    # wall = bd.extrude(amount=wall_height)
    
    # wall = bd.loft(bd.Sketch() + [
    #     wall_outline,
    #     wall_outline_top
    # ])
    # # wall = b.extrude(wall_outline, wall_height, taper=0)

    # # shape = wall + bottom
    # shape = wall_outline_top
    # # wall = (
    # #     wall_outline
    # #     .extrude(wall_height)
    # #     .translate((0, 0, params["base_z"]))
    # # )

# show_object(case.part)

# topf = case.part.faces().sort_by().last
# part = bd.offset(case.part, amount=-0.999, openings=topf)
# show_object(part)


def generate_case(svg_file, params=None):
    if not params:
        params = {} 
    default_params.update(params)
    params = default_params

    outline = bd.import_svg(svg_file)

    base_face = bd.make_face(outline.wires())
    return base_face

    # Extrude the base face to create therbottom of the case
    bottom = bd.extrude(base_face, params["base_z_thickness"])

    # Create the walls
    wall_outline = bd.offset(
        base_face,
        params["wall_xy_thickness"]
    ) - base_face

    wall_height = params["base_z_thickness"] + \
        params["z_space_under_pcb"] +  \
        params["wall_z_height"]
    wall_outline_top = (
        bd.Plane.XY *
            bd.Pos(0, 0, wall_height) *
            bd.offset(wall_outline, params["wall_xy_top_tolerance"])
    )
    
    wall = bd.loft(bd.Sketch() + [
        wall_outline,
        wall_outline_top
    ])
    # wall = b.extrude(wall_outline, wall_height, taper=0)

    # shape = wall + bottom
    shape = wall_outline_top
    # wall = (
    #     wall_outline
    #     .extrude(wall_height)
    #     .translate((0, 0, params["base_z"]))
    # )

    return shape


    return s
    # return loft
    # Extrude the outline to the base thickness
    base = outline.toPending().extrude(params["base_z"])
    # return base

    # return outline.wires()
    s = cq.Sketch()
    # s = s.importDXF(dxf_file)
    # s = s.face(outline.wires().val())
    s = s.circle(5)
    # return s.finalize()
    result = (
        cq.Workplane()
        .sketch()
        .importDXF(dxf_file)
        .finalize()
        .extrude(50)
    )
    return result

    wires = base.wires("<Z").vals()

    wires = cq.sortWiresByBuildOrder(wires)
    base2 = cq.Workplane('XY')

    for wirelist in (wires):
        for wire in wirelist:
            base2._addPendingWire(wire)

    base2.consolidateWires()
    base2.extrude(30.0)
    return base2

    # # Create the walls
    # wall_outline = outline.offset2D(params["wall_xy_thickness"])
    # wall_height = params["z_space_under_pcb"] + params["wall_z_height"]
    # wall = (
    #     wall_outline
    #     .extrude(wall_height)
    #     .translate((0, 0, params["base_z"]))
    # )

    # # Combine the base and walls
    # case_shape = base.union(wall)

    # # Apply tolerances to the walls
    # bottom_tolerance = params["wall_xy_bottom_tolerance"]
    # top_tolerance = params["wall_xy_top_tolerance"]
    # case_shape = (
    #     case_shape
    #     .faces(">Z")
    #     .workplane()
    #     .offset2D(bottom_tolerance, kind="arc")
    #     .extrude(params["z_space_under_pcb"], combine=False)
    #     .faces(">Z")
    #     .workplane()
    #     .offset2D(top_tolerance, kind="arc")
    #     .extrude(params["wall_z_height"], combine=True)
    # )

    # # Create the removal cutout
    # cutout_angle_rad = math.radians(params["cutout_angle"])
    # cutout_width = params["cutout_width"]
    # cutout_length = params["wall_xy_thickness"] * 2
    # cutout = (
    #     cq.Workplane("XY")
    #     .moveTo(0, 0)
    #     .rect(cutout_width, cutout_length)
    #     .extrude(wall_height)
    #     .rotate((0, 0, 0), (0, 0, 1), cutout_angle_rad)
    #     .translate((0, 0, params["base_z"]))
    # )
    # case_shape = case_shape.cut(cutout)

    # # Generate the case files
    # base_name = output_dir.stem
    # if split:
    #     # Generate mirrored pair of files for split board
    #     case_shape_left = case_shape.mirror('XZ')
    #     case_shape_right = case_shape
    #     case_file_left = output_dir.with_name(f'{base_name}_left.step')
    #     case_file_right = output_dir.with_name(f'{base_name}_right.step')
    #     cq.exporters.export(case_shape_left, str(case_file_left))
    #     cq.exporters.export(case_shape_right, str(case_file_right))
    # else:
    #     # Generate a single case file
    #     case_file = output_dir.with_suffix('.step')
    #     cq.exporters.export(case_shape, str(case_file))

    # return case_shape

# # Offset the base face inwards to create the inner wall
# wall_xy_bottom_tolerance = -0.3  # in mm
# inner_wall_face = base_face.offset(wall_xy_bottom_tolerance)

# # Offset the base face outwards to create the outer wall
# wall_xy_thickness = 2  # in mm
# outer_wall_face = base_face.offset(wall_xy_thickness)

# # Create the wall by lofting between the inner and outer wall faces
# wall_z_height = 2  # in mm
# wall = loft(inner_wall_face, outer_wall_face).to(wall_z_height)

# # Combine the bottom and the wall to create the case
# case = bottom.add(wall)

# # Create a cutout for PCB removal
# cutout_angle = 0  # in degrees
# cutout_width = 5  # in mm
# cutout_box = Box(cutout_width, wall_z_height, centered=False)
# cutout_box = cutout_box.rotate(Vector(0, 0, 1), cutout_angle)
# case = case.cut(cutout_box)

# # Display the case
# show_object(case)

    # return outline

if __name__ in ["__cq_main__", "temp"]:
    # For testing via cq-editor
    # object = generate_case("build/outline.svg")
    pass
    # show_object(object)
