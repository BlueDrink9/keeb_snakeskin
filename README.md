# Keyboard Snakeskin

Generate 3D printable cases for custom keyboard PCBs.

## Install

Conversion of gerber to `dxf` for cadquery import requires inkscape to be
on your PATH.
Please install it through your system package manager.
Alternatively, see usage option for 'from dxf'.

`pip install --user keeb_snakeskin` installs this package and dependencies, and
should create a new executable `snakeskin` in your python scripts folder.

## Usage

The program takes in the edge cuts from your gerber files to generate an
svg outline in the `build` folder, which is then used to render the basic shape for the case.
This should be a `.gm1` file. For example:

```python
snakeskin -s -o maizeless ~/src/keyboard_design/maizeless/pcb/build/maizeless-Edge_Cuts.gm1
```

The `-o` option specifies the output directory for your case files. If it is not an absolute path, it will be created as a subfolder or file within `build/`.
`-s` indicates this is a split board and the program should output a mirrored pair of files, `case_left` and `case_right`.
In this case the output would be `./build/maizeless/case_left.step` and `./build/maizeless/case_right.step` 


