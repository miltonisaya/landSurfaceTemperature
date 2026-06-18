# -*- coding: utf-8 -*-
"""ASTER LSE estimation algorithm."""

import numpy as np
from osgeo import gdal
from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterEnum,
    QgsProcessingParameterRasterDestination,
    QgsProcessingException,
)
from ..core.raster_utils import create_output_raster, iterate_blocks, finalize_raster, count_blocks
from ..core.constants import ASTER_LSE_COEFFICIENTS


class AsterLseAlgorithm(QgsProcessingAlgorithm):
    NDVI = 'NDVI'
    BAND_NUMBER = 'BAND_NUMBER'
    OUTPUT = 'OUTPUT'

    BAND_OPTIONS = ['10', '11', '12', '13', '14']

    def name(self):
        return 'aster_lse'

    def displayName(self):
        return 'ASTER LSE'

    def group(self):
        return 'Land Surface Emissivity'

    def groupId(self):
        return 'land_surface_emissivity'

    def shortHelpString(self):
        return 'Estimates land surface emissivity for ASTER TIR bands using NDVI-based approach with MODIS emissivity library values.'

    def createInstance(self):
        return AsterLseAlgorithm()

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(self.NDVI, 'NDVI raster'))
        self.addParameter(QgsProcessingParameterEnum(self.BAND_NUMBER, 'Band number', options=self.BAND_OPTIONS, defaultValue=0))
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT, 'LSE output'))

    def processAlgorithm(self, parameters, context, feedback):
        ndvi_layer = self.parameterAsRasterLayer(parameters, self.NDVI, context)
        band_idx = self.parameterAsEnum(parameters, self.BAND_NUMBER, context)
        band_no = int(self.BAND_OPTIONS[band_idx])
        output_path = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        multiplier, offset = ASTER_LSE_COEFFICIENTS[band_no]

        ds = gdal.Open(ndvi_layer.source(), gdal.GA_ReadOnly)
        if ds is None:
            raise QgsProcessingException('Failed to open NDVI raster')

        band = ds.GetRasterBand(1)
        cols = ds.RasterXSize
        rows = ds.RasterYSize

        # Get NDVI statistics for Pv calculation
        stats = band.GetStatistics(0, 1)
        ndvi_min = stats[0]
        ndvi_max = stats[1]

        out_ds = create_output_raster(output_path, ds)
        out_band = out_ds.GetRasterBand(1)

        total = count_blocks(rows, cols)
        current = 0

        for j, i, num_cols, num_rows in iterate_blocks(rows, cols):
            if feedback.isCanceled():
                break
            ndvi_data = band.ReadAsArray(j, i, num_cols, num_rows).astype('f')

            # Proportion of vegetation
            Pv_con = [ndvi_data > 0.5, ndvi_data < 0.2, np.logical_and(ndvi_data > 0.2, ndvi_data < 0.5)]
            Pv_eqn = np.divide(np.subtract(ndvi_data, ndvi_min), np.subtract(ndvi_max, ndvi_min))
            Pv_eqn = np.multiply(Pv_eqn, Pv_eqn)
            Pv = np.select(Pv_con, [1, 0, Pv_eqn])

            # LSE calculation
            lse_math = np.add(np.multiply(Pv, multiplier), offset)
            lse_con = [
                np.logical_and(ndvi_data >= -1, ndvi_data < -0.185),
                np.logical_and(ndvi_data >= -0.185, ndvi_data <= 0.2),
                np.logical_and(ndvi_data >= 0.2, ndvi_data < 0.7),
                np.logical_and(ndvi_data >= 0.7, ndvi_data <= 1),
            ]
            lse = np.select(lse_con, [0.991, 0.966, lse_math, 0.973])

            out_band.WriteArray(lse, j, i)
            current += 1
            feedback.setProgress(int(current / total * 100))

        finalize_raster(out_ds)
        out_ds = None
        ds = None

        return {self.OUTPUT: output_path}
