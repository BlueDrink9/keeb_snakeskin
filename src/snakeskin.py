import argparse
import json
import subprocess
import sys
from pathlib import Path

from pygerber.gerberx3.api.v2 import GerberFile

from generate_pcb_case import default_params, generate_cases

script_dir = Path(__file__).parent
default_build_dir = script_dir / "build"


def main(split=False):
    args = parse_args()
    args.output_dir = resolve_output_dir(args.output_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    default_build_dir.mkdir(parents=True, exist_ok=True)

    if args.config:
        param_overrides = json.loads(args.config.read_text())
    else:
        param_overrides = {}
    param_overrides.update({k: v for k, v in vars(args).items() if k in default_params})

    if not args.dxf:
        dxf = gerber_to_dxf(args.input_file)
    else:
        dxf = args.input_file

    generate_cases(dxf, params=param_overrides)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate case files from Gerber edge cuts or PCB outline DXF."
    )

    parser.add_argument(
        "input_file",
        type=Path,
        help="Path to the input Gerber edge cuts file (.gm1) or (if --dxf is used) the DXF file.",
    )
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        help="Path to a JSON configuration file to override default parameters. Will be overridden by command line arguments.",
    )
    parser.add_argument(
        "--dxf",
        action="store_true",
        help="Treat the input file as a DXF file (bypasses Gerber parsing, removes need for inkscape)",
    )

    # Add all default params as arguments
    for key, value in default_params.items():
        parser.add_argument(
            f"--{key}",
            type=type(value),
            default=value,
            help=f"Override default value for {key}. Defaults to {value}.",
        )

    args = parser.parse_args()
    return args


def resolve_output_dir(output_path):
    output_path = Path(output_path)
    if output_path.is_absolute():
        return output_path.expanduser().resolve()
    else:
        return default_build_dir / output_path


def gerber_to_dxf(input_file):
    # First convert gerber to svg
    gerber = GerberFile.from_file(input_file).parse()
    svg_file = default_build_dir / "outline.svg"
    gerber.render_svg(svg_file)
    # Convert svg to dxf with inkscape
    dxf_file = default_build_dir / "outline.dxf"
    subprocess.run(["inkscape", str(svg_file), f"--export-filename={str(dxf_file)}"])
    return dxf_file


if __name__ == "__main__":
    main()
