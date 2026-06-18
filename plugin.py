# -*- coding: utf-8 -*-
"""Minimal QGIS 3 plugin class that registers the Processing provider."""

from qgis.core import QgsApplication
from .processing.provider import LstProvider


class LandSurfaceTemperaturePlugin:

    def __init__(self, iface):
        self.iface = iface
        self.provider = None

    def initProcessing(self):
        self.provider = LstProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def initGui(self):
        self.initProcessing()

    def unload(self):
        if self.provider is not None:
            QgsApplication.processingRegistry().removeProvider(self.provider)
