# -*- coding: utf-8 -*-
"""
/***************************************************************************
 LandSurfaceTemperature
                                 A QGIS plugin
 This tool extracts Land Surface Temperature from satellite imagery
                             -------------------
        begin                : 2015-11-10
        copyright            : (C) 2015 by Milton Isaya/Anadolu University
        email                : milton_issaya@hotmail.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load LandSurfaceTemperature class from file LandSurfaceTemperature.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .lst_tool import LandSurfaceTemperature
    return LandSurfaceTemperature(iface)
