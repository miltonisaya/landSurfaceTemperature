# -*- coding: utf-8 -*-
"""Brightness temperature calculation algorithm."""

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
from ..core.constants import SENSOR_K_CONSTANTS


class BrightnessTemperatureAlgorithm(QgsProcessingAlgorithm):
    RADIANCE = 'RADIANCE'
    SENSOR = 'SENSOR'
    BAND_NUMBER = 'BAND_NUMBER'
    OUTPUT = 'OUTPUT'

    SENSOR_OPTIONS = ['Landsat TIRS', 'Landsat ETM+', 'Landsat TM', 'ASTER']
    BAND_OPTIONS = ['6', '10', '11', '12', '13', '14']

    def name(self):
        return 'brightness_temperature'

    def displayName(self):
        return 'Brightness Temperature'

    def group(self):
        return 'Brightness Temperature'

    def groupId(self):
        return 'brightness_temperature'

    def shortHelpString(self):
        return 'Calculates brightness temperature from spectral radiance using K1/K2 calibration constants. BT = K2 / ln(K1/L + 1)'

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), '..', 'icons', 'bt.png'))

    def createInstance(self):
        return BrightnessTemperatureAlgorithm()

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(self.RADIANCE, 'Radiance raster'))
        self.addParameter(QgsProcessingParameterEnum(self.SENSOR, 'Sensor', options=self.SENSOR_OPTIONS, defaultValue=0))
        self.addParameter(QgsProcessingParameterEnum(self.BAND_NUMBER, 'Band number', options=self.BAND_OPTIONS, defaultValue=1))
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT, 'Brightness temperature output'))

    def processAlgorithm(self, parameters, context, feedback):
        rad_layer = self.parameterAsRasterLayer(parameters, self.RADIANCE, context)
        sensor_idx = self.parameterAsEnum(parameters, self.SENSOR, context)
        sensor = self.SENSOR_OPTIONS[sensor_idx]
        band_idx = self.parameterAsEnum(parameters, self.BAND_NUMBER, context)
        band_no = int(self.BAND_OPTIONS[band_idx])
        output_path = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        if sensor not in SENSOR_K_CONSTANTS or band_no not in SENSOR_K_CONSTANTS[sensor]:
            raise QgsProcessingException('Invalid sensor/band combination: {} band {}'.format(sensor, band_no))

        K1 = SENSOR_K_CONSTANTS[sensor][band_no]['K1']
        K2 = SENSOR_K_CONSTANTS[sensor][band_no]['K2']

        ds = gdal.Open(rad_layer.source(), gdal.GA_ReadOnly)
        if ds is None:
            raise QgsProcessingException('Failed to open radiance raster')

        band = ds.GetRasterBand(1)
        cols = ds.RasterXSize
        rows = ds.RasterYSize

        out_ds = create_output_raster(output_path, ds)
        out_band = out_ds.GetRasterBand(1)

        total = count_blocks(rows, cols)
        current = 0

        for j, i, num_cols, num_rows in iterate_blocks(rows, cols):
            if feedback.isCanceled():
                break
            data = band.ReadAsArray(j, i, num_cols, num_rows).astype('f')
            bt = K2 / np.log(np.add(np.divide(K1, data), 1))
            out_band.WriteArray(bt, j, i)
            current += 1
            feedback.setProgress(int(current / total * 100))

        finalize_raster(out_ds)
        out_ds = None
        ds = None

        return {self.OUTPUT: output_path}
