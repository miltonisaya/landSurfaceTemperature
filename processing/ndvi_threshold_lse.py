# -*- coding: utf-8 -*-
"""NDVI Threshold LSE estimation algorithm."""

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


class NdviThresholdLseAlgorithm(QgsProcessingAlgorithm):
    NDVI = 'NDVI'
    OUTPUT = 'OUTPUT'

    def name(self):
        return 'ndvi_threshold_lse'

    def displayName(self):
        return 'NDVI Threshold LSE'

    def group(self):
        return 'Land Surface Emissivity'

    def groupId(self):
        return 'land_surface_emissivity'

    def shortHelpString(self):
        return 'Estimates land surface emissivity using NDVI thresholds with proportion of vegetation and cavity effect correction.'

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), '..', 'icons', 'emissivity.png'))

    def createInstance(self):
        return NdviThresholdLseAlgorithm()

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

        # Get NDVI statistics for Pv calculation
        stats = band.GetStatistics(0, 1)
        ndvi_min = stats[0]
        ndvi_max = stats[1]

        ev = 0.973  # Emissivity of vegetation
        es = 0.966  # Emissivity of soil
        ew = 0.991  # Emissivity of water

        out_ds = create_output_raster(output_path, ds)
        out_band = out_ds.GetRasterBand(1)

        total = count_blocks(rows, cols)
        current = 0

        for j, i, num_cols, num_rows in iterate_blocks(rows, cols):
            if feedback.isCanceled():
                break
            ndvi_data = band.ReadAsArray(j, i, num_cols, num_rows).astype('f')

            water_logic = np.logical_and(ndvi_data >= -1, ndvi_data < -0.185)
            soil_logic = np.logical_and(ndvi_data >= -0.185, ndvi_data < 0.2)
            mixed_logic = np.logical_and(ndvi_data >= 0.2, ndvi_data < 0.5)
            veg_logic = np.logical_and(ndvi_data > 0.5, ndvi_data <= 1)
            condition_list = [water_logic, soil_logic, mixed_logic, veg_logic]

            # Proportion of vegetation
            Pv = np.divide(np.subtract(ndvi_data, ndvi_min), np.subtract(ndvi_max, ndvi_min))
            Pv = np.multiply(Pv, Pv)

            # Cavity effect correction
            C = np.multiply(np.subtract(1, es), np.multiply(ev, 0.55))
            C = np.multiply(C, np.subtract(1, Pv))

            mixed_pixels = np.add(np.multiply(ev, Pv), np.multiply(es, np.subtract(1, Pv)))
            mixed_pixels = np.add(mixed_pixels, C)

            choice_list = [ew, es, mixed_pixels, ev]
            lse = np.select(condition_list, choice_list)

            out_band.WriteArray(lse, j, i)
            current += 1
            feedback.setProgress(int(current / total * 100))

        finalize_raster(out_ds)
        out_ds = None
        ds = None

        return {self.OUTPUT: output_path}
