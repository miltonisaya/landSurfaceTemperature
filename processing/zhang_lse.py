# -*- coding: utf-8 -*-
"""Zhang LSE estimation algorithm."""

import os

import numpy as np
from osgeo import gdal
from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterRasterDestination,
    QgsProcessingException,
)
from qgis.PyQt.QtGui import QIcon
from ..core.raster_utils import create_output_raster, iterate_blocks, finalize_raster, count_blocks


class ZhangLseAlgorithm(QgsProcessingAlgorithm):
    NDVI = 'NDVI'
    OUTPUT = 'OUTPUT'

    def name(self):
        return 'zhang_lse'

    def displayName(self):
        return 'Zhang LSE'

    def group(self):
        return 'Land Surface Emissivity'

    def groupId(self):
        return 'land_surface_emissivity'

    def shortHelpString(self):
        return 'Estimates land surface emissivity using the Zhang et al. method based on NDVI thresholds.'

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), '..', 'icons', 'emissivity.png'))

    def createInstance(self):
        return ZhangLseAlgorithm()

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(self.NDVI, 'NDVI raster'))
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT, 'LSE output'))

    def processAlgorithm(self, parameters, context, feedback):
        ndvi_layer = self.parameterAsRasterLayer(parameters, self.NDVI, context)
        output_path = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        ds = gdal.Open(ndvi_layer.source(), gdal.GA_ReadOnly)
        if ds is None:
            raise QgsProcessingException('Failed to open NDVI raster')

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
            ndvi_data = band.ReadAsArray(j, i, num_cols, num_rows).astype('f')

            condition_list = [
                np.logical_and(ndvi_data < -0.185, ndvi_data >= -1),
                np.logical_and(ndvi_data >= -0.185, ndvi_data <= 0.157),
                np.logical_and(ndvi_data >= 0.157, ndvi_data <= 0.727),
                np.logical_and(ndvi_data > 0.727, ndvi_data <= 1),
            ]
            mixed = np.add(np.multiply(np.log(ndvi_data), 0.047), 1.009)
            choice_list = [0.995, 0.985, mixed, 0.990]
            lse = np.select(condition_list, choice_list)

            out_band.WriteArray(lse, j, i)
            current += 1
            feedback.setProgress(int(current / total * 100))

        finalize_raster(out_ds)
        out_ds = None
        ds = None

        return {self.OUTPUT: output_path}
