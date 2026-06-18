# -*- coding: utf-8 -*-
"""ASTER TIR radiance calculation algorithm."""

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
from ..core.constants import ASTER_UCC


class AsterRadianceAlgorithm(QgsProcessingAlgorithm):
    THERMAL_BAND = 'THERMAL_BAND'
    BAND_NUMBER = 'BAND_NUMBER'
    OUTPUT = 'OUTPUT'

    BAND_OPTIONS = ['10', '11', '12', '13', '14']

    def name(self):
        return 'aster_radiance'

    def displayName(self):
        return 'ASTER Radiance'

    def group(self):
        return 'Radiance'

    def groupId(self):
        return 'radiance'

    def shortHelpString(self):
        return 'Calculates spectral radiance from ASTER TIR bands using unit conversion coefficients.'

    def createInstance(self):
        return AsterRadianceAlgorithm()

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(self.THERMAL_BAND, 'ASTER TIR raster'))
        self.addParameter(QgsProcessingParameterEnum(self.BAND_NUMBER, 'Band number', options=self.BAND_OPTIONS, defaultValue=0))
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT, 'Radiance output'))

    def processAlgorithm(self, parameters, context, feedback):
        thermal_layer = self.parameterAsRasterLayer(parameters, self.THERMAL_BAND, context)
        band_idx = self.parameterAsEnum(parameters, self.BAND_NUMBER, context)
        band_no = int(self.BAND_OPTIONS[band_idx])
        output_path = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        ucc = ASTER_UCC[band_no]
        # The raster band index within the ASTER TIR file
        raster_band = band_no - 9  # band 10 -> index 1, etc.

        ds = gdal.Open(thermal_layer.source(), gdal.GA_ReadOnly)
        if ds is None:
            raise QgsProcessingException('Failed to open ASTER TIR raster')

        band = ds.GetRasterBand(raster_band)
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
            radiance = np.multiply(np.subtract(data, 1), ucc)
            out_band.WriteArray(radiance, j, i)
            current += 1
            feedback.setProgress(int(current / total * 100))

        finalize_raster(out_ds)
        out_ds = None
        ds = None

        return {self.OUTPUT: output_path}
