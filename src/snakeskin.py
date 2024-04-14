import sys
import argparse
from pathlib import Path
import subprocess
import json


from generate_pcb_case import generate_case

from pygerber.gerberx3.api.v2 import GerberFile
import cadquery as cq

script_dir = Path(__file__).parent
build_dir = script_dir / 'build'

def main(split=False):
    args = parse_args()
    output_dir = resolve_output_dir(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    build_dir.mkdir(parents=True, exist_ok=True)
    
    if args.config:
        param_overrides = json.loads(args.config.read_text())
    else:
        param_overrides = None

    if not args.dxf:
        dxf = gerber_to_dxf(args.input_file)
    else:
        dxf = args.input_file
    step = generate_case(dxf, params=param_overrides)
    write_case(step, output_dir, split=args.split)


def parse_args():
    parser = argparse.ArgumentParser(description="Generate case files from Gerber edge cuts or PCB outline DXF.")
    parser.add_argument(
        "input_file", type=Path,
        help="Path to the input Gerber edge cuts file (.gm1) or (if --dxf is used) the DXF file.",

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
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        help="Path to the JSON configuration file"
    )
    parser.add_argument(
        "--dxf",
        action="store_true",
        help="Treat the input file as a DXF file (bypasses Gerber parsing, removes need for inkscape)",
    )
    args = parser.parse_args()
    return args


def resolve_output_dir(output_path):
    output_path = Path(output_path)
    if output_path.is_absolute():
        return output_path.expanduser().resolve()
    else:
        return build_dir / output_path


def gerber_to_dxf(input_file):
    # First convert gerber to svg
    gerber = GerberFile.from_file(input_file).parse()
    svg_file = build_dir / 'outline.svg'
    gerber.render_svg(svg_file)
    # Convert svg to dxf with inkscape
    dxf_file = build_dir / 'outline.dxf'
    subprocess.run(["inkscape", str(svg_file), f"--export-filename={str(dxf_file)}"])
    return dxf_file


def write_case(case_shape, output_dir, split=False):
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
