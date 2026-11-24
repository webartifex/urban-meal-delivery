"""Utilities for drawing maps with `folium`."""

import colorsys

import numpy as np
from matplotlib import colors


def make_random_cmap(
    n_colors: int, bright: bool = True,  # pragma: no cover
) -> colors.LinearSegmentedColormap:
    """Create a random `Colormap` with `n_colors` different colors.

    Args:
        n_colors: number of of different colors; size of `Colormap`
        bright: `True` for strong colors, `False` for pastel colors

    Returns:
        colormap
    """
    np.random.seed(42)

    if bright:
        hsv_colors = [
            (
                np.random.uniform(low=0.0, high=1),
                np.random.uniform(low=0.2, high=1),
                np.random.uniform(low=0.9, high=1),
            )
            for _ in range(n_colors)
        ]

        rgb_colors = []
        for color in hsv_colors:
            rgb_colors.append(colorsys.hsv_to_rgb(*color))

    else:
        low = 0.0
        high = 0.66

        rgb_colors = [
            (
                np.random.uniform(low=low, high=high),
                np.random.uniform(low=low, high=high),
                np.random.uniform(low=low, high=high),
            )
            for _ in range(n_colors)
        ]

    return colors.LinearSegmentedColormap.from_list(
        'random_color_map', rgb_colors, N=n_colors,
    )


def rgb_to_hex(*args: float) -> str:  # pragma: no cover
    """Convert RGB colors into hexadecimal notation.

    Args:
        *args: percentages (0% - 100%) for the RGB channels

    Returns:
        hexadecimal_representation
    """
    red, green, blue = (
        int(255 * args[0]),
        int(255 * args[1]),
        int(255 * args[2]),
    )
    return f'#{red:02x}{green:02x}{blue:02x}'  # noqa:WPS221
