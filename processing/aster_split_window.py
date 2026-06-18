# -*- coding: utf-8 -*-
"""ASTER Split-Window algorithm for LST estimation."""

import numpy as np
from osgeo import gdal
from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterNumber,
    QgsProcessingParameterEnum,
    QgsProcessingParameterRasterDestination,
    QgsProcessingException,
)
from ..core.raster_utils import create_output_raster, iterate_blocks, finalize_raster, count_blocks
from ..core.constants import SWA_CONSTANTS
from ..core.unit_conversion import convert_temperature


class AsterSplitWindowAlgorithm(QgsProcessingAlgorithm):
    BT_B13 = 'BT_B13'
    BT_B14 = 'BT_B14'
    LSE_B13 = 'LSE_B13'
    LSE_B14 = 'LSE_B14'
    ATM_TRANS_B13 = 'ATM_TRANS_B13'
    ATM_TRANS_B14 = 'ATM_TRANS_B14'
    UNIT = 'UNIT'
    OUTPUT = 'OUTPUT'

    UNIT_OPTIONS = ['Kelvin', 'Celsius', 'Fahrenheit']

    def name(self):
        return 'aster_split_window'

    def displayName(self):
        return 'ASTER Split-Window'

    def group(self):
        return 'Land Surface Temperature'

    def groupId(self):
        return 'land_surface_temperature'

    def shortHelpString(self):
        return 'Estimates land surface temperature using the ASTER Split-Window algorithm with bands 13 and 14.'

    def createInstance(self):
        return AsterSplitWindowAlgorithm()

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(self.BT_B13, 'Band 13 brightness temperature'))
        self.addParameter(QgsProcessingParameterRasterLayer(self.BT_B14, 'Band 14 brightness temperature'))
        self.addParameter(QgsProcessingParameterRasterLayer(self.LSE_B13, 'Band 13 land surface emissivity'))
        self.addParameter(QgsProcessingParameterRasterLayer(self.LSE_B14, 'Band 14 land surface emissivity'))
        self.addParameter(QgsProcessingParameterNumber(self.ATM_TRANS_B13, 'Band 13 atmospheric transmittance', type=QgsProcessingParameterNumber.Double, minValue=0.0, maxValue=1.0))
        self.addParameter(QgsProcessingParameterNumber(self.ATM_TRANS_B14, 'Band 14 atmospheric transmittance', type=QgsProcessingParameterNumber.Double, minValue=0.0, maxValue=1.0))
        self.addParameter(QgsProcessingParameterEnum(self.UNIT, 'Temperature unit', options=self.UNIT_OPTIONS, defaultValue=0))
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT, 'LST output'))

    def processAlgorithm(self, parameters, context, feedback):
        bt13_layer = self.parameterAsRasterLayer(parameters, self.BT_B13, context)
        bt14_layer = self.parameterAsRasterLayer(parameters, self.BT_B14, context)
        lse13_layer = self.parameterAsRasterLayer(parameters, self.LSE_B13, context)
        lse14_layer = self.parameterAsRasterLayer(parameters, self.LSE_B14, context)
        tau13 = self.parameterAsDouble(parameters, self.ATM_TRANS_B13, context)
        tau14 = self.parameterAsDouble(parameters, self.ATM_TRANS_B14, context)
        unit_idx = self.parameterAsEnum(parameters, self.UNIT, context)
        unit = self.UNIT_OPTIONS[unit_idx]
        output_path = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        a13 = SWA_CONSTANTS[13]['a']
        b13 = SWA_CONSTANTS[13]['b']
        a14 = SWA_CONSTANTS[14]['a']
        b14 = SWA_CONSTANTS[14]['b']

        ds_bt13 = gdal.Open(bt13_layer.source(), gdal.GA_ReadOnly)
        ds_bt14 = gdal.Open(bt14_layer.source(), gdal.GA_ReadOnly)
        ds_lse13 = gdal.Open(lse13_layer.source(), gdal.GA_ReadOnly)
        ds_lse14 = gdal.Open(lse14_layer.source(), gdal.GA_ReadOnly)
        if any(ds is None for ds in [ds_bt13, ds_bt14, ds_lse13, ds_lse14]):
            raise QgsProcessingException('Failed to open input rasters')

        band_bt13 = ds_bt13.GetRasterBand(1)
        band_bt14 = ds_bt14.GetRasterBand(1)
        band_lse13 = ds_lse13.GetRasterBand(1)
        band_lse14 = ds_lse14.GetRasterBand(1)
        cols = ds_bt13.RasterXSize
        rows = ds_bt13.RasterYSize

        out_ds = create_output_raster(output_path, ds_bt13)
        out_band = out_ds.GetRasterBand(1)

        total = count_blocks(rows, cols)
        current = 0

        for j, i, num_cols, num_rows in iterate_blocks(rows, cols):
            if feedback.isCanceled():
                break
            bt13 = band_bt13.ReadAsArray(j, i, num_cols, num_rows).astype('f')
            bt14 = band_bt14.ReadAsArray(j, i, num_cols, num_rows).astype('f')
            lse13 = band_lse13.ReadAsArray(j, i, num_cols, num_rows).astype('f')
            lse14 = band_lse14.ReadAsArray(j, i, num_cols, num_rows).astype('f')

            # A13 = a13 * lse13 * tau13
            A13 = np.multiply(np.multiply(a13, lse13), tau13)
            # B13 = a13 * bt13 + b13 * lse13 * tau13 - b13
            B13 = np.subtract(np.add(np.multiply(a13, bt13), np.multiply(np.multiply(b13, lse13), tau13)), b13)
            # C13 = (1 - tau13) * ((1 - lse13) * tau13 + 1) * a13
            C13 = np.multiply(np.multiply(np.subtract(1.0, tau13), np.add(np.multiply(np.subtract(1.0, lse13), tau13), 1.0)), a13)
            # D13 = (1 - tau13) * ((1 - lse13) * tau13 + 1) * b13
            D13 = np.multiply(np.multiply(np.subtract(1.0, tau13), np.add(np.multiply(np.subtract(1.0, lse13), tau13), 1.0)), b13)

            # A14, B14, C14, D14 (same pattern with band 14 constants)
            A14 = np.multiply(np.multiply(a14, lse14), tau14)
            B14 = np.subtract(np.add(np.multiply(a14, bt14), np.multiply(np.multiply(b14, lse14), tau14)), b14)
            C14 = np.multiply(np.multiply(np.subtract(1.0, tau14), np.add(np.multiply(np.subtract(1.0, lse14), tau14), 1.0)), a14)
            D14 = np.multiply(np.multiply(np.subtract(1.0, tau14), np.add(np.multiply(np.subtract(1.0, lse14), tau14), 1.0)), b14)

            # LST = (C14*(D13+B13) - C13*(D14+B14)) / (C14*A13 - C13*A14)
            numerator = np.subtract(np.multiply(C14, np.add(D13, B13)), np.multiply(C13, np.add(D14, B14)))
            denominator = np.subtract(np.multiply(C14, A13), np.multiply(C13, A14))
            lst = np.where(denominator != 0, np.divide(numerator, denominator), 0)

            lst = convert_temperature(lst, unit)
            out_band.WriteArray(lst, j, i)
            current += 1
            feedback.setProgress(int(current / total * 100))

        finalize_raster(out_ds)
        out_ds = None
        ds_bt13 = None
        ds_bt14 = None
        ds_lse13 = None
        ds_lse14 = None

        return {self.OUTPUT: output_path}
