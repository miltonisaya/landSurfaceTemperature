# -*- coding: utf-8 -*-
"""
Land Surface Temperature - A QGIS plugin
Extracts Land Surface Temperature from satellite imagery.

Copyright (C) 2015 by Milton Isaya/Anadolu University
Licensed under GNU GPL v2+
"""


def classFactory(iface):
    from .plugin import LandSurfaceTemperaturePlugin
    return LandSurfaceTemperaturePlugin(iface)
