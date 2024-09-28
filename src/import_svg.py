import copy
import os
from math import degrees, sqrt
from pathlib import Path
from typing import TextIO, Union, Optional
import svgpathtools as svg

from build123d.build_enums import CenterOf, Mode, AngularDirection
from build123d.build_line import BuildLine
from build123d.geometry import Color, Location
from build123d.objects_curve import Line, EllipticalCenterArc
from build123d.operations_generic import add, offset, mirror
from build123d.topology import (
    Compound,
    Edge,
    Face,
    Shape,
    ShapeList,
    Shell,
    Solid,
    Vertex,
    Wire,
    downcast,
)

def import_svg_as_forced_outline(
    svg_file: Union[str, Path, TextIO],
    reorient: bool = True,
    tolerance: float = 0.01,
    extra_cleaning=False,
) -> Wire:
    """Import an SVG and apply cleaning operations to return a closed wire outline, if possible. Useful for SVG outlines that are actually made of thin shapes or slightly disconnected paths. May fail on more complex shapes.

    * Removes duplicate lines, including ones that are reverses of the other, within a tolerance level (useful for 'outlines' that are actually very thin shapes)
    * Sorts paths such that they are end to start in order of distance, flipping them if needed to line up start to end
    * Goes through each path and creates the next one such that it starts at the end of the last one
    * Ensures the last and first paths are connected


    Args:
        svg_file (Union[str, Path, TextIO]): svg file
        reorient (bool, optional): Center result on origin by bounding box, and
        flip objects to compensate for svg orientation (so the resulting wire
        is the same way up as it looks when opened in an SVG viewer). Defaults
        to True.
        tolerance (float, optional): Amount of tolerance to use for comparing paths. Defaults to 0.01.
        extra_clean (bool, optional): Do some extra cleaning, including skipping tiny paths and some slight rounding off of corners, which may help smooth out tiny features in the outline. Defaults to False.

    Raises:
        ValueError: If an unknown path type is encountered.
        FileNotFoundError: the input file cannot be found.

    Returns:
        Wire: Forcefully connected SVG paths as a wire.
    """

    def point(path_point):
        return (path_point.real, path_point.imag)

    paths = svg.svg2paths(svg_file)[0]
    curves = []
    for p in paths:
        curves.extend(p)
    curves = _remove_duplicate_paths(curves, tolerance=tolerance)
    curves = _sort_curves(curves)
    first_line = curves[0]
    with BuildLine() as bd_l:
        line_start = point(first_line.start)
        for i, p in enumerate(curves):
            if extra_cleaning and p.length() < tolerance:
                # Filter out tiny edges that may cause issues with OCCT ops
                continue
            line_end = point(p.end)
            if i == len(curves) - 1:
                # Forcefully reconnect the end to the start.
                # Note: This won't quite work if the last path is an arc,
                # but make_face should still sort it out. Once
                # EllipticalStartArc is released in build123d, this can be
                # fixed.
                line_end = point(first_line.start)
            else:
                if (
                    extra_cleaning
                    and Vertex(line_end).distance(Vertex(line_start)) < tolerance
                ):
                    # Skip this path if it's really short, just go straight
                    # to the next one.
                    continue
            if isinstance(p, svg.Line):
                edge = Line(line_start, line_end)
            elif isinstance(p, svg.Arc):
                start, end = sorted(
                    [
                        p.theta,
                        p.theta + p.delta,
                    ]
                )
                if p.delta < 0.0:
                    dir_ = AngularDirection.CLOCKWISE
                else:
                    dir_ = AngularDirection.COUNTER_CLOCKWISE
                edge = EllipticalCenterArc(
                    center=point(p.center),
                    x_radius=p.radius.real,
                    y_radius=p.radius.imag,
                    start_angle=start,
                    end_angle=end,
                    rotation=degrees(p.phi),
                    angular_direction=dir_,
                    mode=Mode.PRIVATE,
                )
                add(edge.move(Location(line_start - edge @ 0)))

            else:
                print("Unknown path type for ", p)
                raise ValueError
            line_start = edge @ 1

    wire = bd_l.wire()
    if reorient:
        wire = wire.move(Location(-wire.center(center_of=CenterOf.BOUNDING_BOX)))
        wire = mirror(wire)

    if extra_cleaning:
        # Going through a round of offset out, then back in, rounds off
        # internally projecting corners just a little, and seems to help reduce the
        # creation of invalid shapes.
        # This won't prevent objects from fitting within the outline, just place tiny gaps in some small concave (from the perspective of the gap) corners.
        off = 1.0
        wire = offset(offset(wire, off), -off)
    return wire


def _sort_curves(curves):
    """Return list of paths sorted and flipped so that they are connected end to end as the list iterates."""
    if not curves:
        return []

    def euclidean_distance(p1, p2):
        return sqrt((p1.real - p2.real) ** 2 + (p1.imag - p2.imag) ** 2)

    # Start with the first curve
    sorted_curves = [curves.pop(0)]

    while curves:
        last_curve = sorted_curves[-1]
        last_end = last_curve.end

        # Find the closest curve to the previous end point.
        closest_curve, closest_distance, flip = None, float("inf"), False
        for curve in curves:
            dist_start = euclidean_distance(last_end, curve.start)
            dist_end = euclidean_distance(last_end, curve.end)
            # If end is closer than start, flip the curve right way around.
            if dist_start < closest_distance:
                closest_curve, closest_distance, flip = curve, dist_start, False
            if dist_end < closest_distance:
                closest_curve, closest_distance, flip = curve, dist_end, True

        # Flip the curve if necessary
        if flip:
            flipped = _reverse_svg_curve(closest_curve)
            sorted_curves.append(flipped)
        else:
            sorted_curves.append(closest_curve)
        curves.remove(closest_curve)

    return sorted_curves


def _remove_duplicate_paths(paths, tolerance=0.01):
    """Remove paths that are identical to within the given positional and
    parameter tolerance limit, including similar but reversed paths."""
    cleaned_paths = []

    for path in paths:
        # Check if a similar path already exists in the cleaned list (either
        # forward or reversed)
        flipped = _reverse_svg_curve(path)
        if any(
            _are_paths_similar(path, cleaned_path, tolerance)
            or _are_paths_similar(flipped, cleaned_path, tolerance)
            for cleaned_path in cleaned_paths
        ):
            # Skip this path if a similar one is already in the list
            continue
        cleaned_paths.append(path)

    return cleaned_paths


def _are_paths_similar(path1, path2, tolerance=0.01):
    """Compares two SVG paths, based on type, start/end points, length, and Arc attributes."""

    if type(path1) != type(path2):
        return False

    def lengths_are_close(p1, p2):
        return (
            abs(p1.length() - p2.length()) / max(p1.length(), p2.length()) < tolerance
        )

    if not lengths_are_close(path1, path2):
        return False

    def points_are_close(p1, p2):
        return abs(p1.real - p2.real) < tolerance and abs(p1.imag - p2.imag) < tolerance

    # Handle reversed paths by checking both normal and reversed orientation
    if not points_are_close(path1.start, path2.start) and points_are_close(
            path1.end, path2.end
        ):
        return False

    # Additional checks for arcs (to handle radius, rotation, etc.)
    if isinstance(path1, svg.Arc) and isinstance(path2, svg.Arc):
        arc_attributes = [
            "radius",
            "phi",
            "theta",
            "delta",
            "rotation",
            "center",
            "large_arc",
            "sweep",
        ]

        for attr in arc_attributes:
            try:
                if abs(vars(path1)[attr] - vars(path2)[attr]) > tolerance:
                    return False
            except KeyError:
                continue

    return True


def _reverse_svg_curve(c):
    c = copy.deepcopy(c)
    t = c.start
    c.start = c.end
    c.end = t
    if isinstance(c, svg.Arc):
        # Flipping ElipticalArcs is a bit more complicated.
        # Calculate the new theta as the original end angle.
        new_theta = c.theta + c.delta
        # Reverse the delta.
        c.delta = -c.delta
        # Set theta to the new start angle.
        c.theta = new_theta
    return c
