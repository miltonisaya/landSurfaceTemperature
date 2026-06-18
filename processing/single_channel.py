# -*- coding: utf-8 -*-
"""Single Channel algorithm for Landsat LST estimation."""

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
from ..core.constants import SINGLE_CHANNEL_PARAMS, C1, C2, SENSOR_WAVELENGTHS
from ..core.unit_conversion import convert_temperature


class SingleChannelAlgorithm(QgsProcessingAlgorithm):
    RADIANCE = 'RADIANCE'
    BT = 'BT'
    LSE = 'LSE'
    SENSOR = 'SENSOR'
    ATM_WATER_VAPOR = 'ATM_WATER_VAPOR'
    UNIT = 'UNIT'
    OUTPUT = 'OUTPUT'

    SENSOR_OPTIONS = ['Landsat TM/ETM+', 'Landsat TIRS']
    UNIT_OPTIONS = ['Kelvin', 'Celsius', 'Fahrenheit']

    def name(self):
        return 'single_channel'

    def displayName(self):
        return 'Single Channel Algorithm'

    def group(self):
        return 'Land Surface Temperature'

    def groupId(self):
        return 'land_surface_temperature'

    def shortHelpString(self):
        return 'Estimates land surface temperature using the Single Channel algorithm (Jimenez-Munoz & Sobrino, 2003) for Landsat sensors.'

    def createInstance(self):
        return SingleChannelAlgorithm()

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(self.RADIANCE, 'Radiance raster'))
        self.addParameter(QgsProcessingParameterRasterLayer(self.BT, 'Brightness temperature raster'))
        self.addParameter(QgsProcessingParameterRasterLayer(self.LSE, 'Land surface emissivity raster'))
        self.addParameter(QgsProcessingParameterEnum(self.SENSOR, 'Sensor', options=self.SENSOR_OPTIONS, defaultValue=0))
        self.addParameter(QgsProcessingParameterNumber(self.ATM_WATER_VAPOR, 'Atmospheric water vapor (g/cm²)', type=QgsProcessingParameterNumber.Double, minValue=0.0))
        self.addParameter(QgsProcessingParameterEnum(self.UNIT, 'Temperature unit', options=self.UNIT_OPTIONS, defaultValue=0))
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT, 'LST output'))

    def processAlgorithm(self, parameters, context, feedback):
        rad_layer = self.parameterAsRasterLayer(parameters, self.RADIANCE, context)
        bt_layer = self.parameterAsRasterLayer(parameters, self.BT, context)
        lse_layer = self.parameterAsRasterLayer(parameters, self.LSE, context)
        sensor_idx = self.parameterAsEnum(parameters, self.SENSOR, context)
        sensor = self.SENSOR_OPTIONS[sensor_idx]
        w = self.parameterAsDouble(parameters, self.ATM_WATER_VAPOR, context)
        unit_idx = self.parameterAsEnum(parameters, self.UNIT, context)
        unit = self.UNIT_OPTIONS[unit_idx]
        output_path = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        params = SINGLE_CHANNEL_PARAMS[sensor]
        psi_1 = params['psi1'][0] * w**2 + params['psi1'][1] * w + params['psi1'][2]
        psi_2 = params['psi2'][0] * w**2 + params['psi2'][1] * w + params['psi2'][2]
        psi_3 = params['psi3'][0] * w**2 + params['psi3'][1] * w + params['psi3'][2]

        # Get effective wavelength (use band 6 for TM/ETM+, band 10 for TIRS)
        if sensor == 'Landsat TM/ETM+':
            eff_wl = SENSOR_WAVELENGTHS['Landsat TM'][6]
        else:
            eff_wl = SENSOR_WAVELENGTHS['Landsat TIRS'][10]

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
            t_sensor = bt_band.ReadAsArray(j, i, num_cols, num_rows).astype('f')
            l_sensor = rad_band.ReadAsArray(j, i, num_cols, num_rows).astype('f')

            # Gamma calculation
            gamma_1 = np.where(t_sensor != 0, np.divide(np.multiply(l_sensor, C2), t_sensor), 0)
            gamma_2 = np.multiply(np.divide(np.power(eff_wl, 4), C1), l_sensor)
            gamma = np.where(np.add(gamma_2, 1.0 / eff_wl) != 0,
                             1.0 / (np.multiply(gamma_1, np.add(gamma_2, 1.0 / eff_wl))), 0)

            # Delta calculation
            delta = np.add(t_sensor, np.multiply(np.multiply(l_sensor, -1), gamma))

            # Single channel equation
            lst = np.multiply(l_sensor, psi_1)
            lst = np.add(lst, psi_2)
            lst = np.multiply(np.where(lse_data != 0, 1.0 / lse_data, 0), lst)
            lst = np.add(lst, psi_3)
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
