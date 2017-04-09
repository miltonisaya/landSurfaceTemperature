# -*- coding: utf-8 -*-
"""
/***************************************************************************
 LandSurfaceTemperatureDialog
                                 A QGIS plugin
 This tool extracts Land Surface Temperature from satellite imagery
                             -------------------
        begin                : 2015-11-10
        git sha              : $Format:%H$
        copyright            : (C) 2015 by Milton Isaya/Anadolu University
        email                : milton_issaya@hotmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import numpy as np
from osgeo import gdal
from osgeo import ogr
import os, sys, struct
from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import *
from qgis.core import *
from numpy import zeros
from numpy import logical_and
import traceback

#The imports below are done to enable the code in different directories to work in PyQGis
import sys
sys.path.append('~/Scripts/python')
from LandSurfaceTemperature.lst_tool_dialog import LandSurfaceTemperatureDialog as lst_dialog

class EstimateLST(QtCore.QObject):
    def __init__(self, geoProcessName, *args):
        QtCore.QObject.__init__(self)
        self.geoProcessName = geoProcessName
        self.args   = args[0]
        self.abort  = False
        self.killed = False
        
    def asterSWAalgorithm(self, b13BriTemp, b14BriTemp, b13Lse, b14Lse, b13atmTrans, b14atmTrans, outputPath, rasterType, unit, addToQGIS):
        try:
            #Open the raster datasets
            dsB13BriTemp = gdal.Open(b13BriTemp, gdal.GA_ReadOnly)
            dsB14BriTemp = gdal.Open(b14BriTemp, gdal.GA_ReadOnly)
            dsB13Lse     = gdal.Open(b13Lse, gdal.GA_ReadOnly)
            dsB14Lse     = gdal.Open(b14Lse, gdal.GA_ReadOnly)
            self.progress.emit(20)
        except IOError, e:
            self.error.emit(e, traceback.format_exc())
            self.kill()
        try:
            #Capture the bands to be used in the algorithm
            band13Bt  = dsB13BriTemp.GetRasterBand(1)
            band14Bt  = dsB14BriTemp.GetRasterBand(1)
            band13Lse = dsB13Lse.GetRasterBand(1)
            band14Lse = dsB14Lse.GetRasterBand(1)
                    
            # get numbers of rows and columns in the bands
            colsBT = dsB13BriTemp.RasterXSize
            rowsBT = dsB13BriTemp.RasterYSize
                
            # create the output image
            driver = gdal.GetDriverByName(rasterType)
            lstDS = driver.Create(outputPath, colsBT, rowsBT, 1, gdal.GDT_Float32)
            lstDS.SetGeoTransform(dsB13BriTemp.GetGeoTransform())
            lstDS.SetProjection(dsB13BriTemp.GetProjection())
            lstBand = lstDS.GetRasterBand(1)
            
            self.progress.emit(40)
            # loop through rows of blocks
            blockSize = 64
            for i in range(0, rowsBT, blockSize):
                if i + blockSize < rowsBT:
                    numRows = blockSize
                else:
                    numRows = rowsBT - i
                
                # now loop through the blocks in the row
                for j in range(0, colsBT, blockSize):
                    if j + blockSize < colsBT:
                        numCols = blockSize
                    else:
                        numCols = colsBT - j
                        
                    #Get the data
                    bt13Data      = band13Bt.ReadAsArray(j, i, numCols, numRows).astype('f')
                    bt14Data      = band14Bt.ReadAsArray(j, i, numCols, numRows).astype('f')
                    band13LseData = dsB13Lse.ReadAsArray(j, i, numCols, numRows).astype('f')
                    band14LseData = dsB14Lse.ReadAsArray(j, i, numCols, numRows).astype('f')
                
                    #Do the calculation here
                    #Calculate A13
                    A13 = np.multiply(0.145236, band13LseData)
                    A13 = np.multiply(A13, b13atmTrans)
                    
                    #Calculate B13
                    B13a = np.multiply(0.145236, bt13Data)
                    B13b = np.multiply(33.685, band13LseData)
                    B13b = np.multiply(B13b, b13atmTrans)
                    B13  = np.add(B13a, B13b)
                    B13  = np.subtract(B13, 33.685)
                    
                    #Calculate C13
                    C13a = np.subtract(1.0, b13atmTrans)
                    C13b = np.subtract(1.0, band13LseData)
                    C13b = np.multiply(C13b, b13atmTrans)
                    C13b = np.add(C13b, 1.0)
                    C13  = np.multiply(C13b, C13a)
                    C13  = np.multiply(C13, 0.145236)
                    
                    #Calculate D13
                    D13a = np.subtract(1.0, b13atmTrans)
                    D13b = np.subtract(1.0, band13LseData)
                    D13b = np.multiply(D13b, b13atmTrans)
                    D13b = np.add(D13b,1.0)
                    D13  = np.multiply(D13b, D13a)
                    D13  = np.multiply(D13, 33.685)
                    
                    #Calculate A14
                    A14 = np.multiply(0.13266, band14LseData)
                    A14 = np.multiply(A14, b14atmTrans)
                    
                    #Calculate B14
                    B14a = np.multiply(0.13266, bt14Data)
                    B14b = np.multiply(30.273, band14LseData)
                    B14b = np.multiply(B14b, b14atmTrans)
                    B14  = np.add(B14a, B14b)
                    B14  = np.subtract(B14, 30.273)
                    
                    #Calculate C14
                    C14a = np.subtract(1.0, b14atmTrans)
                    C14b = np.subtract(1.0, band14LseData)
                    C14b = np.multiply(C14b, b14atmTrans)
                    C14b = np.add(C14b, 1.0)
                    C14  = np.multiply(C14a, C14b)
                    C14  = np.multiply(C14b, 0.13266)

                    #Calculate D14
                    D14a = np.subtract(1.0, b14atmTrans)
                    D14b = np.subtract(1.0, band14LseData)
                    D14b = np.multiply(D14b, b14atmTrans)
                    D14b = np.add(D14b, 1.0)
                    D14  = np.multiply(D14a, D14b)
                    D14  = np.multiply(D14, 30.273)
                    
                    #Put everything together and calculate lst
                    lst_1   = np.add(D13, B13)
                    lst_1   = np.multiply(lst_1, C14)
                    
                    lst_2   = np.add(D14, B14)
                    lst_2   = np.multiply(C13, lst_2)
                    
                    lst_3a  = np.multiply(C14, A13)
                    lst_3b  = np.multiply(C13, A14)
                    lst_3   = np.subtract(lst_3a, lst_3b)
                    
                    lst     = np.subtract(lst_1, lst_2)
                    #lst     = np.divide(lst, lst_3)
                    
                    #Avoid division by zero
                    con_lst = [lst != 0, lst == 0]
                    cho_lst = [np.divide(lst, lst_3), 0]
                    lst     = np.select(con_lst, cho_lst)
                    
                    #Convert the temperature according to the unit selected
                    if (unit == 'Kelvin'):
                        pass
                    elif (unit == 'Celsius'):
                        #Celsius = Kelvin - 273.15
                        lst = np.subtract(lst, 273.15)
                    else:
                        #Fahrenheit = ((kelvin - 273.15) x 1.8) + 32
                        lst = np.subtract(lst, 273.15)
                        lst = np.multiply(lst, 1.8)
                        lst = np.add(lst, 32)
                    
                    #Convert the temperature according to the unit selected
                    if (unit == 'Kelvin'):
                        pass
                    elif (unit == 'Celsius'):
                        #Celsius = Kelvin - 273.15
                        lst = np.subtract(lst, 273.15)
                    else:
                        #Fahrenheit = ((kelvin - 273.15) x 1.8) + 32
                        lst = np.subtract(lst, 273.15)
                        lst = np.multiply(lst, 1.8)
                        lst = np.add(lst, 32)
                    
                    # write the data
                    lstBand.WriteArray(lst, j, i)

            self.progress.emit(90)
            # set the histogram
            lstBand.SetNoDataValue(-99)
            histogram = lstBand.GetDefaultHistogram()
            lstBand.SetDefaultHistogram(histogram[0], histogram[1], histogram[3])
                
            lstDS = None
            
            #Add the output to QGIS
            ret = outputPath
            if (addToQGIS == 'Yes'):
                self.progress.emit(100)
                self.finished.emit(ret)
            else:
                ret = None
                self.progress.emit(100)
                self.finished.emit(ret)
        except RuntimeError, e:
            self.error.emit(e, traceback.format_exc())
    
    
    def asterLSE(self, bandNo, ndvi, outputPath, rasterType, addToQGIS):
        try:
            #The code below opens the NDVI raster
            dsNdviBand = gdal.Open(ndvi, gdal.GA_ReadOnly)
            self.progress.emit(20)
        except IOError, e:
            self.error.emit(e, traceback.format_exc())
            self.kill()
        try:
            #Capture the NDVI band
            ndviBand = dsNdviBand.GetRasterBand(1)
            
            #Get number of rows and columns in the Red and NIR bands
            cols = dsNdviBand.RasterXSize
            rows = dsNdviBand.RasterYSize
                    
            #Create the output image
            driver = gdal.GetDriverByName(rasterType)
            lseDS = driver.Create(outputPath, cols, rows, 1, gdal.GDT_Float32)
            lseDS.SetGeoTransform(dsNdviBand.GetGeoTransform())
            lseDS.SetProjection(dsNdviBand.GetProjection())
            radianceBand = lseDS.GetRasterBand(1)
            self.progress.emit(40)
                    
            #Read the block sizes of the band being processed
            blockSizes = radianceBand.GetBlockSize()
            xBlockSize = blockSizes[0]
            yBlockSize = blockSizes[1]
                
            #Get the statistics of the NDVI band
            stats = ndviBand.GetStatistics(0,1)
            ndviMax = stats[1]
            ndviMin = stats[0]
                  
            # loop through rows of blocks
            for i in range(0, rows, yBlockSize):
                if i + yBlockSize < rows:
                    numRows = yBlockSize
                else:
                    numRows = rows - i
                        
                # now loop through the blocks in the row
                for j in range(0, cols, xBlockSize):
                    if j + xBlockSize < cols:
                        numCols = xBlockSize
                    else:
                        numCols = cols - j
                    # get the data
                    ndviData  = ndviBand.ReadAsArray(j, i, numCols, numRows).astype('f')
                    #Calculate the proportion of vegetaton
                    '''
                    Set the PV = 1 for all pixels whose NDVI is greater than 0.5 and set the PV = 0 for all pixels whose NDVI
                    is less than 0.2. The PV equation is used for the pixels whose NDVI values are between 0.2 and 0.5.
                    '''
                    Pv_Con_List = [ndviData > 0.5, ndviData < 0.2, np.logical_and(ndviData > 0.2 ,ndviData < 0.5)]
                    Pv_Eqn_Upper = np.subtract(ndviData, ndviMin)
                    Pv_Eqn_Lower = np.subtract(ndviMax, ndviMin)
                    Pv_Eqn       = np.divide(Pv_Eqn_Upper, Pv_Eqn_Lower)
                    Pv_Eqn       = np.multiply(Pv_Eqn, Pv_Eqn)
                    Pv_Cho_List  = [1, 0, Pv_Eqn]
                    Pv           = np.select(Pv_Con_List, Pv_Cho_List)

                    #Calculate the LSE according to the bands selected
                    '''The emissivities of soil, water and vegetation have been obtained from MODIS USCB Emissivity Library
                                                http://www.icess.ucsb.edu/modis/EMIS/html/em.html
                    '''
                    if (int(bandNo) == 10):
                        lse_math = np.multiply(Pv, 0.044)
                        lse_math = np.add(lse_math, 0.946)
                        lse_con_list = [np.logical_and(ndviData >= -1, ndviData < -0.185), np.logical_and(ndviData >= -0.185, ndviData <= 0.2), np.logical_and(ndviData >= 0.2, ndviData < 0.7), np.logical_and(ndviData >= 0.7, ndviData <= 1) ]
                        lse_cho_list = [0.991, 0.966, lse_math, 0.973]
                        lse = np.select(lse_con_list, lse_cho_list)
                    elif (int(bandNo) == 11):
                        lse_math = np.multiply(Pv, 0.041)
                        lse_math = np.add(lse_math, 0.949)
                        lse_con_list = [np.logical_and(ndviData >= -1, ndviData < -0.185), np.logical_and(ndviData >= -0.185, ndviData <= 0.2), np.logical_and(ndviData >= 0.2, ndviData < 0.7), np.logical_and(ndviData >= 0.7, ndviData <= 1) ]
                        lse_cho_list = [0.991, 0.966, lse_math, 0.973]
                        lse = np.select(lse_con_list, lse_cho_list)
                    elif (int(bandNo) == 12):
                        lse_math = np.multiply(Pv, 0.049)
                        lse_math = np.add(lse_math, 0.941)
                        lse_con_list = [np.logical_and(ndviData >= -1, ndviData < -0.185), np.logical_and(ndviData >= -0.185, ndviData <= 0.2), np.logical_and(ndviData >= 0.2, ndviData < 0.7), np.logical_and(ndviData >= 0.7, ndviData <= 1) ]
                        lse_cho_list = [0.991, 0.966, lse_math, 0.973]
                        lse = np.select(lse_con_list, lse_cho_list)
                    elif (int(bandNo) == 13):
                        lse_math = np.multiply(Pv, 0.022)
                        lse_math = np.add(lse_math, 0.968)
                        lse_con_list = [np.logical_and(ndviData >= -1, ndviData < -0.185), np.logical_and(ndviData >= -0.185, ndviData <= 0.2), np.logical_and(ndviData >= 0.2, ndviData < 0.7), np.logical_and(ndviData >= 0.7, ndviData <= 1) ]
                        lse_cho_list = [0.991, 0.966, lse_math, 0.973]
                        lse = np.select(lse_con_list, lse_cho_list)
                    elif (int(bandNo) == 14):
                        lse_math = np.multiply(Pv, 0.020)
                        lse_math = np.add(lse_math, 0.970)
                        lse_con_list = [np.logical_and(ndviData >= -1, ndviData < -0.185), np.logical_and(ndviData >= -0.185, ndviData <= 0.2), np.logical_and(ndviData >= 0.2, ndviData < 0.7), np.logical_and(ndviData >= 0.7, ndviData <= 1) ]
                        lse_cho_list = [0.991, 0.966, lse_math, 0.973]
                        lse = np.select(lse_con_list, lse_cho_list)
                    #Write the data
                    lseDS.GetRasterBand(1).WriteArray(lse, j, i)
            
            self.progress.emit(90)                
            # set the histogram
            lseDS.GetRasterBand(1).SetNoDataValue(-99)
            histogram = lseDS.GetRasterBand(1).GetDefaultHistogram()
            lseDS.GetRasterBand(1).SetDefaultHistogram(histogram[0], histogram[1], histogram[3])
        
            lseDS      = None
            dsNdviBand = None
            #Add the output to QGIS
            ret = outputPath
            if (addToQGIS == 'Yes'):
                self.progress.emit(100)
                self.finished.emit(ret)
            else:
                ret = None
                self.progress.emit(100)
                self.finished.emit(ret)
                
        except RuntimeError, e:
            self.error.emit(e, traceback.format_exc())
            
    def asterSingleChannelAlg(self, lse, radiance, briTemp, atmWaterVap, bandNo, modtran, outputPath, unit, rasterType, addToQGIS):
        try:
            #The code below opens the datasets
            dsBT  = gdal.Open(briTemp, gdal.GA_ReadOnly)
            dsLSE = gdal.Open(lse, gdal.GA_ReadOnly)
            dsRad = gdal.Open(radiance, gdal.GA_ReadOnly)
            self.progress.emit(20)
        except IOError, e:
            self.error.emit(e, traceback.format_exc())
            self.kill()
        try:
            #Capture the LSE, Radiance and the Brightness Temperature bands
            btBand  = dsBT.GetRasterBand(1)
            lseBand = dsLSE.GetRasterBand(1)
            radBand = dsRad.GetRasterBand(1)
                    
            # get numbers of rows and columns in the bands
            colsBT = dsBT.RasterXSize
            rowsBT = dsBT.RasterYSize
                
            # create the output image
            driver = gdal.GetDriverByName(rasterType)
            lstDS = driver.Create(outputPath, colsBT, rowsBT, 1, gdal.GDT_Float32)
            lstDS.SetGeoTransform(dsBT.GetGeoTransform())
            lstDS.SetProjection(dsBT.GetProjection())
            lstBand = lstDS.GetRasterBand(1)
            
            self.progress.emit(40)
            #Use the required MODTRAN4 Database according to the profile selected by the user
            if (int(bandNo) == 13 and modtran == 'STD66'):
                parameter_1 = (0.06524   * (atmWaterVap ** 2)) - (0.05878 * atmWaterVap) + 1.06576
                parameter_2 = (-0.55835  * (atmWaterVap ** 2)) - (0.75881 * atmWaterVap) + 0.00327
                parameter_3 = (-0.00284  * (atmWaterVap ** 2)) + (1.35633 * atmWaterVap) - 0.43020
                K1          = 865.65
                K2          = 1349.82
            if (int(bandNo) == 14 and modtran == 'STD66'):
                parameter_1 = (0.10062   * (atmWaterVap ** 2)) - (0.13563 * atmWaterVap) + 1.10559
                parameter_2 = (-0.79740  * (atmWaterVap ** 2)) - (0.39414 * atmWaterVap) + 0.17664
                parameter_3 = (-0.03091  * (atmWaterVap ** 2)) + (1.60094 * atmWaterVap) - 0.56515
                K1          = 649.60
                K2          = 1274.49
            if (int(bandNo) == 13 and modtran == 'TIGR61'):
                parameter_1 = (0.05327   * (atmWaterVap ** 2)) - (0.03937 * atmWaterVap) + 1.05742
                parameter_2 = (-0.48444  * (atmWaterVap ** 2)) - (0.74611 * atmWaterVap) - 0.03015
                parameter_3 = (0.00764   * (atmWaterVap ** 2)) + (1.24532 * atmWaterVap) - 0.39461
                K1          = 865.65
                K2          = 1349.82
            if (int(bandNo) == 14 and modtran == 'TIGR61'):
                parameter_1 = (0.07965   * (atmWaterVap ** 2)) - (0.09580 * atmWaterVap) + 1.08983
                parameter_2 = (-0.66528  * (atmWaterVap ** 2)) - (0.48582 * atmWaterVap) - 0.17029
                parameter_3 = (-0.01578  * (atmWaterVap ** 2)) + (1.46358 * atmWaterVap) - 0.52486
                K1          = 649.60
                K2          = 1274.49
                
            # loop through rows of blocks
            blockSize = 64
            for i in range(0, rowsBT, blockSize):
                if i + blockSize < rowsBT:
                    numRows = blockSize
                else:
                    numRows = rowsBT - i
                
                # now loop through the blocks in the row
                for j in range(0, colsBT, blockSize):
                    if j + blockSize < colsBT:
                        numCols = blockSize
                    else:
                        numCols = colsBT - j
                        
                    # get the data
                    lseData = lseBand.ReadAsArray(j, i, numCols, numRows).astype('f')
                    btData  = btBand.ReadAsArray(j, i, numCols, numRows).astype('f')
                    radData = radBand.ReadAsArray(j, i, numCols, numRows).astype('f')
                
                    # do the calculation here
                    #Calculation of the gamma parameter
                    gamma_upper = np.multiply(btData, btData)
                    gamma_lower = np.multiply(K2, radData)
                    gamma       = np.divide(gamma_upper, gamma_lower)
                    
                    #Calculation of the delta parameter
                    delta_upper = np.multiply(btData, btData)
                    delta       = np.divide(delta_upper, K2)
                    delta       = np.subtract(btData, delta)
                    
                    #Use the ASTER's single channel algorithm
                    inv_lse  = np.divide(lseData, -1)
                    par1Lsen = np.multiply(parameter_1, radData)
                    a        = np.add(par1Lsen, parameter_2)
                    a        = np.multiply(inv_lse, a)
                    lst      = np.add(a, parameter_3)
                    lst      = np.multiply(gamma, lst)
                    lst      = np.add(lst, delta)
                    #Convert the temperature according to the unit selected
                    if (unit == 'Kelvin'):
                        pass
                    elif (unit == 'Celsius'):
                        #Celsius = Kelvin - 273.15
                        lst = np.subtract(lst, 273.15)
                    else:
                        #Fahrenheit = ((kelvin - 273.15) x 1.8) + 32
                        lst = np.subtract(lst, 273.15)
                        lst = np.multiply(lst, 1.8)
                        lst = np.add(lst, 32)
                    
                    #The Single Channel Algorithm Equation is coded below
                    lst     = np.multiply(radData, parameter_1)
                    lst     = np.add(lst, parameter_2)
                    
                    #Avoid the inverse of a zero
                    zr_con  = [lseData != 0, lseData == 0]
                    zr_cho  = [lseData ** -1, 1]
                    inv_lse = np.select(zr_con, zr_cho)
                    
                    lst     = np.multiply(inv_lse, lst)
                    lst     = np.add(lst, parameter_3)
                    lst     = np.multiply(gamma, lst)
                    
                    #Convert the temperature according to the unit selected
                    if (unit == 'Kelvin'):
                        lst = np.add(lst, delta)
                    elif (unit == 'Celsius'):
                        #Celsius = Kelvin - 273.15
                        lst = np.add(lst, delta)
                        lst = np.subtract(lst, 273.15)
                    else:
                        #Fahrenheit = ((kelvin - 273.15) x 1.8) + 32
                        lst = np.add(lst, delta)
                        lst = np.subtract(lst, 273.15)
                        lst = np.multiply(lst, 1.8)
                        lst = np.add(lst, 32)
                    
                    # write the data
                    lstDS.GetRasterBand(1).WriteArray(lst, j, i)
                    
            self.progress.emit(90)
            # set the histogram
            lstDS.GetRasterBand(1).SetNoDataValue(-99)
            histogram = lstDS.GetRasterBand(1).GetDefaultHistogram()
            lstDS.GetRasterBand(1).SetDefaultHistogram(histogram[0], histogram[1], histogram[3])
                
            lstDS    = None
            lseBand  = None
            btBand   = None
            
            #Add the output to QGIS
            ret = outputPath
            if (addToQGIS == 'Yes'):
                self.progress.emit(100)
                self.finished.emit(ret)
            else:
                ret = None
                self.progress.emit(100)
                self.finished.emit(ret)
        except RuntimeError, e:
            self.error.emit(e, traceback.format_exc())
    
    def calcAsterRadiance(self, thermalBand, bandNumber, outputPath, rasterType, addToQGIS):
        try:
            #The code below opens the datasets
            dsThermalBand = gdal.Open(thermalBand, gdal.GA_ReadOnly)
            self.progress.emit(20)
        except IOError, e:
            self.error.emit(e, traceback.format_exc())
        try:
            bandNo = int(bandNumber)
            if (bandNo == 10):
                rasterBand = 1
            elif (bandNo == 11):
                rasterBand = 2
            elif (bandNo == 12):
                bandNo = 3
            elif (bandNo == 13):
                rasterBand = 4
            elif (bandNo ==14):
                rasterBand = 5
            #Capture the thermal band selected by the user
            thermalBand = dsThermalBand.GetRasterBand(rasterBand)
                
            # get number of rows and columns in the bands
            cols = dsThermalBand.RasterXSize
            rows = dsThermalBand.RasterYSize
            
            #Assign the unit conversion value according to the thermal band in use
            if (bandNo == 10):
                UCC = 0.006822
            elif (bandNo == 11):
                UCC = 0.006780
            elif (bandNo == 12):
                UCC = 0.006590
            elif (bandNo == 13):
                UCC = 0.005693
            elif (bandNo == 14):
                UCC = 0.005225
       
            # create the output image
            driver = gdal.GetDriverByName(rasterType)
            radianceDS = driver.Create(outputPath, cols, rows, 1, gdal.GDT_Float32)
            radianceDS.SetGeoTransform(dsThermalBand.GetGeoTransform())
            radianceDS.SetProjection(dsThermalBand.GetProjection())
            radianceBand = radianceDS.GetRasterBand(1)
            self.progress.emit(40)
            
            #Read the block sizes of the thermal band being processed
            blockSizes = radianceBand.GetBlockSize()
            xBlockSize = blockSizes[0]
            yBlockSize = blockSizes[1]
                    
            # loop through rows of blocks
            for i in range(0, rows, yBlockSize):
                if i + yBlockSize < rows:
                    numRows = yBlockSize
                else:
                    numRows = rows - i
                
                # now loop through the blocks in the row
                for j in range(0, cols, xBlockSize):
                    if j + xBlockSize < cols:
                        numCols = xBlockSize
                    else:
                        numCols = cols - j
                    #Read the data and do the calculation
                    thermalBandData = thermalBand.ReadAsArray(j, i, numCols, numRows).astype('f')
                    # do the calculation
                    radiance = np.subtract(thermalBandData, 1)
                    radiance = np.multiply(radiance, UCC)
                    # write the data
                    radianceDS.GetRasterBand(1).WriteArray(radiance,j,i)
                    
            self.progress.emit(90)        
            # set the histogram
            radianceDS.GetRasterBand(1).SetNoDataValue(-99)
            histogram = radianceDS.GetRasterBand(1).GetDefaultHistogram()
            radianceDS.GetRasterBand(1).SetDefaultHistogram(histogram[0], histogram[1], histogram[3])

            radianceDS    = None
            dsThermalBand = None
            #Add the output to QGIS
            ret = outputPath
            if (addToQGIS == 'Yes'):
                self.progress.emit(100)
                self.finished.emit(ret)
            else:
                ret = None
                self.progress.emit(100)
                self.finished.emit(ret)
        except RuntimeError, e:
            self.error.emit(e, traceback.format_exc())
    
    def calcAsterNDVI(self, VNIRBandPath, outputPath, rasterType, addToQGIS):
        try:
            #The code below opens the datasets
            dsVNIRBand = gdal.Open(VNIRBandPath, gdal.GA_ReadOnly)
            self.progress.emit(20)
        except IOError, e:
            self.error.emit(e, traceback.format_exc())
        try:
            #Capture the Red and the NIR bands
            redBand = dsVNIRBand.GetRasterBand(2)
            NIRBand = dsVNIRBand.GetRasterBand(3)

            # get numbers of rows and columns in the bands
            colsRed = dsVNIRBand.RasterXSize
            rowsRed = dsVNIRBand.RasterYSize

            # create the output image
            driver = gdal.GetDriverByName(rasterType)
            ndviDS = driver.Create(outputPath, colsRed, rowsRed, 1, gdal.GDT_Float32)
            ndviDS.SetGeoTransform(dsVNIRBand.GetGeoTransform())
            ndviDS.SetProjection(dsVNIRBand.GetProjection())
            ndviBand = ndviDS.GetRasterBand(1)
            self.progress.emit(40)
                
            # loop through rows of blocks
            blockSize = 64
            for i in range(0, rowsRed, blockSize):
                if i + blockSize < rowsRed:
                    numRows = blockSize
                else:
                    numRows = rowsRed - i

                # now loop through the blocks in the row
                for j in range(0, colsRed, blockSize):
                    if j + blockSize < colsRed:
                        numCols = blockSize
                    else:
                        numCols = colsRed - j
                    # get the data
                    redBandData = redBand.ReadAsArray(j, i, numCols, numRows).astype('f')
                    NIRBandData = NIRBand.ReadAsArray(j, i, numCols, numRows).astype('f')
                    # do the calculation
                    mask = np.greater(redBandData + NIRBandData, 0)
                    ndvi = np.choose(mask, (-99, (NIRBandData - redBandData) / (NIRBandData + redBandData)))
                    # write the data
                    ndviDS.GetRasterBand(1).WriteArray(ndvi, j, i)

            self.progress.emit(90)
            # set the histogram
            ndviDS.GetRasterBand(1).SetNoDataValue(-99)
            histogram = ndviDS.GetRasterBand(1).GetDefaultHistogram()
            ndviDS.GetRasterBand(1).SetDefaultHistogram(histogram[0], histogram[1], histogram[3])

            ndviDS   = None
            #Add the output to QGIS
            ret = outputPath
            if (addToQGIS == 'Yes'):
                self.progress.emit(100)
                self.finished.emit(ret)
            else:
                ret = None
                self.progress.emit(100)
                self.finished.emit(ret)
                    
        except RuntimeError, e:
            self.error.emit(e, traceback.format_exc())
            self.progress.emit(100)
    
    def ndviThresholdLSEAlgorithm(self, ndviRaster, outputPath, rasterType, addToQGIS):
        try:
            #The code below opens the datasets
            dsNdviBand = gdal.Open(ndviRaster, gdal.GA_ReadOnly)
            self.progress.emit(20)
        except IOError, e:
            self.error.emit(e, traceback.format_exc())
        try:
            #Capture the Red and the NIR bands
            ndviBand = dsNdviBand.GetRasterBand(1)
                        
            # get number of rows and columns in the Red and NIR bands
            cols = dsNdviBand.RasterXSize
            rows = dsNdviBand.RasterYSize
                    
            # create the output image
            driver = gdal.GetDriverByName(rasterType)
            lseDS = driver.Create(outputPath, cols, rows, 1, gdal.GDT_Float32)
            lseDS.SetGeoTransform(dsNdviBand.GetGeoTransform())
            lseDS.SetProjection(dsNdviBand.GetProjection())
            radianceBand = lseDS.GetRasterBand(1)
            self.progress.emit(40)
                    
            #Read the block sizes of the band being processed
            blockSizes = radianceBand.GetBlockSize()
            xBlockSize = blockSizes[0]
            yBlockSize = blockSizes[1]
                
            #Get the statistics of the NDVI band
            stats = ndviBand.GetStatistics(0,1)
            ndviMax = stats[1]
            ndviMin = stats[0]
            ev  = 0.973 #Emissivity of vegetation
            es  = 0.966 #Emissivity of soil
            ew  = 0.991 #Emissivity of water
                  
            # loop through rows of blocks
            for i in range(0, rows, yBlockSize):
                if i + yBlockSize < rows:
                    numRows = yBlockSize
                else:
                    numRows = rows - i
                        
                # now loop through the blocks in the row
                for j in range(0, cols, xBlockSize):
                    if j + xBlockSize < cols:
                        numCols = xBlockSize
                    else:
                        numCols = cols - j
                    # get the data
                    ndviData  = ndviBand.ReadAsArray(j, i, numCols, numRows).astype('f')
                    #Do the calculation here
                    water_logic   = np.logical_and(ndviData >= -1,ndviData < -0.185)
                    soil_logic    = np.logical_and(ndviData >= -0.185, ndviData < 0.2)
                    mixed_logic   = np.logical_and(ndviData >= 0.2, ndviData < 0.5)
                    veg_logic     = np.logical_and(ndviData > 0.5, ndviData <= 1)
                    conditionList = [water_logic, soil_logic, mixed_logic, veg_logic]
                    
                    Pv_Upper      = np.subtract(ndviData, ndviMin)
                    Pv_Lower      = np.subtract(ndviMax, ndviMin)
                    Pv            = np.divide(Pv_Upper, Pv_Lower)
                    Pv            = np.multiply(Pv, Pv)
                    #Find the cavity value
                    x             = np.subtract(1, es)
                    evf           = np.multiply(ev, 0.55)
                    y             = np.subtract(1, Pv)
                    C             = np.multiply(x, evf)
                    C             = np.multiply(C, y)
                    EvPv          = np.multiply(ev,Pv)
                    b             = np.multiply(es,np.subtract(1, Pv))
                    mixedPixels   = np.add(EvPv, b)
                    mixedPixels   = np.add(mixedPixels, C)
                    choiceList    = [ew, es, mixedPixels, ev]
                    lse           = np.select(conditionList, choiceList)
            
            self.progress.emit(90)                
            # set the histogram
            lseDS.GetRasterBand(1).SetNoDataValue(-99)
            histogram = lseDS.GetRasterBand(1).GetDefaultHistogram()
            lseDS.GetRasterBand(1).SetDefaultHistogram(histogram[0], histogram[1], histogram[3])
        
            lseDS      = None
            dsNdviBand = None
            #Add the output to QGIS
            ret = outputPath
            if (addToQGIS == 'Yes'):
                self.progress.emit(100)
                self.finished.emit(ret)
            else:
                ret = None
                self.progress.emit(100)
                self.finished.emit(ret)
                
        except RuntimeError, e:
            self.error.emit(e, traceback.format_exc())

    def zhangLSEalgorithm(self, ndviRaster, outputPath, rasterType, addToQGIS):
        try:
            #The code below opens the datasets
            dsNdviBand = gdal.Open(ndviRaster, gdal.GA_ReadOnly)
            self.progress.emit(20)
        except IOError, e:
            self.error.emit(e, traceback.format_exc())
            
        try:
            
            #Capture the Red and the NIR bands
            ndviBand = dsNdviBand.GetRasterBand(1)
                    
            # get number of rows and columns in the Red and NIR bands
            cols = dsNdviBand.RasterXSize
            rows = dsNdviBand.RasterYSize
                
            # create the output image
            driver = gdal.GetDriverByName(rasterType)
            lseDS = driver.Create(outputPath, cols, rows, 1, gdal.GDT_Float32)
            lseDS.SetGeoTransform(dsNdviBand.GetGeoTransform())
            lseDS.SetProjection(dsNdviBand.GetProjection())
            radianceBand = lseDS.GetRasterBand(1)
            
            self.progress.emit(40)
            #Read the block sizes of the thermal band being processed
            blockSizes = radianceBand.GetBlockSize()
            xBlockSize = blockSizes[0]
            yBlockSize = blockSizes[1]
                        
            # loop through rows of blocks
            for i in range(0, rows, yBlockSize):
                if i + yBlockSize < rows:
                    numRows = yBlockSize
                else:
                    numRows = rows - i
                    
                # now loop through the blocks in the row
                for j in range(0, cols, xBlockSize):
                    if j + xBlockSize < cols:
                        numCols = xBlockSize
                    else:
                        numCols = cols - j
                    # get the data
                    ndviData  = ndviBand.ReadAsArray(j, i, numCols, numRows).astype('f')
                    #Do the calculation here
                    conditionList = [np.logical_and(ndviData < -0.185, ndviData >= -1), np.logical_and(ndviData >= -0.185, ndviData <= 0.157), np.logical_and(ndviData >= 0.157, ndviData <= 0.727), np.logical_and(ndviData > 0.727, ndviData <= 1)]
                    mixedPixels   = np.log(ndviData)
                    mixedPixels   = np.multiply(mixedPixels, 0.047)
                    mixedPixels   = np.add(mixedPixels, 1.009)
                    choiceList    = [0.995, 0.985, mixedPixels, 0.990]
                    lse           = np.select(conditionList, choiceList)
                    
                    # write the data
                    lseDS.GetRasterBand(1).WriteArray(lse, j, i)
            
            self.progress.emit(90)
            # set the histogram
            lseDS.GetRasterBand(1).SetNoDataValue(-99)
            histogram = lseDS.GetRasterBand(1).GetDefaultHistogram()
            lseDS.GetRasterBand(1).SetDefaultHistogram(histogram[0], histogram[1], histogram[3])
    
            lseDS      = None
            dsNdviBand = None
            #Add the output to QGIS
            ret = outputPath
            if (addToQGIS == 'Yes'):
                self.progress.emit(100)
                self.finished.emit(ret)
            else:
                ret = None
                self.progress.emit(100)
                self.finished.emit(ret)
        except RuntimeError, e:
            self.error.emit(e, traceback.format_exc())

    def radiativeTransferEquation(self, sensorType, bandNo, upWellingRadiance, downWellingRadiance, toaRadiance, atmTrans, lse, outputPath, unit, rasterFormat, addToQGIS):
        try:
            #The code below opens the datasets
            dsTOA = gdal.Open(toaRadiance, gdal.GA_ReadOnly)
            dsLSE = gdal.Open(lse, gdal.GA_ReadOnly)
            self.progress.emit(20)
            
        except IOError, e:
            self.error.emit(e, traceback.format_exc())
        try:
            #Set the K1 and K2 constants
            if (sensorType == 'Landsat TIRS'):
                if (int(bandNo) == 10):
                    K1 = 774.89
                    K2 = 1321.08
                elif (int(bandNo) ==11):
                    K1 = 480.89
                    K2 = 1201.14
            elif (sensorType == 'Landsat ETM+'):
                K1 = 660.09
                K2 = 1282.71
            elif (sensorType == 'Landsat TM'):
                K1 = 607.76
                K2 = 1260.56
            #Capture the LSE and the Brightness Temperature bands
            toaBand = dsTOA.GetRasterBand(1)
            lseBand = dsLSE.GetRasterBand(1)
                    
            # get numbers of rows and columns in the Red and NIR bands
            colsTOA = dsTOA.RasterXSize
            rowsTOA = dsTOA.RasterYSize
                
            colsLSE = dsLSE.RasterXSize
            rowsLSE = dsLSE.RasterYSize
                
            # create the output image
            driver = gdal.GetDriverByName(str(rasterFormat))
            lstDS = driver.Create(outputPath, colsTOA, rowsTOA, 1, gdal.GDT_Float32)
            lstDS.SetGeoTransform(dsTOA.GetGeoTransform())
            lstDS.SetProjection(dsTOA.GetProjection())
            lstBand = lstDS.GetRasterBand(1)
            
            self.progress.emit(40)        
            # loop through rows of blocks
            blockSize = 64
            for i in range(0, rowsTOA, blockSize):
                if i + blockSize < rowsTOA:
                    numRows = blockSize
                else:
                    numRows = rowsTOA - i
                
                # now loop through the blocks in the row
                for j in range(0, colsTOA, blockSize):
                    if j + blockSize < colsTOA:
                        numCols = blockSize
                    else:
                        numCols = colsTOA - j
                        
                    # get the data
                    lseData  = lseBand.ReadAsArray(j, i, numCols, numRows).astype('f')
                    toaData  = toaBand.ReadAsArray(j, i, numCols, numRows).astype('f')
                
                    # Estimate the land surface radiance of kinetic temperature (LT)
                    #Left hand side of the equation
                    left  = np.subtract(toaData, float(upWellingRadiance))
                    te    = np.multiply(float(atmTrans), lseData) #The product of LSE and Atmospheric Transmittance
                    left  = np.divide(left, te)
                    #Right hand side of the equation
                    right = np.subtract(1, lseData)
                    #right = np.divide(right, lseData)
                    
                    cond_list   = [lseData < 0, lseData > 0]
                    choice_list = [1, np.divide(right, lseData)]
                    right       = np.select(cond_list, choice_list)
                    
                    right = np.multiply(right, float(downWellingRadiance))
                    LTS   = np.subtract(left, right)
                    
                    #Application of the planck equation to invert the radiance
                    plank_lower = np.divide(K1, LTS)
                    plank_lower = np.add(plank_lower, 1)
                    
                    log_cond_list   = [plank_lower == 0, lseData > 0]
                    log_choice_list = [1, np.log(plank_lower)]
                    plank_lower     = np.select(log_cond_list, log_choice_list)
                    
                    #plank_lower = np.log(plank_lower)
                    plank_cond_list   = [plank_lower == 0, plank_lower > 0]
                    plank_choice_list = [-99, (np.divide(K2,plank_lower))]
                    #lst         = np.divide(K2, plank_lower)
                    #Convert the temperature according to the unit selected
                    if (unit == 'Kelvin'):
                        lst = np.select(plank_cond_list, plank_choice_list)
                    elif (unit == 'Celsius'):
                        #Celsius = Kelvin - 273.15
                        lst = np.select(plank_cond_list, plank_choice_list)
                        lst = np.subtract(lst, 273.15)
                    else:
                        #Fahrenheit = ((kelvin - 273.15) x 1.8) + 32
                        lst = np.select(plank_cond_list, plank_choice_list)
                        lst = np.subtract(lst, 273.15)
                        lst = np.multiply(lst, 1.8)
                        lst = np.add(lst, 32)
                    # write the data
                    lstDS.GetRasterBand(1).WriteArray(lst, j, i)
            
            self.progress.emit(90)
            # set the histogram
            lstDS.GetRasterBand(1).SetNoDataValue(-99)
            histogram = lstDS.GetRasterBand(1).GetDefaultHistogram()
            lstDS.GetRasterBand(1).SetDefaultHistogram(histogram[0], histogram[1], histogram[3])
                
            lstDS     = None
            lseBand   = None
            toaBand   = None
            
            #Add the output to QGIS
            ret = outputPath
            if (addToQGIS == 'Yes'):
                self.progress.emit(100)
                self.finished.emit(ret)
            else:
                ret = None
                self.progress.emit(100)
                self.finished.emit(ret)
        except RuntimeError, e:
            self.error.emit(e, traceback.format_exc())
    
    def singleChannelAlgorithm(self, sensorType, atmWaterVapour, radiance,  bt, lse, outputPath, unit, rasterType, addToQGIS):
        try:
            #The code below opens the datasets
            dsBT = gdal.Open(bt, gdal.GA_ReadOnly)
            dsLSE = gdal.Open(lse, gdal.GA_ReadOnly)
            dsRad = gdal.Open(radiance, gdal.GA_ReadOnly)
            self.progress.emit(20)
        except IOError, e:
            self.error.emit(e, traceback.format_exc())
            self.kill()
        try:
            #Capture the LSE and the Brightness Temperature bands
            btBand = dsBT.GetRasterBand(1)
            lseBand = dsLSE.GetRasterBand(1)
            radBand = dsRad.GetRasterBand(1)
                    
            # get numbers of rows and columns in the Red and NIR bands
            colsBT = dsBT.RasterXSize
            rowsBT = dsBT.RasterYSize
                
            # create the output image
            driver = gdal.GetDriverByName(rasterType)
            lstDS = driver.Create(outputPath, colsBT, rowsBT, 1, gdal.GDT_Float32)
            lstDS.SetGeoTransform(dsBT.GetGeoTransform())
            lstDS.SetProjection(dsBT.GetProjection())
            lstBand = lstDS.GetRasterBand(1)
            self.progress.emit(40)
            
            #Convert the variables to float
            atmWaterVapour = float(atmWaterVapour)
            if (sensorType == 'Landsat TM/ETM+'):
                effWavelenth = 11.45  #Effective wavelength for Landsat TM/ETM+
            elif (sensorType == 'Landsat TIRS'):
                effWavelenth = 11.395  #Effective wavelength for Landsat TIRS
            psi_1 = (0.14714 * (atmWaterVapour ** 2)) - (0.15583 * atmWaterVapour) + 1.1234
            psi_2 = (-1.1836 * (atmWaterVapour ** 2)) - (0.37607 * atmWaterVapour) - 0.52894
            psi_3 = (-0.0455 * (atmWaterVapour ** 2)) + (1.8719 * atmWaterVapour) - 0.39071
            C1    = 119104000
            C2    = 14387.7
            # loop through rows of blocks
            blockSize = 64
            for i in range(0, rowsBT, blockSize):
                if i + blockSize < rowsBT:
                    numRows = blockSize
                else:
                    numRows = rowsBT - i
                
                # now loop through the blocks in the row
                for j in range(0, colsBT, blockSize):
                    if j + blockSize < colsBT:
                        numCols = blockSize
                    else:
                        numCols = colsBT - j
                        
                    # get the data
                    lseData = lseBand.ReadAsArray(j, i, numCols, numRows).astype('f')
                    TSensor  = btBand.ReadAsArray(j, i, numCols, numRows).astype('f')
                    LSensor = radBand.ReadAsArray(j, i, numCols, numRows).astype('f')
                
                    # do the calculation                    
                    #The gamma equation is coded below
                    gamma_1_upper = np.multiply(LSensor, C2)
                    gamma_1_lower = TSensor
                    
                    cond_list1    = [gamma_1_lower == 0, gamma_1_lower != 0]
                    choice_list1  = [0, np.divide(gamma_1_upper, gamma_1_lower)]
                    gamma_1       = np.select(cond_list1, choice_list1)
                    
                    gamma_2       = np.power(effWavelenth, 4)
                    gamma_2       = np.divide(gamma_2, C1)
                    gamma_2       = np.multiply(gamma_2, LSensor)
                    
                    gamma_3       = effWavelenth ** -1
                    
                    gamma         = np.add(gamma_2, gamma_3)
                    gamma         = np.multiply(gamma_1, gamma)
                    gamma         = gamma ** -1
                    
                    #The delta equation is coded below
                    delta = np.multiply(LSensor, -1)
                    delta = np.multiply(delta, gamma)
                    delta = np.add(delta, TSensor)
                    
                    #The Single Channel Algorithm Equation is coded below
                    lst     = np.multiply(LSensor, psi_1)
                    lst     = np.add(lst, psi_2)
                    inv_lse = lseData ** -1
                    lst     = np.multiply(inv_lse, lst)
                    lst     = np.add(lst, psi_3)
                    lst     = np.multiply(gamma, lst)
                    
                    #Convert the temperature according to the unit selected
                    if (unit == 'Kelvin'):
                        lst = np.add(lst, delta)
                    elif (unit == 'Celsius'):
                        #Celsius = Kelvin - 273.15
                        lst = np.add(lst, delta)
                        lst = np.subtract(lst, 273.15)
                    else:
                        #Fahrenheit = ((kelvin - 273.15) x 1.8) + 32
                        lst = np.add(lst, delta)
                        lst = np.subtract(lst, 273.15)
                        lst = np.multiply(lst, 1.8)
                        lst = np.add(lst, 32)
                    
                    # write the data
                    lstDS.GetRasterBand(1).WriteArray(lst, j, i)
                    
            self.progress.emit(90)
            # set the histogram
            lstDS.GetRasterBand(1).SetNoDataValue(-99)
            histogram = lstDS.GetRasterBand(1).GetDefaultHistogram()
            lstDS.GetRasterBand(1).SetDefaultHistogram(histogram[0], histogram[1], histogram[3])
                
            lstDS    = None
            lseBand  = None
            btBand   = None
            
            #Add the output to QGIS
            ret = outputPath
            if (addToQGIS == 'Yes'):
                self.progress.emit(100)
                self.finished.emit(ret)
            else:
                ret = None
                self.progress.emit(100)
                self.finished.emit(ret)
        except RuntimeError, e:
            self.error.emit(e, traceback.format_exc())

    def monoWindowAlgorithm(self, atmTrans, nearSurfTemp, atmProfile, bt, lse, outputPath, unit, rasterType, addToQGIS):
        #The code below opens the datasets
        try:
            dsBT = gdal.Open(bt, gdal.GA_ReadOnly)
            dsLSE = gdal.Open(lse, gdal.GA_ReadOnly)
            self.progress.emit(20)
        except IOError,e:
            self.error.emit(e, traceback.format_exc())
            self.kill()
        try:
            #Capture the LSE and the Brightness Temperature bands
            btBand = dsBT.GetRasterBand(1)
            lseBand = dsLSE.GetRasterBand(1)
                    
            # get numbers of rows and columns in the Red and NIR bands
            colsBT = dsBT.RasterXSize
            rowsBT = dsBT.RasterYSize
                
            # create the output image
            driver = gdal.GetDriverByName(rasterType)
            lstDS = driver.Create(outputPath, colsBT, rowsBT, 1, gdal.GDT_Float32)
            lstDS.SetGeoTransform(dsBT.GetGeoTransform())
            lstDS.SetProjection(dsBT.GetProjection())
            lstBand = lstDS.GetRasterBand(1)
            self.progress.emit(40)
            
            #Convert the variables to float
            nearSurfTemp = float(nearSurfTemp)
            atmTrans     = float(atmTrans)
            
            #Calculate the effective mean atmospheric temperature
            if (atmProfile == 'USA 1976'):
                T = 25.9396 + (0.88045 * nearSurfTemp)
            elif (atmProfile == 'Tropical'):
                T = 17.9769 + (0.91715 * nearSurfTemp)
            elif (atmProfile == 'Mid-Latitude Summer'):
                T = 16.0110 + (0.92621 * nearSurfTemp)
            elif (atmProfile == 'Mid-Latitude Winter'):
                T = 19.2704 + (0.91118 * nearSurfTemp)
            # loop through rows of blocks
            blockSize = 64
            for i in range(0, rowsBT, blockSize):
                if i + blockSize < rowsBT:
                    numRows = blockSize
                else:
                    numRows = rowsBT - i
                
                # now loop through the blocks in the row
                for j in range(0, colsBT, blockSize):
                    if j + blockSize < colsBT:
                        numCols = blockSize
                    else:
                        numCols = colsBT - j
                        
                    # get the data
                    lseData = lseBand.ReadAsArray(j, i, numCols, numRows).astype('f')
                    btData  = btBand.ReadAsArray(j, i, numCols, numRows).astype('f')
                
                    # do the calculation     
                    A    = -67.355351
                    B    = 0.458606
                    C    = np.multiply(lseData, atmTrans)
                    D1   = 1 - float(atmTrans)
                    D2   = np.multiply(atmTrans, lseData)
                    D2   = np.subtract(atmTrans, D2)
                    D2   = np.add(D2, 1)
                    D    = np.multiply(D1, D2)
                    lst1 = np.subtract(1, C)
                    lst1 = np.subtract(lst1, D)
                    lst1 = np.multiply(A, lst1)
                    lst2 = np.subtract(1, C)
                    lst2 = np.subtract(lst2, D)
                    lst2 = np.multiply(B, lst2)
                    lst2 = np.add(lst2, C)
                    lst2 = np.add(lst2, D)
                    lst2 = np.multiply(lst2, btData)
                    DT   = np.multiply(D, T)
                    lst_upper = np.add(lst1, lst2)
                    lst_upper = np.subtract(lst_upper, DT)
                    cond_list   = [C > 0, C < 0]
                    choice_list = [np.divide(lst_upper, C), 0]
                    
                    #Convert the temperature according to the unit selected
                    if (unit == 'Kelvin'):
                        lst  = np.select(cond_list, choice_list)
                    elif (unit == 'Celsius'):
                        #Celsius = Kelvin - 273.15
                        lst  = np.select(cond_list, choice_list)
                        lst = np.subtract(lst, 273.15)
                    else:
                        #Fahrenheit = ((kelvin - 273.15) x 1.8) + 32
                        lst  = np.select(cond_list, choice_list)
                        lst = np.subtract(lst, 273.15)
                        lst = np.multiply(lst, 1.8)
                        lst = np.add(lst, 32)
                    # write the data
                    lstDS.GetRasterBand(1).WriteArray(lst, j, i)
                
            self.progress.emit(90)
            # set the histogram
            lstDS.GetRasterBand(1).SetNoDataValue(-99)
            histogram = lstDS.GetRasterBand(1).GetDefaultHistogram()
            lstDS.GetRasterBand(1).SetDefaultHistogram(histogram[0], histogram[1], histogram[3])
                
            lstDS    = None
            lseBand  = None
            btBand   = None
            #Add the output to QGIS
            ret = outputPath
            if (addToQGIS == 'Yes'):
                self.progress.emit(100)
                self.finished.emit(ret)
            else:
                ret = None
                self.progress.emit(100)
                self.finished.emit(ret)
                
        except RuntimeError, e:
            self.error.emit(e, traceback.format_exc())
    
    def planckEquation(self, sensorType, bandNo, bt, lse, outputPath, unit, rasterType, addToQGIS):
        try:
            #The code below opens the datasets
            dsBT  = gdal.Open(bt, gdal.GA_ReadOnly)
            dsLSE = gdal.Open(lse, gdal.GA_ReadOnly)
            self.progress.emit(20)
        except IOError, e:
            self.error.emit(e, traceback.format_exc())
        try:
            #Set the wavelengths of the emitted radiances according to the sensor selected
            if (sensorType == 'Landsat TIRS'):
                if (int(bandNo) == 10):
                    wl = 11.395
                elif (int(bandNo) == 11):
                    wl = 12.005
            elif (sensorType == 'Landsat ETM+'):
                wl = 11.45
            elif (sensorType == 'Landsat TM'):
                wl = 11.45
            elif (sensorType == 'ASTER'):
                if (int(bandNo) == 10):
                    wl = 8.291
                elif (int(bandNo) == 11):
                    wl = 8.634
                elif (int(bandNo) == 12):
                    wl = 9.075
                elif (int(bandNo) == 13):
                    wl = 10.657
                elif (int(bandNo) == 14):
                    wl = 11.318
            #Capture the LSE and the Brightness Temperature bands
            btBand = dsBT.GetRasterBand(1)
            lseBand = dsLSE.GetRasterBand(1)
                    
            # get numbers of rows and columns in the Red and NIR bands
            colsBT = dsBT.RasterXSize
            rowsBT = dsBT.RasterYSize
                
            colsLSE = dsLSE.RasterXSize
            rowsLSE = dsLSE.RasterYSize
                
            # create the output image
            driver = gdal.GetDriverByName(rasterType)
            lstDS = driver.Create(outputPath, colsBT, rowsBT, 1, gdal.GDT_Float32)
            lstDS.SetGeoTransform(dsBT.GetGeoTransform())
            lstDS.SetProjection(dsBT.GetProjection())
            lstBand = lstDS.GetRasterBand(1)
            self.progress.emit(40)
                    
            # loop through rows of blocks
            blockSize = 64
            for i in range(0, rowsBT, blockSize):
                if i + blockSize < rowsBT:
                    numRows = blockSize
                else:
                    numRows = rowsBT - i
                
                # now loop through the blocks in the row
                for j in range(0, colsBT, blockSize):
                    if j + blockSize < colsBT:
                        numCols = blockSize
                    else:
                        numCols = colsBT - j
                        
                    # get the data
                    lseData = lseBand.ReadAsArray(j, i, numCols, numRows).astype('f')
                    btData  = btBand.ReadAsArray(j, i, numCols, numRows).astype('f')
                
                    # do the calculation
                    cond_list   = [lseData > 0, lseData <= 0]
                    choice_list = [np.log(lseData), 0]
                    log_lse     = np.select(cond_list, choice_list)
                    lst_upper   = btData
                    lst_lower   = np.divide(btData, 14380)
                    lst_lower   = np.multiply(lst_lower, wl)
                    lst_lower   = np.multiply(lst_lower, log_lse)
                    lst_lower   = np.add(lst_lower, 1)
                    
                    #Convert the temperature according to the unit selected
                    if (unit == 'Kelvin'):
                        lst = np.divide(lst_upper, lst_lower)
                    elif (unit == 'Celsius'):
                        #Celsius = Kelvin - 273.15
                        lst = np.divide(lst_upper, lst_lower)
                        lst = np.subtract(lst, 273.15)
                    else:
                        #Fahrenheit = ((kelvin - 273.15) x 1.8) + 32
                        lst = np.divide(lst_upper, lst_lower)
                        lst = np.subtract(lst, 273.15)
                        lst = np.multiply(lst, 1.8)
                        lst = np.add(lst, 32)
                    # write the data
                    lstDS.GetRasterBand(1).WriteArray(lst, j, i)
                    
            self.progress.emit(90)
            # set the histogram
            lstDS.GetRasterBand(1).SetNoDataValue(-99)
            histogram = lstDS.GetRasterBand(1).GetDefaultHistogram()
            lstDS.GetRasterBand(1).SetDefaultHistogram(histogram[0], histogram[1], histogram[3])
                
            lstDS    = None
            lseBand  = None
            btBand   = None
            
            #Add the output to QGIS
            ret = outputPath
            if (addToQGIS == 'Yes'):
                self.progress.emit(100)
                self.finished.emit(ret)
            else:
                ret = None
                self.progress.emit(100)
                self.finished.emit(ret)
                
        except RuntimeError, e:
            self.error.emit(e, traceback.format_exc())
            
    def calcBrightnessTemp(self, sensorType, bandNo, radiance, outputPath, fileType, addToQGIS):
        try:
            #The code below opens the datasets
            dsRadianceBand = gdal.Open(radiance, gdal.GA_ReadOnly)
            self.progress.emit(20)
        except IOError, e:
            self.error.emit(e, traceback.format_exc())
        try:
            radianceBand = dsRadianceBand.GetRasterBand(1)
                
            # get numbers of rows and columns in the Red and NIR bands
            cols = dsRadianceBand.RasterXSize
            rows = dsRadianceBand.RasterYSize
            if (sensorType == 'Landsat TIRS'):
                if (int(bandNo) == 10):
                    K1 = 774.89
                    K2 = 1321.08
                elif (int(bandNo) ==11):
                    K1 = 480.89
                    K2 = 1201.14
            elif (sensorType == 'Landsat ETM+'):
                K1 = 660.09
                K2 = 1282.71
            elif (sensorType == 'Landsat TM'):
                K1 = 607.76
                K2 = 1260.56
            elif (sensorType == 'ASTER'):
                if (int(bandNo) == 10):
                    K1 = 3047.47
                    K2 = 1736.18
                elif (int(bandNo) == 11):
                    K1 = 2480.93
                    K2 = 1666.21
                elif (int(bandNo) == 12):
                    K1 = 1930.80
                    K2 = 1584.72
                elif (int(bandNo) == 13):
                    K1 = 865.65
                    K2 = 1349.82
                elif (int(bandNo) == 14):
                    K1 = 649.60
                    K2 = 1274.49
                
            # Create the output image
            driver = gdal.GetDriverByName(fileType)
            brightnessDS = driver.Create(outputPath, cols, rows, 1, gdal.GDT_Float32)
            brightnessDS.SetGeoTransform(dsRadianceBand.GetGeoTransform())
            brightnessDS.SetProjection(dsRadianceBand.GetProjection())
            brightnessBand = brightnessDS.GetRasterBand(1)
            self.progress.emit(40)
            #Read the block sizes of the thermal band being processed
            blockSizes = brightnessBand.GetBlockSize()
            xBlockSize = blockSizes[0]
            yBlockSize = blockSizes[1]
                    
            # loop through rows of blocks
            for i in range(0, rows, yBlockSize):
                if i + yBlockSize < rows:
                    numRows = yBlockSize
                else:
                    numRows = rows - i
                
                # now loop through the blocks in the row
                for j in range(0, cols, xBlockSize):
                    if j + xBlockSize < cols:
                        numCols = xBlockSize
                    else:
                        numCols = cols - j
                        
                    radianceBandData = radianceBand.ReadAsArray(j, i, numCols, numRows).astype('f')
                    # do the calculation
                    bt_upper = K2
                    bt_lower = np.divide(K1, radianceBandData)
                    bt_lower = np.add(bt_lower, 1)
                    bt_lower = np.log(bt_lower)
                    bt = np.divide(bt_upper, bt_lower)

                    # write the data
                    brightnessDS.GetRasterBand(1).WriteArray(bt,j,i)

            self.progress.emit(90)          
            # set the histogram
            brightnessDS.GetRasterBand(1).SetNoDataValue(-99)
            histogram = brightnessDS.GetRasterBand(1).GetDefaultHistogram()
            brightnessDS.GetRasterBand(1).SetDefaultHistogram(histogram[0], histogram[1], histogram[3])

            brightnessDS    = None
            dsRadianceBand  = None
            
            #Add the output to QGIS
            ret = outputPath
            if (addToQGIS == 'Yes'):
                self.progress.emit(100)
                self.finished.emit(ret)
            else:
                ret = None
                self.progress.emit(100)
                self.finished.emit(ret)
                
        except RuntimeError, e:
            self.error.emit(e, traceback.format_exc())
                
    def calcTMRadiance(self, thermalBand, outputPath, fileType, metadata, addToQGIS):
        try:
            #The code below opens the datasets
            dsThermalBand = gdal.Open(thermalBand, gdal.GA_ReadOnly)
            self.progress.emit(20)
        except IOError, e:
            self.error.emit(e, traceback.format_exc())
        try:
            #Capture the Red and the NIR bands
            thermalBand = dsThermalBand.GetRasterBand(1)
                
            # get number of rows and columns in the Red and NIR bands
            cols = dsThermalBand.RasterXSize
            rows = dsThermalBand.RasterYSize
            #Read the metadata from the metadata file
            metaVariables = self.readMetadataFile(metadata, 'Landsat 5', '')
            QCALMAX       = float(metaVariables['QCALMAX'])
            QCALMIN       = float(metaVariables['QCALMIN'])
            LMAX          = float(metaVariables['LMAX'])
            LMIN          = float(metaVariables['LMIN'])           
            # create the output image
            driver = gdal.GetDriverByName(fileType)
            radianceDS = driver.Create(outputPath, cols, rows, 1, gdal.GDT_Float32)
            radianceDS.SetGeoTransform(dsThermalBand.GetGeoTransform())
            radianceDS.SetProjection(dsThermalBand.GetProjection())
            radianceBand = radianceDS.GetRasterBand(1)
            self.progress.emit(40)
            
            #Read the block sizes of the thermal band being processed
            blockSizes = radianceBand.GetBlockSize()
            xBlockSize = blockSizes[0]
            yBlockSize = blockSizes[1]
                    
            # loop through rows of blocks
            for i in range(0, rows, yBlockSize):
                if i + yBlockSize < rows:
                    numRows = yBlockSize
                else:
                    numRows = rows - i
                
                # now loop through the blocks in the row
                for j in range(0, cols, xBlockSize):
                    if j + xBlockSize < cols:
                        numCols = xBlockSize
                    else:
                        numCols = cols - j
                    #If the band selected is TIRS band 11
                    thermalBandData = thermalBand.ReadAsArray(j, i, numCols, numRows).astype('f')
                    # do the calculation
                    m = ((LMAX - QCALMIN) / (QCALMAX - QCALMIN))
                    x = np.subtract(thermalBandData, QCALMIN)
                    radiance = np.multiply(m, x)
                    radiance = np.add(radiance, LMIN)
                    # write the data
                    radianceDS.GetRasterBand(1).WriteArray(radiance,j,i)
            
            self.progress.emit(90)
            # set the histogram
            radianceDS.GetRasterBand(1).SetNoDataValue(-99)
            histogram = radianceDS.GetRasterBand(1).GetDefaultHistogram()
            radianceDS.GetRasterBand(1).SetDefaultHistogram(histogram[0], histogram[1], histogram[3])

            radianceDS    = None
            dsThermalBand = None
            #Add the output to QGIS
            ret = outputPath
            if (addToQGIS == 'Yes'):
                self.progress.emit(100)
                self.finished.emit(ret)
            else:
                ret = None
                self.progress.emit(100)
                self.finished.emit(ret)
                
        except RuntimeError, e:
            self.error.emit(e, traceback.format_exc())
    
    def calcETMRadiance(self, thermalBand, gain, outputPath, fileType, metadata, addToQGIS):
        try:
            #The code below opens the datasets
            dsThermalBand = gdal.Open(thermalBand, gdal.GA_ReadOnly)
            self.progress.emit(20)
        except IOError, e:
            self.error.emit(e, traceback.format_exc())
        try:
            #Capture the Red and the NIR bands
            thermalBand = dsThermalBand.GetRasterBand(1)
                
            # get numbers of rows and columns in the Red and NIR bands
            cols = dsThermalBand.RasterXSize
            rows = dsThermalBand.RasterYSize
            #Read the metadata from the metadata file
            metaVariables = self.readMetadataFile(metadata, 'Landsat 7', gain)
            QCALMAX       = float(metaVariables['QCALMAX'])
            QCALMIN       = float(metaVariables['QCALMIN'])
            LMAX          = float(metaVariables['LMAX'])
            LMIN          = float(metaVariables['LMIN'])           
            # create the output image
            driver = gdal.GetDriverByName(fileType)
            radianceDS = driver.Create(outputPath, cols, rows, 1, gdal.GDT_Float32)
            radianceDS.SetGeoTransform(dsThermalBand.GetGeoTransform())
            radianceDS.SetProjection(dsThermalBand.GetProjection())
            radianceBand = radianceDS.GetRasterBand(1)
            self.progress.emit(40)
            
            #Read the block sizes of the thermal band being processed
            blockSizes = radianceBand.GetBlockSize()
            xBlockSize = blockSizes[0]
            yBlockSize = blockSizes[1]
                    
            # loop through rows of blocks
            for i in range(0, rows, yBlockSize):
                if i + yBlockSize < rows:
                    numRows = yBlockSize
                else:
                    numRows = rows - i
                
                # now loop through the blocks in the row
                for j in range(0, cols, xBlockSize):
                    if j + xBlockSize < cols:
                        numCols = xBlockSize
                    else:
                        numCols = cols - j
                    #If the band selected is TIRS band 11
                    thermalBandData = thermalBand.ReadAsArray(j, i, numCols, numRows).astype('f')
                    # do the calculation
                    m = ((LMAX - QCALMIN) / (QCALMAX - QCALMIN))
                    x = np.subtract(thermalBandData, QCALMIN)
                    radiance = np.multiply(m, x)
                    radiance = np.add(radiance, LMIN)
                    # write the data
                    radianceDS.GetRasterBand(1).WriteArray(radiance,j,i)
                    
            self.progress.emit(90)
            # set the histogram
            radianceDS.GetRasterBand(1).SetNoDataValue(-99)
            histogram = radianceDS.GetRasterBand(1).GetDefaultHistogram()
            radianceDS.GetRasterBand(1).SetDefaultHistogram(histogram[0], histogram[1], histogram[3])

            radianceDS    = None
            dsThermalBand = None

            #Add the output to QGIS
            ret = outputPath
            if (addToQGIS == 'Yes'):
                self.progress.emit(100)
                self.finished.emit(ret)
            else:
                ret = None
                self.progress.emit(100)
                self.finished.emit(ret)
        except RuntimeError, e:
            self.error.emit(e, traceback.format_exc())
    
    def calcTIRSRadiance(self, thermalBand, bandNo, calibFactor, outputPath, fileType, metadata, addToQGIS):
        try:
            #The code below opens the datasets
            dsThermalBand = gdal.Open(thermalBand, gdal.GA_ReadOnly)
            self.progress.emit(20)
        except IOError, e:
            self.error.emit(e, traceback.format_exc())
        try:
            #Capture the Red and the NIR bands
            thermalBand = dsThermalBand.GetRasterBand(1)
                
            # get numbers of rows and columns in the Red and NIR bands
            cols = dsThermalBand.RasterXSize
            rows = dsThermalBand.RasterYSize
            #Read the metadata from the metadata file
            metaVariables       = self.readMetadataFile(metadata, 'Landsat 8', '')
            RadMultFactorBand10 = float(metaVariables['RadMultFactorBand10'])
            RadAddBand10        = float(metaVariables['RadAddBand10'])
            RadMultFactorBand11 = float(metaVariables['RadMultFactorBand11'])
            RadAddBand11        = float(metaVariables['RadAddBand11'])           
            # create the output image
            driver = gdal.GetDriverByName(fileType)
            radianceDS = driver.Create(outputPath, cols, rows, 1, gdal.GDT_Float32)
            radianceDS.SetGeoTransform(dsThermalBand.GetGeoTransform())
            radianceDS.SetProjection(dsThermalBand.GetProjection())
            radianceBand = radianceDS.GetRasterBand(1)
            self.progress.emit(40)
            
            #Read the block sizes of the thermal band being processed
            blockSizes = radianceBand.GetBlockSize()
            xBlockSize = blockSizes[0]
            yBlockSize = blockSizes[1]
                    
            # loop through rows of blocks
            for i in range(0, rows, yBlockSize):
                if i + yBlockSize < rows:
                    numRows = yBlockSize
                else:
                    numRows = rows - i
                
                # now loop through the blocks in the row
                for j in range(0, cols, xBlockSize):
                    if j + xBlockSize < cols:
                        numCols = xBlockSize
                    else:
                        numCols = cols - j
                        
                    if (int(bandNo) == 10):
                        #If the band selected is TIRS band 11
                        thermalBandData = thermalBand.ReadAsArray(j, i, numCols, numRows).astype('f')
                        # do the calculation
                        radiance = np.multiply(thermalBandData, RadMultFactorBand10)
                        radiance = np.add(radiance, RadAddBand10)
                        radiance = np.subtract(radiance, float(calibFactor))
                        # write the data
                        radianceDS.GetRasterBand(1).WriteArray(radiance,j,i)
                    else:
                        #If the band selected is TIRS band 11
                        thermalBandData = thermalBand.ReadAsArray(j, i, numCols, numRows).astype('f')
                        # do the calculation
                        #mask = np.greater(thermalBandData, 0)
                        radiance = np.multiply(thermalBandData, RadMultFactorBand11)
                        radiance = np.add(radiance, RadAddBand11)
                        radiance = np.subtract(radiance, float(calibFactor))
                        # write the data
                        radianceDS.GetRasterBand(1).WriteArray(radiance,j,i)
                        #radianceDS.WriteArray(radiance, j, i)
                        
            self.progress.emit(90)
            # set the histogram
            radianceDS.GetRasterBand(1).SetNoDataValue(-99)
            histogram = radianceDS.GetRasterBand(1).GetDefaultHistogram()
            radianceDS.GetRasterBand(1).SetDefaultHistogram(histogram[0], histogram[1], histogram[3])

            radianceDS    = None
            dsThermalBand = None
            #Add the output to QGIS
            ret = outputPath
            if (addToQGIS == 'Yes'):
                self.progress.emit(100)
                self.finished.emit(ret)
            else:
                ret = None
                self.progress.emit(100)
                self.finished.emit(ret)
                
        except RuntimeError, e:
            self.error.emit(e, traceback.format_exc())  
    
    def readMetadataFile(self, metadataPath, sensorType, gain):
        try:
            metadata = open(metadataPath, 'r')
            output = {} #Dict
            for metadataLine in metadata.readlines():
                if ("=") in metadataLine:
                    line = metadataLine.split("=") 
                    output[line[0].strip()] = line[1].strip() 
            
            #Change the variables to be read from the metadata file according to the sensor selected
            if (sensorType == 'Landsat 8'):
                K1_Band10 = float(output['K1_CONSTANT_BAND_10'])
                K2_Band10 = float(output['K2_CONSTANT_BAND_10'])
                K1_Band11 = float(output['K1_CONSTANT_BAND_11'])
                K2_Band11 = float(output['K2_CONSTANT_BAND_11'])
                RadAddBand10  = float(output['RADIANCE_ADD_BAND_10'])
                RadAddBand11  = float(output['RADIANCE_ADD_BAND_11'])
                RadMultFactorBand10 = float(output['RADIANCE_MULT_BAND_10'])
                RadMultFactorBand11 = float(output['RADIANCE_MULT_BAND_11'])
                #Return all the required variables
                return {'K1_Band10':K1_Band10, 'K2_Band10':K2_Band10, 'K1_Band11':K1_Band11, 'K2_Band11':K2_Band11,\
                        'RadAddBand10':RadAddBand10, 'RadAddBand11':RadAddBand11, 'RadMultFactorBand10':RadMultFactorBand10,\
                        'RadMultFactorBand11':RadMultFactorBand11}
                
            elif (sensorType == 'Landsat 7'):
                if (gain == 'High'): #If the image was taken in a high gain
                    QCALMAX = float(output['QUANTIZE_CAL_MAX_BAND_6_VCID_2'])
                    QCALMIN = float(output['QUANTIZE_CAL_MIN_BAND_6_VCID_2'])
                    LMAX = float(output['RADIANCE_MAXIMUM_BAND_6_VCID_2'])
                    LMIN = float(output['RADIANCE_MINIMUM_BAND_6_VCID_2'])
                    #Return all the required variables
                    return {'QCALMAX':QCALMAX, 'QCALMIN':QCALMIN, 'LMAX':LMAX, 'LMIN':LMIN}
                
                elif (gain == 'Low'): #If the image was taken in a low gain
                    QCALMAX = float(output['QUANTIZE_CAL_MAX_BAND_6_VCID_1'])
                    QCALMIN = float(output['QUANTIZE_CAL_MIN_BAND_6_VCID_1'])
                    LMAX = float(output['RADIANCE_MAXIMUM_BAND_6_VCID_1'])
                    LMIN = float(output['RADIANCE_MINIMUM_BAND_6_VCID_1'])
                    #Return all the required variables
                    return {'QCALMAX':QCALMAX, 'QCALMIN':QCALMIN, 'LMAX':LMAX, 'LMIN':LMIN}
                
            elif (sensorType == 'Landsat 5'):
                    QCALMAX = float(output['QUANTIZE_CAL_MAX_BAND_6'])
                    QCALMIN = float(output['QUANTIZE_CAL_MIN_BAND_6'])
                    LMAX = float(output['RADIANCE_MAXIMUM_BAND_6'])
                    LMIN = float(output['RADIANCE_MINIMUM_BAND_6'])
                    #Return all the required variables
                    return {'QCALMAX':QCALMAX, 'QCALMIN':QCALMIN, 'LMAX':LMAX, 'LMIN':LMIN}
            
            #Close the metadata file 
            metadata.close
        except RuntimeError, e:
            self.error.emit(e, traceback.format_exc())

    def calcNDVI(self, redBandPath, NIRBandPath, outputPath, rasterType, addToQGIS):
        try:
            #The code below opens the datasets
            dsRedBand = gdal.Open(redBandPath, gdal.GA_ReadOnly)
            dsNIRBand = gdal.Open(NIRBandPath, gdal.GA_ReadOnly)
            self.progress.emit(20)
        except IOError, e:
            self.error.emit(e, traceback.format_exc())
        try:
            #Capture the Red and the NIR bands
            redBand = dsRedBand.GetRasterBand(1)
            NIRBand = dsNIRBand.GetRasterBand(1)

            # get numbers of rows and columns in the Red and NIR bands
            colsRed = dsRedBand.RasterXSize
            rowsRed = dsRedBand.RasterYSize

            # create the output image
            driver = gdal.GetDriverByName(rasterType)
            ndviDS = driver.Create(outputPath, colsRed, rowsRed, 1, gdal.GDT_Float32)
            ndviDS.SetGeoTransform(dsRedBand.GetGeoTransform())
            ndviDS.SetProjection(dsRedBand.GetProjection())
            ndviBand = ndviDS.GetRasterBand(1)
            self.progress.emit(40)
                
            # loop through rows of blocks
            blockSize = 64
            for i in range(0, rowsRed, blockSize):
                if i + blockSize < rowsRed:
                    numRows = blockSize
                else:
                    numRows = rowsRed - i

                # now loop through the blocks in the row
                for j in range(0, colsRed, blockSize):
                    if j + blockSize < colsRed:
                        numCols = blockSize
                    else:
                        numCols = colsRed - j
                    # get the data
                    redBandData = redBand.ReadAsArray(j, i, numCols, numRows).astype('f')
                    NIRBandData = NIRBand.ReadAsArray(j, i, numCols, numRows).astype('f')
                    # do the calculation
                    mask = np.greater(redBandData + NIRBandData, 0)
                    ndvi = np.choose(mask, (-99, (NIRBandData - redBandData) / (NIRBandData + redBandData)))
                    # write the data
                    ndviDS.GetRasterBand(1).WriteArray(ndvi, j, i)
            
            self.progress.emit(90)
            # set the histogram
            ndviDS.GetRasterBand(1).SetNoDataValue(-99)
            histogram = ndviDS.GetRasterBand(1).GetDefaultHistogram()
            ndviDS.GetRasterBand(1).SetDefaultHistogram(histogram[0], histogram[1], histogram[3])

            ndviDS   = None
            redBand  = None
            NIRBand  = None

            #Add the output to QGIS
            ret = outputPath
            if (addToQGIS == 'Yes'):
                self.progress.emit(100)
                self.finished.emit(ret)
            else:
                ret = None
                self.progress.emit(100)
                self.finished.emit(ret)
                    
        except RuntimeError, e:
            self.error.emit(e, traceback.format_exc())
            
    def kill(self):
        self.killed = True

    def run(self):
        if (self.geoProcessName == 'LSTNDVI'):
            #Capture the varibles needed for NDVI calculation
            self.RedBand      = self.args[0]
            self.NIRBand      = self.args[1]
            self.outputRaster = self.args[2]
            self.rasterType   = self.args[3]
            self.addToQGIS    = self.args[4]            
            self.calcNDVI(self.RedBand, self.NIRBand, self.outputRaster, self.rasterType, self.addToQGIS)
        elif (self.geoProcessName == 'ETMRadiance'):
            #Capture the variables required for the radiance of the ETM calculation
            self.thermalBand = self.args[0]
            self.gain        = self.args[1]
            self.outputPath  = self.args[2]
            self.fileType    = self.args[3]
            self.metadata    = self.args[4]
            self.addToQgis   = self.args[5]
            self.calcETMRadiance(self.thermalBand, self.gain, self.outputPath, self.fileType, self.metadata, self.addToQgis)
        elif (self.geoProcessName == 'TMRadiance'):
            #Capture the variables required for the radiance of the TM calculation
            self.thermalBand = self.args[0]
            self.outputPath  = self.args[1]
            self.fileType    = self.args[2]
            self.metadata    = self.args[3]
            self.addToQgis   = self.args[4]
            self.calcTMRadiance(self.thermalBand, self.outputPath, self.fileType, self.metadata, self.addToQgis)
        elif (self.geoProcessName == 'TIRSRadiance'):
            #Capture the variables required for the radiance of the TIRS calculation
            self.thermalBand   = self.args[0]
            self.bandNo        = self.args[1]
            self.calibFactor   = self.args[2]
            self.outputPath    = self.args[3]
            self.fileType      = self.args[4]
            self.metadata      = self.args[5]
            self.addToQGIS     = self.args[6]
            self.calcTIRSRadiance(self.thermalBand, self.bandNo, self.calibFactor, self.outputPath, self.fileType, self.metadata, self.addToQGIS)
        elif (self.geoProcessName == 'BT'):
            self.sensorType    = self.args[0]
            self.bandNo        = self.args[1]
            self.radiance      = self.args[2]
            self.outputPath    = self.args[3]
            self.fileType      = self.args[4]
            self.addToQGIS     = self.args[5]
            self.calcBrightnessTemp(self.sensorType, self.bandNo, self.radiance, self.outputPath, self.fileType, self.addToQGIS)
        elif (self.geoProcessName == 'Planck'):
            self.sensorType    = self.args[0]
            self.bandNo        = self.args[1]
            self.bt            = self.args[2]
            self.lse           = self.args[3]
            self.outputPath    = self.args[4]
            self.unit          = self.args[5]
            self.rasterType    = self.args[6]
            self.addToQGIS     = self.args[7]
            self.planckEquation(self.sensorType, self.bandNo, self.bt, self.lse, self.outputPath, self.unit,self.rasterType, self.addToQGIS)
        elif (self.geoProcessName == 'MWA'):
            self.atmTrans     = self.args[0]
            self.nearSurfTemp = self.args[1]
            self.atmProfile   = self.args[2]
            self.bt           = self.args[3]
            self.lse          = self.args[4]
            self.outputPath   = self.args[5]
            self.unit         = self.args[6]
            self.rasterType   = self.args[7]
            self.addToQGIS    = self.args[8]
            self.monoWindowAlgorithm(self.atmTrans, self.nearSurfTemp, self.atmProfile, self.bt, self.lse, self.outputPath, self.unit, self.rasterType, self.addToQGIS)
        elif (self.geoProcessName == 'Single'):
            self.sensorType      = self.args[0]
            self.atmWaterVapour  = self.args[1]
            self.radiance        = self.args[2]
            self.bt              = self.args[3]
            self.lse             = self.args[4]
            self.outputPath      = self.args[5]
            self.unit            = self.args[6]
            self.rasterType      = self.args[7]
            self.addToQGIS       = self.args[8]
            self.singleChannelAlgorithm(self.sensorType, self.atmWaterVapour, self.radiance, self.bt, self.lse, self.outputPath, self.unit, self.rasterType, self.addToQGIS)
        elif (self.geoProcessName == 'RTE'):
            self.sensorType           = self.args[0]
            self.bandNo               = self.args[1]
            self.upWellingRadiance    = self.args[2]
            self.downWellingRadiance  = self.args[3]
            self.toaRadiance          = self.args[4]
            self.atmTrans             = self.args[5]
            self.lse                  = self.args[6]
            self.outputPath           = self.args[7]
            self.unit                 = self.args[8]
            self.rasterFormat         = self.args[9]
            self.addToQGIS            = self.args[10]
            self.radiativeTransferEquation(self.sensorType, self.bandNo, self.upWellingRadiance, self.downWellingRadiance, \
                                           self.toaRadiance, self.atmTrans, self.lse, self.outputPath, self.unit, \
                                           self.rasterFormat, self.addToQGIS)
        elif (self.geoProcessName == 'ZhangLSE'):
            #Capture the variables required for LSE estimation
            self.ndviRaster = self.args[0]
            self.outputPath = self.args[1]
            self.rasterType = self.args[2]
            self.addToQGIS  = self.args[3]
            self.zhangLSEalgorithm(self.ndviRaster, self.outputPath, self.rasterType, self.addToQGIS)
        elif (self.geoProcessName == 'ndviThresholdLSE'):
            self.ndviRaster           = self.args[0]
            self.outputPath           = self.args[1]
            self.rasterType           = self.args[2]
            self.addToQGIS            = self.args[3]
            self.ndviThresholdLSEAlgorithm(self.ndviRaster, self.outputPath, self.rasterType, self.addToQGIS)
        elif (self.geoProcessName == 'ASTERNDVI'):
            self.VNIRBandPath         = self.args[0]
            self.outputPath           = self.args[1]
            self.rasterType           = self.args[2]
            self.addToQGIS            = self.args[3]
            self.calcAsterNDVI(self.VNIRBandPath, self.outputPath, self.rasterType, self.addToQGIS)
        elif (self.geoProcessName == 'ASTERSCA'):
            self.lse                  = self.args[0]
            self.radiance             = self.args[1]
            self.bt                   = self.args[2]
            self.atmWaterVapor        = self.args[3]
            self.bandNo               = self.args[4]
            self.modtran              = self.args[5]
            self.outputRaster         = self.args[6]
            self.unit                 = self.args[7]
            self.rasterType           = self.args[8]
            self.addToQGIS            = self.args[9]
            self.asterSingleChannelAlg(self.lse, self.radiance, self.bt, self.atmWaterVapor, self.bandNo, self.modtran, \
                                       self.outputRaster, self.unit, self.rasterType, self.addToQGIS)
        elif (self.geoProcessName == 'ASTERRAD'):
            self.thermalBand          = self.args[0]
            self.bandNumber           = self.args[1]
            self.outputPath           = self.args[2]
            self.rasterType           = self.args[3]
            self.addToQGIS            = self.args[4]
            self.calcAsterRadiance(self.thermalBand, self.bandNumber, self.outputPath, self.rasterType, self.addToQGIS)
        elif (self.geoProcessName == 'ASTERLSE'):
            self.bandNo               = self.args[0]
            self.ndvi                 = self.args[1]
            self.outputPath           = self.args[2]
            self.rasterType           = self.args[3]
            self.addToQGIS            = self.args[4]
            self.asterLSE(self.bandNo, self.ndvi, self.outputPath, self.rasterType, self.addToQGIS)
        elif (self.geoProcessName == 'SWA'):
            self.b13BriTemp           = self.args[0]
            self.b14BriTemp           = self.args[1]
            self.b13Lse               = self.args[2]
            self.b14Lse               = self.args[3]
            self.b13atmTrans          = self.args[4]
            self.b14atmTrans          = self.args[5]
            self.outputPath           = self.args[6]
            self.rasterType           = self.args[7]
            self.unit                 = self.args[8]
            self.addToQGIS            = self.args[9]
            self.asterSWAalgorithm(self.b13BriTemp, self.b14BriTemp, self.b13Lse, self.b14Lse, self.b13atmTrans, self.b14atmTrans, \
                                   self.outputPath, self.rasterType, self.unit, self.addToQGIS)

    finished = QtCore.pyqtSignal(object)
    error    = QtCore.pyqtSignal(Exception, basestring)
    progress = QtCore.pyqtSignal(int)
    

        
        

        
