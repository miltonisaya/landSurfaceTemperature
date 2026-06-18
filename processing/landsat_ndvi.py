# -*- coding: utf-8 -*-
"""Landsat NDVI calculation algorithm."""

import numpy as np
from osgeo import gdal
from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterRasterDestination,
    QgsProcessingException,
)
from ..core.raster_utils import create_output_raster, iterate_blocks, finalize_raster, count_blocks


class LandsatNdviAlgorithm(QgsProcessingAlgorithm):
    RED_BAND = 'RED_BAND'
    NIR_BAND = 'NIR_BAND'
    OUTPUT = 'OUTPUT'

    def name(self):
        return 'landsat_ndvi'

    def displayName(self):
        return 'Landsat NDVI'

    def group(self):
        return 'Vegetation Indices'

    def groupId(self):
        return 'vegetation_indices'

    def shortHelpString(self):
        return 'Calculates NDVI from separate Landsat red and NIR band rasters. NDVI = (NIR - Red) / (NIR + Red)'

    def createInstance(self):
        return LandsatNdviAlgorithm()

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(self.RED_BAND, 'Red band'))
        self.addParameter(QgsProcessingParameterRasterLayer(self.NIR_BAND, 'NIR band'))
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT, 'NDVI output'))

    def processAlgorithm(self, parameters, context, feedback):
        red_layer = self.parameterAsRasterLayer(parameters, self.RED_BAND, context)
        nir_layer = self.parameterAsRasterLayer(parameters, self.NIR_BAND, context)
        output_path = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        ds_red = gdal.Open(red_layer.source(), gdal.GA_ReadOnly)
        ds_nir = gdal.Open(nir_layer.source(), gdal.GA_ReadOnly)
        if ds_red is None or ds_nir is None:
            raise QgsProcessingException('Failed to open input rasters')

        red_band = ds_red.GetRasterBand(1)
        nir_band = ds_nir.GetRasterBand(1)
        cols = ds_red.RasterXSize
        rows = ds_red.RasterYSize

        out_ds = create_output_raster(output_path, ds_red)
        out_band = out_ds.GetRasterBand(1)

        total = count_blocks(rows, cols)
        current = 0

        for j, i, num_cols, num_rows in iterate_blocks(rows, cols):
            if feedback.isCanceled():
                break
            red_data = red_band.ReadAsArray(j, i, num_cols, num_rows).astype('f')
            nir_data = nir_band.ReadAsArray(j, i, num_cols, num_rows).astype('f')
            mask = np.greater(red_data + nir_data, 0)
            ndvi = np.choose(mask, (-99, (nir_data - red_data) / (nir_data + red_data)))
            out_band.WriteArray(ndvi, j, i)
            current += 1
            feedback.setProgress(int(current / total * 100))

        finalize_raster(out_ds)
        out_ds = None
        ds_red = None
        ds_nir = None

        return {self.OUTPUT: output_path}
