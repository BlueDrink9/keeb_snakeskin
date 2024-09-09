# Keyboard Snakeskin

Generate 3D printable cases for custom keyboard PCBs.

This case design generally uses a friction fit to get the PCB to stay in the case. You can use hot glue instead if your printer tolerances aren't great or you want a sturdier fit.
Cases have a removal cutout in one part of the wall for you to pull the case out
after pushing in.

## Install

Conversion of gerber to `dxf` for cadquery import requires inkscape to be
on your PATH.
Please install it through your system package manager.
Alternatively, see usage option for 'from dxf'.

`pip install --user keeb_snakeskin` installs this package and dependencies, and
should create a new executable `snakeskin` in your python scripts folder.

## Usage

### Input File

#### Getting the starting svg

In kicad, export just the edge.cuts layer as svg (board only, not page).

### Options

- `-o`, `--output`: Output directory or file path (default: "build")
- `-s`, `--split`: Generate mirrored pair of files for split board
- `-c`, `--config`: Path to the JSON configuration file
- `--dxf`: Treat the input file as a DXF file (bypasses Gerber parsing, removes need for inkscape)

### Run

The program takes in the edge cuts from your gerber files to generate an
svg outline in the `build` folder, which is then used to render the basic shape for the case.
This should be a `.gm1` file. For example:

```python
snakeskin -s -o maizeless ~/src/keyboard_design/maizeless/pcb/build/maizeless-Edge_Cuts.gm1
```

The `-o` option specifies the output directory for your case files. If it is not an absolute path, it will be created as a subfolder or file within `build/`.
`-s` indicates this is a split board and the program should output a mirrored pair of files, `case_left` and `case_right`.
In this case the output would be `./build/maizeless/case_left.step` and `./build/maizeless/case_right.step` 

Alternatively, if you already have a `.dxf` outline of your pcb, you can bypass the svg conversion step (removing the need for inkscape) and specify it directly with
`--dxf path/to/outline.dxf`

### Specifying case parameters

The following table outlines the possible variables you can specify for
your case creation.
To modify the paramters, pass a path to a `.json` file with
`-c path/to/cfg.json`. This should have anything you want to override from
defaults specified as a top level key:value, for example:
```json
{
    "base_z": 4,
    "wall_xy_thickness": 2.5,
    "cutout_width": 6
}
```


| Parameter name | default value | description |
| -------------- | ------------- | ----------- |
| `base_z_thickness` | 3 mm | Z thickness of bottom of the case, in mm |
| `wall_xy_thickness` | 2 mm | Thickness/width in X and Y of the wall around the edge of the PCB, holding it in the case |
| `wall_z_height` | 1.6 mm | Z height of the wall from the bottom of the PCB. The default is a standard PCB thickness, and is unlikely to need modifying. |
| `z_space_under_pcb` | 1 mm | The size of the gap beneath the PCB, to leave room for through-hole pins, wires, hotswap sockets etc on the underside. Modify this to at least 1.85 if you are using kailh hotswap sockets under the PCB, for example. Also increase it if you want to have bigger tolerences for the fit and need more space for the walls to narrow in. By default, leaves just enough space for the pins of a choc switch directly soldered into a 1.6 mm pcb (which I measure stick out at about 0.83 mm). |
| `wall_xy_bottom_tolerance` | -0.3 mm | Amount of space between the narrowest part of the walls (at the bottom) and the PCB outline. Use -ve values for friction fit |
| `wall_xy_top_tolerance` | 0.3 mm | Amount of space between the widest part of the walls (at the top) and the PCB outline. Adjust this depending on printer tolerances and how tight you want the friction fit. You may want to increase `z_space_under_pcb` if the difference between this and `wall_xy_bottom_tolerance` is large |
| `cutout_position` | 0.0 | Location, as a percentage, along the walls of the pcb case for the finger removal cutout. Between 0 and 1, representing a percentage along the walls. Play with it until you find a good spot for it. Known issues: Some faces, for whatever reason, will rarely rotate the cutout sideways. Choosing another position seems to be the only fix. |
| `cutout_width` | 15 mm | Width of the removal cutout. May cut out more if the area isn't a straight line. |
| `carrycase_tolerance` | 0.3 mm | Gap size between the pcb case and the carry case. Will probably need playing around with on your printer to get a good fit. Err on the side of too large if you don't want to print too much. |
| `carrycase_wall_xy_thickness` | 2 mm | Thickness of the carrycase outer wall |
| `carrycase_z_gap_between_cases` | 8 mm | How much room to leave between each pcb (well, actually between the tops of the pcb case walls). By default this works for soldered in choc v1 switches with thin keycaps (and it will leave about 2 mm between them when they are in the case |
| `carrycase_cutout_position` | 0.0 | Location, as a percentage, along the walls of the carrycase for the finger removal cutout. Between 0 and 1, representing a percentage along the case. Play with it until you find a good spot for it. |
| `carrycase_cutout_width` | 5 mm | Width of the removal cutout. May cut out more if the area isn't a straight line. |

### More examples

Generate case files from a Gerber file in build/cool_board/:
```bash
snakeskin cool_board.gbr -o cool_board
```

Generate case files from a DXF file, outputting to the specified dir:
```bash
snakeskin cool_board.dxf --dxf -o ~/Downloads/cool_board
```

Generate case files with custom parameters:
```bash
snakeskin input.gbr -o output_dir -c params.json
```
