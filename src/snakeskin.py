import argparse
import json
import subprocess
import sys
from pathlib import Path

from pygerber.gerberx3.api.v2 import GerberFile

from generate_pcb_case import default_params, generate_cases

script_dir = Path(__file__).parent
default_build_dir = script_dir / "build"


def main():
    args = parse_args()
    args.output_dir = resolve_output_dir(args.output_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    default_build_dir.mkdir(parents=True, exist_ok=True)

    if args.config:
        config = Path(args.config).expanduser()
        print(f"Reading config from {str(config)}...")
        param_overrides = json.loads(config.read_text())
    else:
        param_overrides = {}
    param_overrides.update({k: v for k, v in vars(args).items() if k in default_params})

    if args.input_file.suffix == ".gm1":
        svg = gerber_to_svg(args.input_file)
    elif args.input_file.suffix == ".svg":
        svg = args.input_file
    else:
        # Exit with error.
        sys.exit(f"Unknown file type (please check the readme): {args.input_file.suffix}")


    generate_cases(svg, user_params=param_overrides)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate case files from Gerber edge cuts or PCB outline SVG."
    )

    parser.add_argument(
        "input_file",
        type=Path,
        help="Path to the input Gerber edge cuts file (.gm1) or an SVG outline file.",
    )
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        help="Path to a JSON configuration file to override default parameters. Any parameters that are also provided as CLI args will take the CLI value.",
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


def gerber_to_svg(input_file):
    # First convert gerber to svg
    gerber = GerberFile.from_file(input_file).parse()
    svg_file = default_build_dir / "outline.svg"
    gerber.render_svg(svg_file)
    return svg_file


if __name__ == "__main__":
    main()
