# -*- coding: utf-8 -*-
"""Landsat ETM+ (Landsat 7) radiance calculation algorithm."""

import os

import numpy as np
from osgeo import gdal
from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterFile,
    QgsProcessingParameterEnum,
    QgsProcessingParameterRasterDestination,
    QgsProcessingException,
)
from qgis.PyQt.QtGui import QIcon
from ..core.raster_utils import create_output_raster, iterate_blocks, finalize_raster, count_blocks
from ..core.metadata_parser import parse_landsat_metadata


class EtmRadianceAlgorithm(QgsProcessingAlgorithm):
    THERMAL_BAND = 'THERMAL_BAND'
    GAIN = 'GAIN'
    METADATA = 'METADATA'
    OUTPUT = 'OUTPUT'

    GAIN_OPTIONS = ['High', 'Low']

    def name(self):
        return 'etm_radiance'

    def displayName(self):
        return 'ETM+ Radiance'

    def group(self):
        return 'Radiance'

    def groupId(self):
        return 'radiance'

    def shortHelpString(self):
        return 'Calculates spectral radiance from Landsat 7 ETM+ thermal band using metadata calibration values.'

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), '..', 'icons', 'radiance.png'))

    def createInstance(self):
        return EtmRadianceAlgorithm()

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(self.THERMAL_BAND, 'Thermal band (band 6)'))
        self.addParameter(QgsProcessingParameterEnum(self.GAIN, 'Gain', options=self.GAIN_OPTIONS, defaultValue=0))
        self.addParameter(QgsProcessingParameterFile(self.METADATA, 'Metadata file (MTL)', extension='txt'))
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT, 'Radiance output'))

    def processAlgorithm(self, parameters, context, feedback):
        thermal_layer = self.parameterAsRasterLayer(parameters, self.THERMAL_BAND, context)
        gain_idx = self.parameterAsEnum(parameters, self.GAIN, context)
        gain = self.GAIN_OPTIONS[gain_idx]
        metadata_path = self.parameterAsFile(parameters, self.METADATA, context)
        output_path = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        meta = parse_landsat_metadata(metadata_path, 'Landsat 7', gain)
        QCALMAX = meta['QCALMAX']
        QCALMIN = meta['QCALMIN']
        LMAX = meta['LMAX']
        LMIN = meta['LMIN']

        ds = gdal.Open(thermal_layer.source(), gdal.GA_ReadOnly)
        if ds is None:
            raise QgsProcessingException('Failed to open thermal band')

        band = ds.GetRasterBand(1)
        cols = ds.RasterXSize
        rows = ds.RasterYSize

        out_ds = create_output_raster(output_path, ds)
        out_band = out_ds.GetRasterBand(1)

        m = (LMAX - QCALMIN) / (QCALMAX - QCALMIN)
        total = count_blocks(rows, cols)
        current = 0

        for j, i, num_cols, num_rows in iterate_blocks(rows, cols):
            if feedback.isCanceled():
                break
            data = band.ReadAsArray(j, i, num_cols, num_rows).astype('f')
            radiance = np.multiply(m, np.subtract(data, QCALMIN))
            radiance = np.add(radiance, LMIN)
            out_band.WriteArray(radiance, j, i)
            current += 1
            feedback.setProgress(int(current / total * 100))

        finalize_raster(out_ds)
        out_ds = None
        ds = None

        return {self.OUTPUT: output_path}
