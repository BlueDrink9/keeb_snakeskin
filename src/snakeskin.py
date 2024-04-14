import sys
import argparse
from pathlib import Path
import subprocess

from pygerber.gerberx3.api.v2 import GerberFile
import cadquery as cq

script_dir = Path(__file__).parent
build_dir = script_dir / 'build'

def main(split=False):
    args = parse_args()
    input_file = args.input_file
    split = args.split
    output_dir = resolve_output_dir(args.output)

    output_dir.mkdir(parents=True, exist_ok=True)
    build_dir.mkdir(parents=True, exist_ok=True)
    outline = create_outline(input_file, output_dir)
    generate_case(outline, output_dir, split=split)

def parse_args():
    parser = argparse.ArgumentParser(description="Generate case files from Gerber.")
    parser.add_argument(
        "input_file", type=Path, help="Path to the input Gerber file (.gbr)"
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=build_dir,
        help="Output directory (or subdirectory of build dir)",
    )
    parser.add_argument(
        "-s",
        "--split",
        action="store_true",
        help="Generate mirrored pair of files for split board",
    )
    args = parser.parse_args()
    return args


def resolve_output_dir(output_path):
    output_path = Path(output_path)
    if output_path.is_absolute():
        return output_path
    else:
        return build_dir / output_path


def create_outline(input_file, output_dir):
    gerber = GerberFile.from_file(input_file).parse()
    svg_file = build_dir / 'outline.svg'
    gerber.render_svg(svg_file)
    return svg_file

def generate_case(svg_file, output_dir, split=False):
    dxf_file = output_dir / 'outline.dxf'
    subprocess.run(["inkscape", str(svg_file), f"--export-filename={str(dxf_file)}"])
    case_shape = cq.importers.importDXF(dxf_file)

    if split:
        # Generate mirrored pair of files for split board
        case_shape_right = case_shape.mirror('XZ')
        case_file_right = output_dir / 'case_right.step'
        cq.exporters.export(case_shape_right, str(case_file_right))
        case_file = output_dir / 'case_left.step'
    else:
        case_file = output_dir / 'case.step'
    cq.exporters.export(case_shape, str(case_file))

if __name__ == '__main__':
    main()
