import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from default_params import default_params
from generate_pcb_case import generate_cases

script_dir = Path(__file__).parent
default_build_dir = default_params["output_dir"]


def main():
    args = parse_args()
    if args.output_dir:
        args.output_dir = resolve_output_dir(args.output_dir)
        args.output_dir.mkdir(parents=True, exist_ok=True)
    default_build_dir.mkdir(parents=True, exist_ok=True)

    if args.config:
        config = Path(args.config).expanduser()
        print(f"Reading config from {str(config)}...")
        param_overrides = json.loads(config.read_text())
    else:
        param_overrides = {}
    for k, v in vars(args).items():
        if k not in default_params and k not in ["input_file", "config"]:
            print(f"Warning: Unknown parameter '{k}'")
        elif v is not None:
            param_overrides[k] = v

    input_file = Path(args.input_file).expanduser()
    if input_file.suffix == ".gm1":
        svg = gerber_to_svg(input_file)
    elif input_file.suffix == ".svg":
        svg = input_file
    elif input_file.suffix == ".kicad_pcb":
        svg = pcb_to_svg(input_file)
    else:
        # Exit with error.
        sys.exit(
            f"Unknown file type (please check the readme): {args.input_file.suffix}"
        )

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
            # default=value,
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
    from pygerber.gerberx3.api.v2 import GerberFile
    # First convert gerber to svg
    gerber = GerberFile.from_file(input_file).parse()
    svg_file = default_build_dir / "outline.svg"
    gerber.render_svg(svg_file)
    return svg_file


def pcb_to_svg(input_file):
    """Run kicad-cli to convert the input pcb to svg, and check it ran correctly"""
    # For some reason kicad-cli (or maybe just the flatpak version) can't write
    # to tmp files.
    output_path = default_build_dir / "outline.svg"

    # Define the kicad-cli command
    command = [
        "kicad-cli",
        "pcb",
        "export",
        "svg",
        "--exclude-drawing-sheet",
        "--drill-shape-opt",
        "1",
        "--layers",
        "Edge.Cuts",
        "--output",
        str(output_path),
        str(input_file),
    ]
    try:
        print("Running kicad-cli to convert .kicad_pcb file into svg")
        print(output_path)
        subprocess.run(command, check=True, text=True)
        # print(list(tmpdir.walk()))
        return output_path
    except FileNotFoundError:
        print(
            "Error: The 'kicad-cli' command was not found. Please ensure KiCad is installed and the executable is in your PATH."
        )
        sys.exit(1)
    except OSError as e:
        if e.errno == 8:  # Exec format error
            print(
                "Error: Unable to execute 'kicad-cli'. This may be due to an architecture mismatch or a corrupted executable."
            )
        else:
            print(f"Error: An unexpected OS error occurred: {e}")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print("An error occurred while running kicad-cli:", e)
        print("Error output:", e.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
