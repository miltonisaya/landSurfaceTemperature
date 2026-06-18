# -*- coding: utf-8 -*-
"""Landsat TIRS (Landsat 8) radiance calculation algorithm."""

import os

import numpy as np
from osgeo import gdal
from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterFile,
    QgsProcessingParameterEnum,
    QgsProcessingParameterNumber,
    QgsProcessingParameterRasterDestination,
    QgsProcessingException,
)
from qgis.PyQt.QtGui import QIcon
from ..core.raster_utils import create_output_raster, iterate_blocks, finalize_raster, count_blocks
from ..core.metadata_parser import parse_landsat_metadata


class TirsRadianceAlgorithm(QgsProcessingAlgorithm):
    THERMAL_BAND = 'THERMAL_BAND'
    BAND_NUMBER = 'BAND_NUMBER'
    CALIB_OFFSET = 'CALIB_OFFSET'
    METADATA = 'METADATA'
    OUTPUT = 'OUTPUT'

    BAND_OPTIONS = ['10', '11']

    def name(self):
        return 'tirs_radiance'

    def displayName(self):
        return 'TIRS Radiance'

    def group(self):
        return 'Radiance'

    def groupId(self):
        return 'radiance'

    def shortHelpString(self):
        return 'Calculates spectral radiance from Landsat 8 TIRS thermal bands using metadata calibration values.'

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), '..', 'icons', 'radiance.png'))

    def createInstance(self):
        return TirsRadianceAlgorithm()

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(self.THERMAL_BAND, 'Thermal band'))
        self.addParameter(QgsProcessingParameterEnum(self.BAND_NUMBER, 'Band number', options=self.BAND_OPTIONS, defaultValue=0))
        self.addParameter(QgsProcessingParameterNumber(self.CALIB_OFFSET, 'Calibration offset', type=QgsProcessingParameterNumber.Double, defaultValue=0.0))
        self.addParameter(QgsProcessingParameterFile(self.METADATA, 'Metadata file (MTL)', extension='txt'))
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT, 'Radiance output'))

    def processAlgorithm(self, parameters, context, feedback):
        thermal_layer = self.parameterAsRasterLayer(parameters, self.THERMAL_BAND, context)
        band_idx = self.parameterAsEnum(parameters, self.BAND_NUMBER, context)
        band_no = int(self.BAND_OPTIONS[band_idx])
        calib_offset = self.parameterAsDouble(parameters, self.CALIB_OFFSET, context)
        metadata_path = self.parameterAsFile(parameters, self.METADATA, context)
        output_path = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        meta = parse_landsat_metadata(metadata_path, 'Landsat 8')

        if band_no == 10:
            mult = meta['RadMultFactorBand10']
            add = meta['RadAddBand10']
        else:
            mult = meta['RadMultFactorBand11']
            add = meta['RadAddBand11']

        ds = gdal.Open(thermal_layer.source(), gdal.GA_ReadOnly)
        if ds is None:
            raise QgsProcessingException('Failed to open thermal band')

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
            radiance = np.multiply(data, mult)
            radiance = np.add(radiance, add)
            radiance = np.subtract(radiance, calib_offset)
            out_band.WriteArray(radiance, j, i)
            current += 1
            feedback.setProgress(int(current / total * 100))

        finalize_raster(out_ds)
        out_ds = None
        ds = None

        return {self.OUTPUT: output_path}
