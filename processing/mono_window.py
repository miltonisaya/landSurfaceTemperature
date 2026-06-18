# -*- coding: utf-8 -*-
"""Mono-Window algorithm for LST estimation."""

import numpy as np
from osgeo import gdal
from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterEnum,
    QgsProcessingParameterNumber,
    QgsProcessingParameterRasterDestination,
    QgsProcessingException,
)
from ..core.raster_utils import create_output_raster, iterate_blocks, finalize_raster, count_blocks
from ..core.constants import MONO_WINDOW_PROFILES, MONO_WINDOW_A, MONO_WINDOW_B
from ..core.unit_conversion import convert_temperature


class MonoWindowAlgorithm(QgsProcessingAlgorithm):
    BT = 'BT'
    LSE = 'LSE'
    ATM_TRANS = 'ATM_TRANS'
    NEAR_SURF_TEMP = 'NEAR_SURF_TEMP'
    ATM_PROFILE = 'ATM_PROFILE'
    UNIT = 'UNIT'
    OUTPUT = 'OUTPUT'

    ATM_PROFILE_OPTIONS = ['USA 1976', 'Tropical', 'Mid-Latitude Summer', 'Mid-Latitude Winter']
    UNIT_OPTIONS = ['Kelvin', 'Celsius', 'Fahrenheit']

    def name(self):
        return 'mono_window'

    def displayName(self):
        return 'Mono-Window Algorithm'

    def group(self):
        return 'Land Surface Temperature'

    def groupId(self):
        return 'land_surface_temperature'

    def shortHelpString(self):
        return 'Estimates land surface temperature using the Mono-Window algorithm (Qin et al., 2001).'

    def createInstance(self):
        return MonoWindowAlgorithm()

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(self.BT, 'Brightness temperature raster'))
        self.addParameter(QgsProcessingParameterRasterLayer(self.LSE, 'Land surface emissivity raster'))
        self.addParameter(QgsProcessingParameterNumber(self.ATM_TRANS, 'Atmospheric transmittance', type=QgsProcessingParameterNumber.Double, minValue=0.0, maxValue=1.0))
        self.addParameter(QgsProcessingParameterNumber(self.NEAR_SURF_TEMP, 'Near-surface air temperature (K)', type=QgsProcessingParameterNumber.Double))
        self.addParameter(QgsProcessingParameterEnum(self.ATM_PROFILE, 'Atmospheric profile', options=self.ATM_PROFILE_OPTIONS, defaultValue=0))
        self.addParameter(QgsProcessingParameterEnum(self.UNIT, 'Temperature unit', options=self.UNIT_OPTIONS, defaultValue=0))
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT, 'LST output'))

    def processAlgorithm(self, parameters, context, feedback):
        bt_layer = self.parameterAsRasterLayer(parameters, self.BT, context)
        lse_layer = self.parameterAsRasterLayer(parameters, self.LSE, context)
        atm_trans = self.parameterAsDouble(parameters, self.ATM_TRANS, context)
        near_surf_temp = self.parameterAsDouble(parameters, self.NEAR_SURF_TEMP, context)
        profile_idx = self.parameterAsEnum(parameters, self.ATM_PROFILE, context)
        profile = self.ATM_PROFILE_OPTIONS[profile_idx]
        unit_idx = self.parameterAsEnum(parameters, self.UNIT, context)
        unit = self.UNIT_OPTIONS[unit_idx]
        output_path = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        # Calculate effective mean atmospheric temperature
        intercept, slope = MONO_WINDOW_PROFILES[profile]
        T = intercept + (slope * near_surf_temp)

        A = MONO_WINDOW_A
        B = MONO_WINDOW_B

        ds_bt = gdal.Open(bt_layer.source(), gdal.GA_ReadOnly)
        ds_lse = gdal.Open(lse_layer.source(), gdal.GA_ReadOnly)
        if ds_bt is None or ds_lse is None:
            raise QgsProcessingException('Failed to open input rasters')

        bt_band = ds_bt.GetRasterBand(1)
        lse_band = ds_lse.GetRasterBand(1)
        cols = ds_bt.RasterXSize
        rows = ds_bt.RasterYSize

        out_ds = create_output_raster(output_path, ds_bt)
        out_band = out_ds.GetRasterBand(1)

        total = count_blocks(rows, cols)
        current = 0

        for j, i, num_cols, num_rows in iterate_blocks(rows, cols):
            if feedback.isCanceled():
                break
            lse_data = lse_band.ReadAsArray(j, i, num_cols, num_rows).astype('f')
            bt_data = bt_band.ReadAsArray(j, i, num_cols, num_rows).astype('f')

            C = np.multiply(lse_data, atm_trans)
            D1 = 1 - atm_trans
            D2 = np.add(np.subtract(atm_trans, np.multiply(atm_trans, lse_data)), 1)
            D = np.multiply(D1, D2)

            lst1 = np.multiply(A, np.subtract(np.subtract(1, C), D))
            lst2 = np.multiply(np.add(np.add(np.multiply(B, np.subtract(np.subtract(1, C), D)), C), D), bt_data)
            DT = np.multiply(D, T)

            lst_upper = np.subtract(np.add(lst1, lst2), DT)
            lst = np.where(C > 0, np.divide(lst_upper, C), 0)

            lst = convert_temperature(lst, unit)
            out_band.WriteArray(lst, j, i)
            current += 1
            feedback.setProgress(int(current / total * 100))

        finalize_raster(out_ds)
        out_ds = None
        ds_bt = None
        ds_lse = None

        return {self.OUTPUT: output_path}
