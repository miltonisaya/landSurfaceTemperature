Land Surface Temperature
========================
A QGIS 3 plugin for extracting Land Surface Temperature (LST) from
satellite imagery.

Author:  Milton Isaya
License: GNU GPL v2 or later
Repository: https://github.com/miltonisaya/landSurfaceTemperature


Overview
--------
This plugin provides a suite of algorithms in the QGIS Processing toolbox
for deriving Land Surface Temperature from thermal infrared imagery acquired
by Landsat 5 (TM), Landsat 7 (ETM+), Landsat 8 (TIRS), and ASTER sensors.

All algorithms follow a step-by-step workflow:
  1. Compute NDVI (vegetation index)
  2. Convert thermal DN to spectral radiance
  3. Convert radiance to brightness temperature
  4. Estimate land surface emissivity (LSE)
  5. Retrieve land surface temperature (LST)


Supported Sensors
-----------------
  - Landsat 5 TM  (thermal band 6)
  - Landsat 7 ETM+ (thermal band 6, high and low gain)
  - Landsat 8 TIRS (thermal bands 10 and 11)
  - ASTER          (TIR bands 10-14, VNIR bands 1-3)


Algorithms
----------
Vegetation Indices
  - Landsat NDVI       — NDVI from separate Landsat red and NIR band rasters
  - ASTER NDVI         — NDVI from ASTER VNIR multi-band raster

Radiance
  - TM Radiance        — Landsat 5 TM thermal band to spectral radiance
  - ETM+ Radiance      — Landsat 7 ETM+ thermal band to spectral radiance
  - TIRS Radiance      — Landsat 8 TIRS bands 10/11 to spectral radiance
  - ASTER Radiance     — ASTER TIR bands 10-14 to spectral radiance

Brightness Temperature
  - Brightness Temperature — Radiance to BT using K1/K2 calibration constants

Land Surface Emissivity
  - Zhang LSE              — NDVI-threshold method (Zhang et al.)
  - NDVI Threshold LSE     — NDVI threshold with proportion of vegetation and
                             cavity effect correction
  - ASTER LSE              — ASTER-specific LSE using MODIS emissivity values

Land Surface Temperature
  - Planck Equation LST      — Emissivity-corrected Planck inversion
  - Mono-Window Algorithm    — Qin et al. (2001), requires atmospheric profile
  - Single Channel Algorithm — Jimenez-Munoz & Sobrino (2003), requires water vapor
  - Radiative Transfer Eq.   — Full atmospheric correction (up/down radiance)
  - ASTER Single Channel     — ASTER bands 13/14 with MODTRAN4 parameters
  - ASTER Split-Window       — ASTER bands 13 and 14 combined


Installation
------------
1. Download or clone this repository.
2. Copy the entire folder into your QGIS 3 Python plugin directory:
     Linux/macOS: ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/
     Windows:     %APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\
3. Start QGIS and enable the plugin via Plugins > Manage and Install Plugins.
4. The algorithms will appear in Processing > Toolbox under
   "Land Surface Temperature".


Compiling Resources (optional)
-------------------------------
If you modify icons or resources.qrc, recompile with:
  pyrcc5 -o resources.py resources.qrc


Requirements
------------
  - QGIS >= 3.0
  - Python >= 3.6
  - GDAL/OGR (included with QGIS)
  - NumPy (included with QGIS)


License
-------
This program is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation, either version 2 of the License, or (at your
option) any later version.

Copyright (C) 2015 Milton Isaya / Anadolu University
