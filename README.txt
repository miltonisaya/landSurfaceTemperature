Land Surface Temperature
========================
Suite of 16 Processing algorithms for complete Land Surface Temperature
(LST) retrieval from Landsat 5/7/8 and ASTER thermal imagery.

Author:  Milton Isaya
License: GNU GPL v2 or later
Repository: https://github.com/miltonisaya/landSurfaceTemperature


Overview
--------
This plugin provides a complete, step-by-step workflow for deriving Land
Surface Temperature from satellite thermal infrared imagery using 16
algorithms in the QGIS Processing toolbox. It supports Landsat 5 TM,
Landsat 7 ETM+, Landsat 8 TIRS, and ASTER sensors.

Input imagery can be obtained free of charge from:
  - USGS EarthExplorer  : earthexplorer.usgs.gov
  - NASA Earthdata      : earthdata.nasa.gov


Applications
------------
  - Urban heat island analysis
  - Drought and vegetation stress monitoring
  - Agricultural water management
  - Wildfire burn severity assessment
  - Climate and land use change studies


Workflow
--------
  1. Compute NDVI from red and near-infrared bands
  2. Convert thermal band digital numbers to spectral radiance
  3. Convert radiance to at-sensor brightness temperature using
     K1/K2 calibration constants
  4. Estimate land surface emissivity (LSE) using NDVI-based
     classification
  5. Retrieve land surface temperature using one of six LST algorithms


Supported Sensors
-----------------
  - Landsat 5 TM   (thermal band 6)
  - Landsat 7 ETM+ (thermal band 6, high and low gain)
  - Landsat 8 TIRS (thermal bands 10 and 11)
  - ASTER          (TIR bands 10-14, VNIR bands 1-3)


Algorithms
----------
Vegetation Indices
  - Landsat NDVI   — NDVI from separate Landsat red and NIR band rasters
  - ASTER NDVI     — NDVI from ASTER VNIR multi-band raster

Radiance
  - TM Radiance (L5)    — Landsat 5 TM thermal band to spectral radiance
  - ETM+ Radiance (L7)  — Landsat 7 ETM+ thermal band to spectral radiance
  - TIRS Radiance (L8)  — Landsat 8 TIRS bands 10/11 to spectral radiance
  - ASTER Radiance      — ASTER TIR bands 10-14 to spectral radiance

Brightness Temperature
  - Brightness Temperature — Radiance to BT using K1/K2 calibration
                             constants: BT = K2 / ln(K1/L + 1)

Land Surface Emissivity
  - Zhang LSE          — NDVI-threshold method (Zhang et al.)
  - NDVI Threshold LSE — NDVI threshold with proportion of vegetation
                         and cavity effect correction
  - ASTER LSE          — ASTER-specific LSE using MODIS emissivity values

Land Surface Temperature
  - Planck Equation LST      — Emissivity-corrected Planck inversion
  - Mono-Window Algorithm    — Qin et al. (2001); requires atmospheric
                               transmittance and near-surface air temperature
  - Single Channel Algorithm — Jimenez-Munoz & Sobrino (2003); requires
                               atmospheric water vapor content
  - Radiative Transfer Eq.   — Full atmospheric correction using upwelling
                               and downwelling radiance
  - ASTER Single Channel     — ASTER bands 13/14 with MODTRAN4 parameters
  - ASTER Split-Window       — ASTER bands 13 and 14 combined

Temperature output available in Kelvin, Celsius, or Fahrenheit.


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
