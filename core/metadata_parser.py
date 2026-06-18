# -*- coding: utf-8 -*-
"""Landsat metadata (MTL) file parser."""

from .constants import LANDSAT_META_KEYS


def parse_landsat_metadata(path, sensor, gain=''):
    """Parse a Landsat MTL metadata file and return required calibration values.

    :param path: Path to the metadata text file.
    :param sensor: Sensor identifier ('Landsat 5', 'Landsat 7', or 'Landsat 8').
    :param gain: Gain setting for Landsat 7 ('High' or 'Low'). Ignored for other sensors.
    :returns: Dictionary of calibration values.
    :raises ValueError: If sensor/gain combination is not supported.
    """
    raw = {}
    with open(path, 'r') as f:
        for line in f:
            if '=' in line:
                parts = line.split('=')
                raw[parts[0].strip()] = parts[1].strip()

    if sensor == 'Landsat 8':
        key_map = LANDSAT_META_KEYS['Landsat 8']
        return {k: float(raw[v]) for k, v in key_map.items()}

    elif sensor == 'Landsat 7':
        if gain not in ('High', 'Low'):
            raise ValueError("Landsat 7 requires gain='High' or gain='Low'")
        key_map = LANDSAT_META_KEYS['Landsat 7'][gain]
        return {k: float(raw[v]) for k, v in key_map.items()}

    elif sensor == 'Landsat 5':
        key_map = LANDSAT_META_KEYS['Landsat 5']
        return {k: float(raw[v]) for k, v in key_map.items()}

    else:
        raise ValueError("Unsupported sensor: {}".format(sensor))
