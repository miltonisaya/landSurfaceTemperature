# -*- coding: utf-8 -*-
"""Radiative Transfer Equation algorithm for LST estimation."""

import os

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
from qgis.PyQt.QtGui import QIcon
from ..core.raster_utils import create_output_raster, iterate_blocks, finalize_raster, count_blocks
from ..core.constants import SENSOR_K_CONSTANTS
from ..core.unit_conversion import convert_temperature


class RadiativeTransferAlgorithm(QgsProcessingAlgorithm):
    TOA_RADIANCE = 'TOA_RADIANCE'
    LSE = 'LSE'
    SENSOR = 'SENSOR'
    BAND_NUMBER = 'BAND_NUMBER'
    UP_RAD = 'UP_RAD'
    DOWN_RAD = 'DOWN_RAD'
    ATM_TRANS = 'ATM_TRANS'
    UNIT = 'UNIT'
    OUTPUT = 'OUTPUT'

    SENSOR_OPTIONS = ['Landsat TIRS', 'Landsat ETM+', 'Landsat TM']
    BAND_OPTIONS = ['6', '10', '11']
    UNIT_OPTIONS = ['Kelvin', 'Celsius', 'Fahrenheit']

    def name(self):
        return 'radiative_transfer'

    def displayName(self):
        return 'Radiative Transfer Equation'

    def group(self):
        return 'Land Surface Temperature'

    def groupId(self):
        return 'land_surface_temperature'

    def shortHelpString(self):
        return 'Estimates land surface temperature using the Radiative Transfer Equation with atmospheric correction parameters.'

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), '..', 'icons', 'algorithms.png'))

    def createInstance(self):
        return RadiativeTransferAlgorithm()

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(self.TOA_RADIANCE, 'TOA radiance raster'))
        self.addParameter(QgsProcessingParameterRasterLayer(self.LSE, 'Land surface emissivity raster'))
        self.addParameter(QgsProcessingParameterEnum(self.SENSOR, 'Sensor', options=self.SENSOR_OPTIONS, defaultValue=0))
        self.addParameter(QgsProcessingParameterEnum(self.BAND_NUMBER, 'Band number', options=self.BAND_OPTIONS, defaultValue=1))
        self.addParameter(QgsProcessingParameterNumber(self.UP_RAD, 'Upwelling radiance (W/m²/sr/μm)', type=QgsProcessingParameterNumber.Double))
        self.addParameter(QgsProcessingParameterNumber(self.DOWN_RAD, 'Downwelling radiance (W/m²/sr/μm)', type=QgsProcessingParameterNumber.Double))
        self.addParameter(QgsProcessingParameterNumber(self.ATM_TRANS, 'Atmospheric transmittance', type=QgsProcessingParameterNumber.Double, minValue=0.0, maxValue=1.0))
        self.addParameter(QgsProcessingParameterEnum(self.UNIT, 'Temperature unit', options=self.UNIT_OPTIONS, defaultValue=0))
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT, 'LST output'))

    def processAlgorithm(self, parameters, context, feedback):
        toa_layer = self.parameterAsRasterLayer(parameters, self.TOA_RADIANCE, context)
        lse_layer = self.parameterAsRasterLayer(parameters, self.LSE, context)
        sensor_idx = self.parameterAsEnum(parameters, self.SENSOR, context)
        sensor = self.SENSOR_OPTIONS[sensor_idx]
        band_idx = self.parameterAsEnum(parameters, self.BAND_NUMBER, context)
        band_no = int(self.BAND_OPTIONS[band_idx])
        up_rad = self.parameterAsDouble(parameters, self.UP_RAD, context)
        down_rad = self.parameterAsDouble(parameters, self.DOWN_RAD, context)
        atm_trans = self.parameterAsDouble(parameters, self.ATM_TRANS, context)
        unit_idx = self.parameterAsEnum(parameters, self.UNIT, context)
        unit = self.UNIT_OPTIONS[unit_idx]
        output_path = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        if sensor not in SENSOR_K_CONSTANTS or band_no not in SENSOR_K_CONSTANTS[sensor]:
            raise QgsProcessingException('Invalid sensor/band combination: {} band {}'.format(sensor, band_no))

        K1 = SENSOR_K_CONSTANTS[sensor][band_no]['K1']
        K2 = SENSOR_K_CONSTANTS[sensor][band_no]['K2']

        ds_toa = gdal.Open(toa_layer.source(), gdal.GA_ReadOnly)
        ds_lse = gdal.Open(lse_layer.source(), gdal.GA_ReadOnly)
        if ds_toa is None or ds_lse is None:
            raise QgsProcessingException('Failed to open input rasters')

        toa_band = ds_toa.GetRasterBand(1)
        lse_band = ds_lse.GetRasterBand(1)
        cols = ds_toa.RasterXSize
        rows = ds_toa.RasterYSize

        out_ds = create_output_raster(output_path, ds_toa)
        out_band = out_ds.GetRasterBand(1)

        total = count_blocks(rows, cols)
        current = 0

        for j, i, num_cols, num_rows in iterate_blocks(rows, cols):
            if feedback.isCanceled():
                break
            lse_data = lse_band.ReadAsArray(j, i, num_cols, num_rows).astype('f')
            toa_data = toa_band.ReadAsArray(j, i, num_cols, num_rows).astype('f')

            # Land surface radiance of kinetic temperature
            te = np.multiply(atm_trans, lse_data)
            left = np.where(te != 0, np.divide(np.subtract(toa_data, up_rad), te), 0)
            right = np.where(lse_data > 0, np.divide(np.subtract(1, lse_data), lse_data), 0)
            right = np.multiply(right, down_rad)
            LTS = np.subtract(left, right)

            # Invert radiance using Planck equation
            planck_inner = np.where(LTS != 0, np.add(np.divide(K1, LTS), 1), 1)
            planck_log = np.where(planck_inner > 0, np.log(planck_inner), 0)
            lst = np.where(planck_log != 0, np.divide(K2, planck_log), -99)

            lst = convert_temperature(lst, unit)
            out_band.WriteArray(lst, j, i)
            current += 1
            feedback.setProgress(int(current / total * 100))

        finalize_raster(out_ds)
        out_ds = None
        ds_toa = None
        ds_lse = None

        return {self.OUTPUT: output_path}
