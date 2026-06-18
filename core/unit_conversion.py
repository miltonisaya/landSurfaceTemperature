# -*- coding: utf-8 -*-
"""Temperature unit conversion utilities."""

import numpy as np


def convert_temperature(data, unit):
    """Convert temperature data from Kelvin to the specified unit.

    :param data: Temperature array in Kelvin.
    :param unit: Target unit ('Kelvin', 'Celsius', or 'Fahrenheit').
    :returns: Converted temperature array.
    """
    if unit == 'Celsius':
        return np.subtract(data, 273.15)
    elif unit == 'Fahrenheit':
        return np.add(np.multiply(np.subtract(data, 273.15), 1.8), 32)
    return data
