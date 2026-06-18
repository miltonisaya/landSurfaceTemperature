# -*- coding: utf-8 -*-
"""Sensor constants for Land Surface Temperature calculations."""

# K1/K2 calibration constants by sensor and band
SENSOR_K_CONSTANTS = {
    'Landsat TIRS': {
        10: {'K1': 774.89, 'K2': 1321.08},
        11: {'K1': 480.89, 'K2': 1201.14},
    },
    'Landsat ETM+': {
        6: {'K1': 660.09, 'K2': 1282.71},
    },
    'Landsat TM': {
        6: {'K1': 607.76, 'K2': 1260.56},
    },
    'ASTER': {
        10: {'K1': 3047.47, 'K2': 1736.18},
        11: {'K1': 2480.93, 'K2': 1666.21},
        12: {'K1': 1930.80, 'K2': 1584.72},
        13: {'K1': 865.65, 'K2': 1349.82},
        14: {'K1': 649.60, 'K2': 1274.49},
    },
}

# ASTER unit conversion coefficients (DN to radiance) by band
ASTER_UCC = {
    10: 0.006822,
    11: 0.006780,
    12: 0.006590,
    13: 0.005693,
    14: 0.005225,
}

# Wavelengths (micrometers) by sensor and band for Planck/single-channel algorithms
SENSOR_WAVELENGTHS = {
    'Landsat TIRS': {
        10: 11.395,
        11: 12.005,
    },
    'Landsat ETM+': {
        6: 11.45,
    },
    'Landsat TM': {
        6: 11.45,
    },
    'Landsat TM/ETM+': {
        6: 11.45,
    },
    'ASTER': {
        10: 8.291,
        11: 8.634,
        12: 9.075,
        13: 10.657,
        14: 11.318,
    },
}

# ASTER LSE coefficients: (multiplier for Pv, offset) by band
# LSE = multiplier * Pv + offset
ASTER_LSE_COEFFICIENTS = {
    10: (0.044, 0.946),
    11: (0.041, 0.949),
    12: (0.049, 0.941),
    13: (0.022, 0.968),
    14: (0.020, 0.970),
}

# Split-window algorithm constants for bands 13 and 14
SWA_CONSTANTS = {
    13: {'a': 0.145236, 'b': 33.685},
    14: {'a': 0.13266, 'b': 30.273},
}

# Mono-window atmospheric profile coefficients
# T_a = intercept + slope * T_near_surface
MONO_WINDOW_PROFILES = {
    'USA 1976': (25.9396, 0.88045),
    'Tropical': (17.9769, 0.91715),
    'Mid-Latitude Summer': (16.0110, 0.92621),
    'Mid-Latitude Winter': (19.2704, 0.91118),
}

# MODTRAN4 database parameters for ASTER single-channel algorithm
# Keys: (band, database) -> (p1_a, p1_b, p1_c, p2_a, p2_b, p2_c, p3_a, p3_b, p3_c)
# parameter_i = p_i_a * w^2 + p_i_b * w + p_i_c  where w = atmospheric water vapor
MODTRAN4_PARAMS = {
    (13, 'STD66'): {
        'p1': (0.06524, -0.05878, 1.06576),
        'p2': (-0.55835, -0.75881, 0.00327),
        'p3': (-0.00284, 1.35633, -0.43020),
    },
    (14, 'STD66'): {
        'p1': (0.10062, -0.13563, 1.10559),
        'p2': (-0.79740, -0.39414, 0.17664),
        'p3': (-0.03091, 1.60094, -0.56515),
    },
    (13, 'TIGR61'): {
        'p1': (0.05327, -0.03937, 1.05742),
        'p2': (-0.48444, -0.74611, -0.03015),
        'p3': (0.00764, 1.24532, -0.39461),
    },
    (14, 'TIGR61'): {
        'p1': (0.07965, -0.09580, 1.08983),
        'p2': (-0.66528, -0.48582, -0.17029),
        'p3': (-0.01578, 1.46358, -0.52486),
    },
}

# Single-channel algorithm atmospheric function coefficients for Landsat
# psi_i = a * w^2 + b * w + c  where w = atmospheric water vapor
SINGLE_CHANNEL_PARAMS = {
    'Landsat TM/ETM+': {
        'psi1': (0.14714, -0.15583, 1.1234),
        'psi2': (-1.1836, -0.37607, -0.52894),
        'psi3': (-0.0455, 1.8719, -0.39071),
    },
    'Landsat TIRS': {
        'psi1': (0.14714, -0.15583, 1.1234),
        'psi2': (-1.1836, -0.37607, -0.52894),
        'psi3': (-0.0455, 1.8719, -0.39071),
    },
}

# Planck function constants
C1 = 119104000  # First radiation constant (um^4 * W / m^2)
C2 = 14387.7    # Second radiation constant (um * K)

# Mono-window algorithm constants
MONO_WINDOW_A = -67.355351
MONO_WINDOW_B = 0.458606

# Landsat metadata key mappings by sensor
LANDSAT_META_KEYS = {
    'Landsat 8': {
        'RadMultFactorBand10': 'RADIANCE_MULT_BAND_10',
        'RadAddBand10': 'RADIANCE_ADD_BAND_10',
        'RadMultFactorBand11': 'RADIANCE_MULT_BAND_11',
        'RadAddBand11': 'RADIANCE_ADD_BAND_11',
        'K1_Band10': 'K1_CONSTANT_BAND_10',
        'K2_Band10': 'K2_CONSTANT_BAND_10',
        'K1_Band11': 'K1_CONSTANT_BAND_11',
        'K2_Band11': 'K2_CONSTANT_BAND_11',
    },
    'Landsat 7': {
        'High': {
            'QCALMAX': 'QUANTIZE_CAL_MAX_BAND_6_VCID_2',
            'QCALMIN': 'QUANTIZE_CAL_MIN_BAND_6_VCID_2',
            'LMAX': 'RADIANCE_MAXIMUM_BAND_6_VCID_2',
            'LMIN': 'RADIANCE_MINIMUM_BAND_6_VCID_2',
        },
        'Low': {
            'QCALMAX': 'QUANTIZE_CAL_MAX_BAND_6_VCID_1',
            'QCALMIN': 'QUANTIZE_CAL_MIN_BAND_6_VCID_1',
            'LMAX': 'RADIANCE_MAXIMUM_BAND_6_VCID_1',
            'LMIN': 'RADIANCE_MINIMUM_BAND_6_VCID_1',
        },
    },
    'Landsat 5': {
        'QCALMAX': 'QUANTIZE_CAL_MAX_BAND_6',
        'QCALMIN': 'QUANTIZE_CAL_MIN_BAND_6',
        'LMAX': 'RADIANCE_MAXIMUM_BAND_6',
        'LMIN': 'RADIANCE_MINIMUM_BAND_6',
    },
}
