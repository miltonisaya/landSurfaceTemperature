# -*- coding: utf-8 -*-
"""ASTER Single Channel algorithm for LST estimation."""

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
from ..core.constants import MODTRAN4_PARAMS, SENSOR_K_CONSTANTS
from ..core.unit_conversion import convert_temperature


class AsterSingleChannelAlgorithm(QgsProcessingAlgorithm):
    RADIANCE = 'RADIANCE'
    BT = 'BT'
    LSE = 'LSE'
    BAND_NUMBER = 'BAND_NUMBER'
    ATM_WATER_VAPOR = 'ATM_WATER_VAPOR'
    MODTRAN_DB = 'MODTRAN_DB'
    UNIT = 'UNIT'
    OUTPUT = 'OUTPUT'

    BAND_OPTIONS = ['13', '14']
    MODTRAN_OPTIONS = ['STD66', 'TIGR61']
    UNIT_OPTIONS = ['Kelvin', 'Celsius', 'Fahrenheit']

    def name(self):
        return 'aster_single_channel'

    def displayName(self):
        return 'ASTER Single Channel'

    def group(self):
        return 'Land Surface Temperature'

    def groupId(self):
        return 'land_surface_temperature'

    def shortHelpString(self):
        return 'Estimates land surface temperature from ASTER bands 13/14 using the Single Channel algorithm with MODTRAN4 atmospheric parameters.'

    def createInstance(self):
        return AsterSingleChannelAlgorithm()

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(self.RADIANCE, 'Radiance raster'))
        self.addParameter(QgsProcessingParameterRasterLayer(self.BT, 'Brightness temperature raster'))
        self.addParameter(QgsProcessingParameterRasterLayer(self.LSE, 'Land surface emissivity raster'))
        self.addParameter(QgsProcessingParameterEnum(self.BAND_NUMBER, 'Band number', options=self.BAND_OPTIONS, defaultValue=0))
        self.addParameter(QgsProcessingParameterNumber(self.ATM_WATER_VAPOR, 'Atmospheric water vapor (g/cm²)', type=QgsProcessingParameterNumber.Double, minValue=0.0))
        self.addParameter(QgsProcessingParameterEnum(self.MODTRAN_DB, 'MODTRAN4 database', options=self.MODTRAN_OPTIONS, defaultValue=0))
        self.addParameter(QgsProcessingParameterEnum(self.UNIT, 'Temperature unit', options=self.UNIT_OPTIONS, defaultValue=0))
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT, 'LST output'))

    def processAlgorithm(self, parameters, context, feedback):
        rad_layer = self.parameterAsRasterLayer(parameters, self.RADIANCE, context)
        bt_layer = self.parameterAsRasterLayer(parameters, self.BT, context)
        lse_layer = self.parameterAsRasterLayer(parameters, self.LSE, context)
        band_idx = self.parameterAsEnum(parameters, self.BAND_NUMBER, context)
        band_no = int(self.BAND_OPTIONS[band_idx])
        w = self.parameterAsDouble(parameters, self.ATM_WATER_VAPOR, context)
        modtran_idx = self.parameterAsEnum(parameters, self.MODTRAN_DB, context)
        modtran = self.MODTRAN_OPTIONS[modtran_idx]
        unit_idx = self.parameterAsEnum(parameters, self.UNIT, context)
        unit = self.UNIT_OPTIONS[unit_idx]
        output_path = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        key = (band_no, modtran)
        if key not in MODTRAN4_PARAMS:
            raise QgsProcessingException('Invalid band/MODTRAN combination: band {} {}'.format(band_no, modtran))

        params = MODTRAN4_PARAMS[key]
        p1 = params['p1'][0] * w**2 + params['p1'][1] * w + params['p1'][2]
        p2 = params['p2'][0] * w**2 + params['p2'][1] * w + params['p2'][2]
        p3 = params['p3'][0] * w**2 + params['p3'][1] * w + params['p3'][2]

        K1 = SENSOR_K_CONSTANTS['ASTER'][band_no]['K1']
        K2 = SENSOR_K_CONSTANTS['ASTER'][band_no]['K2']

        ds_rad = gdal.Open(rad_layer.source(), gdal.GA_ReadOnly)
        ds_bt = gdal.Open(bt_layer.source(), gdal.GA_ReadOnly)
        ds_lse = gdal.Open(lse_layer.source(), gdal.GA_ReadOnly)
        if ds_rad is None or ds_bt is None or ds_lse is None:
            raise QgsProcessingException('Failed to open input rasters')

        rad_band = ds_rad.GetRasterBand(1)
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
            rad_data = rad_band.ReadAsArray(j, i, num_cols, num_rows).astype('f')

            # Gamma parameter
            gamma = np.where(np.multiply(K2, rad_data) != 0,
                             np.divide(np.multiply(bt_data, bt_data), np.multiply(K2, rad_data)), 0)

            # Delta parameter
            delta = np.subtract(bt_data, np.where(K2 != 0, np.divide(np.multiply(bt_data, bt_data), K2), 0))

            # Single channel equation
            lst = np.add(np.multiply(rad_data, p1), p2)
            inv_lse = np.where(lse_data != 0, 1.0 / lse_data, 1)
            lst = np.multiply(inv_lse, lst)
            lst = np.add(lst, p3)
            lst = np.multiply(gamma, lst)
            lst = np.add(lst, delta)

            lst = convert_temperature(lst, unit)
            out_band.WriteArray(lst, j, i)
            current += 1
            feedback.setProgress(int(current / total * 100))

        finalize_raster(out_ds)
        out_ds = None
        ds_rad = None
        ds_bt = None
        ds_lse = None

        return {self.OUTPUT: output_path}
