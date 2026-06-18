# -*- coding: utf-8 -*-
"""Planck equation LST algorithm."""

import os

import numpy as np
from osgeo import gdal
from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterEnum,
    QgsProcessingParameterRasterDestination,
    QgsProcessingException,
)
from qgis.PyQt.QtGui import QIcon
from ..core.raster_utils import create_output_raster, iterate_blocks, finalize_raster, count_blocks
from ..core.constants import SENSOR_WAVELENGTHS
from ..core.unit_conversion import convert_temperature


class PlanckLstAlgorithm(QgsProcessingAlgorithm):
    BT = 'BT'
    LSE = 'LSE'
    SENSOR = 'SENSOR'
    BAND_NUMBER = 'BAND_NUMBER'
    UNIT = 'UNIT'
    OUTPUT = 'OUTPUT'

    SENSOR_OPTIONS = ['Landsat TIRS', 'Landsat ETM+', 'Landsat TM', 'ASTER']
    BAND_OPTIONS = ['6', '10', '11', '12', '13', '14']
    UNIT_OPTIONS = ['Kelvin', 'Celsius', 'Fahrenheit']

    def name(self):
        return 'planck_lst'

    def displayName(self):
        return 'Planck Equation LST'

    def group(self):
        return 'Land Surface Temperature'

    def groupId(self):
        return 'land_surface_temperature'

    def shortHelpString(self):
        return 'Calculates land surface temperature using the Planck equation with emissivity correction.'

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), '..', 'icons', 'algorithms.png'))

    def createInstance(self):
        return PlanckLstAlgorithm()

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(self.BT, 'Brightness temperature raster'))
        self.addParameter(QgsProcessingParameterRasterLayer(self.LSE, 'Land surface emissivity raster'))
        self.addParameter(QgsProcessingParameterEnum(self.SENSOR, 'Sensor', options=self.SENSOR_OPTIONS, defaultValue=0))
        self.addParameter(QgsProcessingParameterEnum(self.BAND_NUMBER, 'Band number', options=self.BAND_OPTIONS, defaultValue=1))
        self.addParameter(QgsProcessingParameterEnum(self.UNIT, 'Temperature unit', options=self.UNIT_OPTIONS, defaultValue=0))
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT, 'LST output'))

    def processAlgorithm(self, parameters, context, feedback):
        bt_layer = self.parameterAsRasterLayer(parameters, self.BT, context)
        lse_layer = self.parameterAsRasterLayer(parameters, self.LSE, context)
        sensor_idx = self.parameterAsEnum(parameters, self.SENSOR, context)
        sensor = self.SENSOR_OPTIONS[sensor_idx]
        band_idx = self.parameterAsEnum(parameters, self.BAND_NUMBER, context)
        band_no = int(self.BAND_OPTIONS[band_idx])
        unit_idx = self.parameterAsEnum(parameters, self.UNIT, context)
        unit = self.UNIT_OPTIONS[unit_idx]
        output_path = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        if sensor not in SENSOR_WAVELENGTHS or band_no not in SENSOR_WAVELENGTHS[sensor]:
            raise QgsProcessingException('Invalid sensor/band combination: {} band {}'.format(sensor, band_no))

        wl = SENSOR_WAVELENGTHS[sensor][band_no]

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
            bt_data = bt_band.ReadAsArray(j, i, num_cols, num_rows).astype('f')
            lse_data = lse_band.ReadAsArray(j, i, num_cols, num_rows).astype('f')

            # ln(LSE), avoiding log of non-positive values
            log_lse = np.where(lse_data > 0, np.log(lse_data), 0)

            lst_upper = bt_data
            lst_lower = np.add(np.multiply(np.divide(bt_data, 14380) * wl, log_lse), 1)
            lst = np.divide(lst_upper, lst_lower)

            lst = convert_temperature(lst, unit)
            out_band.WriteArray(lst, j, i)
            current += 1
            feedback.setProgress(int(current / total * 100))

        finalize_raster(out_ds)
        out_ds = None
        ds_bt = None
        ds_lse = None

        return {self.OUTPUT: output_path}
