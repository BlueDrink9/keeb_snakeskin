# Keyboard Snakeskin

Automatically generate a 3D printable case and magnetic carrycase for your custom split keyboard PCBs, from just the
outline. Also generates cases for other PCBs.

This case design generally uses a friction fit to get the PCB to stay in the
case. You can use hot glue instead if your printer tolerances are bad or
you want a sturdier/more permanent fit.
Cases have a removal cutout in one part of the wall for you to pull the case out
after pushing it in.

Inspired by and in collaboration with the [Compression keyboard](https://github.com/compressionKeyboards/compression4c) by Bennett Hermanoff. [More images here](https://compressionkeyboards.com/).

![case render](img/maizeless_snakeskin_honeycomb.png)

*Example case rendered from the
[maizeless](https://github.com/BlueDrink9/maizeless) PCB, with honeycomb base.*

![carrycase render](img/maizeless_snakeskin_carrycase.png)
![carrycase with case render](img/maizeless_snakeskin_honeycomb_in_carrycase.png)

*Carrycase with one case inside*. The carrycase is mirrored around the center, to
allow for two halves of a split board to be carried together.

## Install

`pip install --user keeb_snakeskin` installs this package and dependencies, and
should create a new executable `snakeskin` in your python scripts folder.

## Printing

These designs are designed to be printed without supports where possible. There
is only one severe (90 degree) overhang in the design, which is the first
blocker of the carrycase. This should be the only part that needs supports.
Setting your printer to only print overhangs over 70 degrees should be enough
to automatically support only this part. If you aren't printing the carrycase,
you shouldn't need supports unless your bridging performance on the magnets is
bad.

### Assembly

The only assembly required is inserting magnets. Check out [the Compression
video](https://www.youtube.com/watch?v=eRLCBHWX4eQ&t=905s) to get the general
idea.
Only the carrycase magnets should need glue, the case magnets should be held in
with the magnet alone.

## Usage

Overall:
1. In KiCad, export **just the edge cuts layer** as an SVG. Note that KiCad has two ways
to do this - plotting fabrication as an SVG, and exporting just edge as an SVG directly. The latter gives a more stable output.
2. Customise the design parameters for your board, either by create a config json or just passing the right arguments. At minimum you should tweak the cutout and magnet positioning for your board.
3. Run `snakeskin.py --config path/to/config.json path/to/edge_cuts.svg`.

### Input File

#### Getting the starting svg

In kicad, export just the edge.cuts layer as plot format `svg` (board only, not page).
Ensure coordinate output is mm, and all the 'plot' general options are
unchecked.

### Extra Options

Other than the case design parameters below, you can also input the following
arguments:
- `-o`, `--output`: Output directory or file path (default: "build")
- `-c`, `--config`: Path to the JSON configuration file

### Run

The program takes in the edge cuts from your gerber files to generate an
svg outline in the `build` folder, which is then used to render the basic shape for the case.
This could be an `svg` or  `.gm1` file. For example:

```python
snakeskin -s -o maizeless ~/src/keyboard_design/maizeless/pcb/build/maizeless-Edge_Cuts.gm1
```

The `-o` option specifies the output directory for your case files. If it is
not an absolute path, it will be created as a subfolder or file within the
`build` folder.
`-s` indicates this is a split board and the program should output a mirrored pair of files.
In this case the output would be `./build/maizeless/case.step` and `./build/maizeless/case_mirrored.stl`

### Specifying parameters

The following tables outline the possible variables you can specify for
your case creation.
To modify the paramters, pass a path to a `.json` file with
`-c path/to/cfg.json`, or pass individual parameters as command line arguments.
See `python snakeskin.py --help` for more information and for defaults.
The json should have anything you want to override from
defaults specified as a top level key:value. See `./preset_configs/` for
examples.

| Parameter name | Example value + unit| Description |
| -------------- | ------------- | ----------- |
| `split`| True | If True, generate mirrored pair of files for a split board |
| `carrycase` | True | Whether the output designs should incorporate the compression-style carrycase. Will affect the main case as well. |
| `honeycomb_base` | True | Make the base of the case a honeycombed/hexagon cage instead of solid |
| `output_filetype` | `.step` | `.step` or `.stl`. What filetype the case will be exported as. |
| `base_z_thickness` | 3 mm | Z thickness of bottom of the case, in mm |
| `wall_xy_thickness` | 3 mm | Thickness/width in X and Y of the wall around the edge of the PCB, holding it in the case.  Top and bottom wall tolerance will also affect the thickness that actually gets printed. Recommend 2 + `magnet_separation_distance` if you're using the carrycase, so the magnets don't rattle. If it's larger, you'll have to glue the magnets into the case as well as the carrycase. |
| `wall_z_height` | 4.0 mm | Z height of the wall **from the bottom of the PCB** (total case wall height will include z_space_under_pcb). The default includes room for magnets for the carrycase. If you aren't adding a carrycase, 1.6 is a good height for a standard PCB thickness if you just want to cover the pcb. |
| `z_space_under_pcb` | 1 mm | The size of the gap beneath the PCB, to leave room for through-hole pins, wires, hotswap sockets etc on the underside. Modify this to at least 1.85 if you are using kailh hotswap sockets under the PCB, for example. Also increase it if you want to have bigger tolerences for the fit and need more space for the walls to narrow in. By default, leaves just enough space for the pins of a choc switch directly soldered into a 1.6 mm pcb (which I measure stick out at about 0.83 mm). |
| `wall_xy_bottom_tolerance` | -0.3 mm | Amount of space between the PCB and the case walls near the case bottom, where PCB should sit (i.e. above z_space_under_pcb). Intended as a -ve value to get a tight friction fit. This is implemented with a scaling hack because of engine limitations, so I'd encourage measuring the result in a CAD program if you need it exact. |
| `wall_xy_top_tolerance` | 0.3 mm | Amount of space between the widest part of the walls (at the top) and the PCB outline. Adjust this depending on printer tolerances and how tight you want the friction fit. You may want to increase `z_space_under_pcb` if the difference between this and `wall_xy_bottom_tolerance` is large |
| `cutout_position` | 10 | Location  along the walls of the pcb case for the finger removal cutout, as an angle from the center of the case. Angle is between -180 and 180, with 0 pointing in +ve X axis, and -90 pointing in the -ve Y axis. Not every angle is possible, so your argument will be mapped to the closest acceptable angle. |
| `cutout_width` | 15 mm | Width of the removal cutout. May cut out more if the area isn't a straight line. |
| `honeycomb_radius` | 6 mm | Radius of the blank space hexagons for the honeycomb case base |
| `honeycomb_thickness` | 2 mm | Thickness of the bars (space between hexagons) of the honeycomb case base |

#### Carrycase options

If you are creating a carrycase (`"carrycase": true`), the following additional parameters are available in the same configuration:

| Parameter name | default value | description |
| -------------- | ------------- | ----------- |
| `carrycase_tolerance_xy` | 0.8 mm | Gap size between the pcb case and the carry case. May need playing around with on your printer to get a good fit. Err on the side of too large if you don't want to print too much. |
| `carrycase_tolerance_z` | 0.5 mm | Gap size between the pcb case and the carry case blockers. May need playing around with on your printer to get a good fit. Larger carrycase tolerances will make it easier to get the case into and out of the carrycase, at the cost of tightness of fit once it's in there. |
| `carrycase_wall_xy_thickness` | 2 mm | Thickness of the carrycase outer wall |
| `carrycase_z_gap_between_cases` | 8 mm | How much room to leave between each pcb (well, actually between the tops of the pcb case walls). By default this works for soldered in choc v1 switches with thin keycaps (and it will leave about 1 mm between them when they are in the case |
| `carrycase_cutout_position` | -90 | Location  along the walls of the carrycase for the finger removal cutout, as an angle from the center of the case. Angle is between -180 and 180, with 0 pointing in +ve X axis, and -90 pointing in the -ve Y axis. Not every angle is possible, so your argument will be mapped to the closest acceptable angle. Should be opposite the lip, on the same side as the magnets. |
| `carrycase_cutout_xy_width` | 15 mm | Width of the finger cutout for removing the boards from the case. May cut out more if the area isn't a straight line. |
| `lip_z_thickness` | 2 mm | Thickness of the lip cut out of the case that holds the non-magnet end to the carrycase |
| `lip_xy_len` | 1.5 mm | Length of the lip. |
| `lip_position_angles` | [160, 30] | A list of two angles, [start_angle, end_angle], that defines the position of the lip on the case. Measured in degrees from the positive X-axis. Positive angles are measured counterclockwise, with 0 degrees being the positive X-axis and 90 degrees being the positive Y-axis, -90 is the direction of the negative Y axis.The difference between the start and end angles must be less than 180 degrees. It is recommended to set the angles to cover a long, straight section of the case. This must be opposite to the location of the finger cutout on the carry case and the magnets. |
| `magnet_position` | -90 | Location  along the walls of the carrycase and case where the magnets will be centered, as an angle from the center of the case. Angle is between -180 and 180, with 0 pointing in +ve X axis, and -90 pointing in the -ve Y axis. |
| `magnet_separation_distance` | 0.3 mm | Amount of plastic separating the
magnets in the case from the magnets in the carrycase. How thick the case wall |
| `magnet_spacing` | 12 mm | Distance between the centers of magnets along the same wall of the case |
| `magnet_count` | 6 | Number of magnets per case (a split board and compression case will need 4* this amount to complete the build). |

#### More usage examples

Generate case files from an SVG to build/cool_board/:
```bash
snakeskin cool_board.svg -o build/cool_board
```

Generate case files from a Gerber file in build/:
```bash
snakeskin cool_board.gm1 -o build/
```
Generate case files with custom parameters:
```bash
snakeskin board_outline.svg -o output_dir -c params.json
```
