# -*- coding: utf-8 -*-
"""
/***************************************************************************
 LandSurfaceTemperature
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

from PyQt4.QtCore import *
from PyQt4.QtGui import *
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from lst_tool_dialog import LandSurfaceTemperatureDialog
from qgis.core import QgsProject
from core.lst_funcs import *
import os.path
import qgis.core
from qgis.utils import iface
import qgis.gui
import traceback
from osgeo import gdal
from osgeo import ogr
from qgis.gui import QgsMessageBar

#The imports below are done to enable the code in different directories to work in PyQGis
import sys
sys.path.append('~/Scripts/python')
from core.lst_funcs import EstimateLST


class LandSurfaceTemperature:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'LandSurfaceTemperature_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = LandSurfaceTemperatureDialog()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Land Surface Temperature')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'LandSurfaceTemperature')
        self.toolbar.setObjectName(u'LandSurfaceTemperature')

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('LandSurfaceTemperature', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToRasterMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        """This deals with the Land Surface Temperature Menu"""
        icon_path = ':/plugins/LandSurfaceTemperature/icons/landsat_8.ico'
        self.add_action(
            icon_path,
            text=self.tr(u'Land Surface Temperature'),
            callback=self.run,
            parent=self.iface.mainWindow())   
        

        #The code below attaches the close functionality 
        self.dlg.NDVI_btnClose.clicked.connect(self.closePlugin)
        self.dlg.lseZhangClose.clicked.connect(self.closePlugin)
        self.dlg.rad_btnClose.clicked.connect(self.closePlugin)
        self.dlg.bt_btnClose.clicked.connect(self.closePlugin)
        self.dlg.plkClose.clicked.connect(self.closePlugin)
        self.dlg.ndviSensorType.currentIndexChanged.connect(self.uiChangeNDVISensorInput)
        
        #The code below is for the NDVI tab
        self.dlg.ndviBrwNIRBand.clicked.connect(self.uiNDVIBrwNIR)
        self.dlg.NDVI_btnCalc.clicked.connect(self.uiCalcNDVI)
        self.dlg.ndviBrwRedBand.clicked.connect(self.uiNDVIBrwRed)
        self.dlg.NDVI_btnOutputBrw.clicked.connect(self.uiNDVIBrwOut)
        self.dlg.ndviBrwVNIRBand.clicked.connect(self.uiNDVIBrwVNIR)
        self.uiNDVIOutputFile()
        self.uiChangeNDVISensorInput()
        
        #The code below initilizes the values of the widgets in the radiance tab according to the sensor selected by default
        self.dlg.radGain.setEnabled(False)
        self.dlg.lblGain.setEnabled(False)
        self.dlg.radOffset.setEnabled(False)
        self.dlg.radLabelOffset.setEnabled(False)

        #The code below deals with the modification of the interface of the radiance calculation tab
        self.dlg.radSensorType.currentIndexChanged.connect(self.uiChangeRadianceInput)
        self.dlg.radCalc.clicked.connect(self.calcRadiance)
        self.dlg.radBrwThermal.clicked.connect(self.uiRadThermalBrw)
        self.dlg.radBrwOutput.clicked.connect(self.uiRadOutputBrw)
        self.dlg.radBrwMeta.clicked.connect(self.uiRadMetadataBrw)
        self.uiRadOutputFile()
        self.uiChangeRadianceInput()
        
        #The code below deals with the modification of the interface of the brightness temperature calculation tab
        self.uiChangeBrightnessTempInput()
        self.dlg.btSensorType.currentIndexChanged.connect(self.uiChangeBrightnessTempInput)
        self.dlg.btRadRasterBrw.clicked.connect(self.uiBtBrwRadiance)
        self.dlg.btOutRasterBrw.clicked.connect(self.uiBtBrwBtOutput)
        self.dlg.btCalculate.clicked.connect(self.uiCalcBrightnessTemp)
        self.uiBtOutputFile()
        
        #The code below connects the Plank equation/Emissivity correction tab
        self.dlg.plankSensor.currentIndexChanged.connect(self.changePlankSensor)
        self.dlg.plkCalc.clicked.connect(self.uiCalcPlankEqn)
        self.dlg.plkBtBrw.clicked.connect(self.uiPlkBtBrw)
        self.dlg.plkLSEBrw.clicked.connect(self.uiPlkLSEBrw)
        self.dlg.plkOutBrw.clicked.connect(self.uiPlkOutBrw)
        self.changePlankSensor()
        self.uiLSEOutputFile()
        self.uiPlankOutputFile()
        
        #The code below connects the Mono-window algorithm tab
        self.dlg.monoCalc.clicked.connect(self.monoWindowAlgorithm)
        self.dlg.monoClose.clicked.connect(self.closePlugin)
        self.dlg.monoBrwBT.clicked.connect(self.uiBrwMonoBriTemp)
        self.dlg.monoBrwLSE.clicked.connect(self.uiBrwMonoLSE)
        self.dlg.monoBrwOutputRaster.clicked.connect(self.uiBrwMonoOutput)
        self.uiMonoWindowOutputFile()
        self.uiMonoOutputFile()
                
        #The code below connects the single channel algorithm tab
        self.dlg.singleCalc.clicked.connect(self.calcSingleChannelAlgorithm)
        self.dlg.singleBrwRad.clicked.connect(self.uiBrwSingleRad)
        self.dlg.singleBrwBri.clicked.connect(self.uiBrwSingleBriTemp)
        self.dlg.singleBrwLSE.clicked.connect(self.uiBrwSingleLse)
        self.dlg.singleBrwOutput.clicked.connect(self.uiBrwOutputRaster)
        self.dlg.singleClose.clicked.connect(self.closePlugin)
        self.uiSingleOutputFile()
        
        #The code below deals with the Radiative Transfer Equation Tab
        self.uiRTEOutputFile()
        self.changeRTESensor()
        self.dlg.rteSensor.currentIndexChanged.connect(self.changeRTESensor)
        self.dlg.rteCalc.clicked.connect(self.calcRTE)
        self.dlg.rteClose.clicked.connect(self.closePlugin)
        self.dlg.rteBrwTOA.clicked.connect(self.uiBrwRTEtoa)
        self.dlg.rteBrwLSE.clicked.connect(self.uiBrwRTElse)
        self.dlg.rteBrwOutput.clicked.connect(self.uiBrwRTEout)
        
        #The code below connects the Zhang's LSE algorithm tab with the methods
        self.dlg.lseCalcZhang.clicked.connect(self.zhangLSEalgorithm)
        self.dlg.lseZhangClose.clicked.connect(self.closePlugin)
        self.dlg.lseBrwNDVIZhang.clicked.connect(self.brwZhangNDVI)
        self.dlg.lseBrwOutputZhang.clicked.connect(self.brwZhangOutput)
        
        #The code below connects the interface of the NDVI Threshold LSE estimation algorithm with the methods
        self.dlg.ndviThresholdNDVIBrw.clicked.connect(self.uiNDVIThresholdLSEBrwNDVI)
        self.dlg.ndviThresholdLSEBrw.clicked.connect(self.uiNDVIThresholdLSEBrwSave)
        self.dlg.ndviThresholdLSECalc.clicked.connect(self.uiNDVIthresholdLSEcalc)
        self.dlg.ndviThresholdLSEClose.clicked.connect(self.closePlugin)
        self.uiNDVIthresholdOutputFile()
        
        #The code below connects the interface of ASTER's single channel algorithm
        self.dlg.singleAsterBrwLSE.clicked.connect(self.uiSingleAsterBrwLSE)
        self.dlg.singleAsterBrwRadiance.clicked.connect(self.uiSingleAsterBrwRadiance)
        self.dlg.singleAsterBrwBriTemp.clicked.connect(self.uiSingleAsterBrwBriTemp)
        self.dlg.singleAsterBrwOutput.clicked.connect(self.uiSingleAsterBrwOutput)
        self.dlg.singleAsterCalc.clicked.connect(self.uiAsterSingleChannelCalc)
        self.dlg.singleAsterClose.clicked.connect(self.closePlugin)
        self.asterSCAOutputFile()
        
        #The code below connects the ASTER land surface emissivity calculation tab to the functions
        self.dlg.asterLSEBrwNDVI.clicked.connect(self.uiAsterLseNdviBrw)
        self.dlg.asterLSEBrwOutput.clicked.connect(self.uiAsterLseOutputBrw)
        self.dlg.asterLSEClose.clicked.connect(self.closePlugin)
        self.dlg.asterLSECalc.clicked.connect(self.uiAsterLSEcalc)
        self.asterLSEOutputFile()
        
        #The code below connects the split window algorithm tab to the functions
        self.dlg.asterSWAcalc.clicked.connect(self.uiAsterSWAcalc)
        self.dlg.asterSWAClose.clicked.connect(self.closePlugin)
        self.dlg.swaB13btBrw.clicked.connect(self.uiAsterB13Brw)
        self.dlg.swaB14btBrw.clicked.connect(self.uiAsterB14Brw)
        self.dlg.swaB13lseBrw.clicked.connect(self.uiAsterLse13Brw)
        self.dlg.swaB14lseBrw.clicked.connect(self.uiAsterLse14Brw)
        self.dlg.swaLstBrw.clicked.connect(self.uiAsterOutputBrw)
        self.asterSWAOutputFile()
    
    def uiAsterB13Brw(self):
        self.bt = QFileDialog.getOpenFileName(self.dlg, 'Open the band 13 brightness temperature raster', '.')
        self.dlg.lineEditSWAbt13.setText(self.bt)
    
    def uiAsterB14Brw(self):
        self.bt = QFileDialog.getOpenFileName(self.dlg, 'Open the band 14 brightness temperature raster', '.')
        self.dlg.lineEditSWAbt14.setText(self.bt)
    
    def uiAsterLse13Brw(self):
        self.lse = QFileDialog.getOpenFileName(self.dlg, 'Open the band 13 land surface emissivity raster', '.')
        self.dlg.lineEditSWAlse13.setText(self.lse)
    
    def uiAsterLse14Brw(self):
        self.lse = QFileDialog.getOpenFileName(self.dlg, 'Open the band 14 surface emissivity raster', '.')
        self.dlg.lineEditSWAlse14.setText(self.lse)
        
    def uiAsterOutputBrw(self):
        self.lst = QFileDialog.getSaveFileName(self.dlg, 'Output save location', '.')
        self.dlg.lineEditSWAOut.setText(self.lst)
        
    def uiAsterSWAcalc(self):
        self.btBand13       = self.dlg.lineEditSWAbt13.text()
        self.btBand14       = self.dlg.lineEditSWAbt14.text()
        self.lseBand13      = self.dlg.lineEditSWAlse13.text()
        self.lseBand14      = self.dlg.lineEditSWAlse14.text()
        self.atmTransBand13 = float(self.dlg.b13atmTrans.text())
        self.atmTransBand14 = float(self.dlg.b14atmTrans.text())
        self.rasterType     = str(self.dlg.swaRasterType.currentText()) 
        self.outputPath     = self.dlg.lineEditSWAOut.text()
        self.unit           = str(self.dlg.swaUnit.currentText())
        if (self.dlg.swaAddToProj.isChecked()):
            self.addToQGIS = 'Yes'
        else:
            self.addToQGIS = 'No'
            
        if (self.btBand13 == ''):
            self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                                    "Band 13 brightness temperature is required",
                                    QgsMessageBar.WARNING, 3)
        elif (self.btBand14 == ''):
            self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                                    "Band 14 brightness temperature is required",
                                    QgsMessageBar.WARNING, 3)
        elif (self.lseBand13 == ''):
            self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                                    "Band 13 land surface emissivity is required",
                                    QgsMessageBar.WARNING, 3)
        elif (self.lseBand14 == ''):
            self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                                    "Band 14 land surface emissivity is required",
                                    QgsMessageBar.WARNING, 3)
        elif (self.outputPath == ''):
            self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                                    "The output save location is required",
                                    QgsMessageBar.WARNING, 3)
        else:
            self.argList = [self.btBand13, self.btBand14, self.lseBand13, self.lseBand14, self.atmTransBand13, \
                            self.atmTransBand14, self.outputPath, self.rasterType, self.unit, self.addToQGIS]
            self.startWorker('SWA', self.argList, 'Calculating land surface temperature')
        self.closePlugin() 
    
    def uiAsterLSEcalc(self):
        self.ndvi         = self.dlg.asterLSEndvi.text()
        self.bandNo       = self.dlg.asterLSEBandNo.currentText()
        self.outputRaster = self.dlg.asterLSEoutput.text()
        self.rasterType   = str(self.dlg.asterLSErasterType.currentText())
        
        if self.bandNo == '':
            self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                                    "The band number is required",
                                    QgsMessageBar.WARNING, 3)
        elif self.ndvi == '':
            self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                                    "NDVI is required",
                                    QgsMessageBar.WARNING, 3)
        elif self.outputRaster == '':
            self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                                    "The output save location is required",
                                    QgsMessageBar.WARNING, 3)
        else:
            #Check if the add to project checkbox has been selected
            if (self.dlg.asterLSEAddToProject.isChecked()):
                self.addToQGIS = 'Yes'
            else:
                self.addToQGIS = 'No'
            self.argList = [self.bandNo, self.ndvi, self.outputRaster, self.rasterType, self.addToQGIS]
            self.startWorker('ASTERLSE', self.argList, 'Calculating land surface emissivity')
        self.closePlugin() 
    
    def uiAsterLseNdviBrw(self):
        self.ndvi = QFileDialog.getOpenFileName(self.dlg, 'Select the NDVI raster file', '.')
        self.dlg.asterLSEndvi.setText(self.ndvi)
    
    def uiAsterLseOutputBrw(self, ):
        self.lse = QFileDialog.getSaveFileName(self.dlg, 'Output save location', '.')
        self.dlg.asterLSEoutput.setText(self.lse)
        
    def uiSingleAsterBrwLSE(self):
        self.lse = QFileDialog.getOpenFileName(self.dlg, 'Select the land surface emissivity raster file', '.')
        self.dlg.singleAsterLSE.setText(self.lse)

    def uiSingleAsterBrwRadiance(self):
        self.radiance = QFileDialog.getOpenFileName(self.dlg, 'Open the radiance raster', '.')
        self.dlg.singleAsterRadiance.setText(self.radiance)
    
    def uiSingleAsterBrwBriTemp(self):
        self.bt = QFileDialog.getOpenFileName(self.dlg, 'Open the brightness temperature raster', '.')
        self.dlg.singleAsterBriTemp.setText(self.bt)
        
    def uiSingleAsterBrwOutput(self):
        self.out = QFileDialog.getSaveFileName(self.dlg, 'Output save location', '.')
        self.dlg.singleAsterOutputLocation.setText(self.out)
        
    def uiAsterSingleChannelCalc(self):
        self.lse           = self.dlg.singleAsterLSE.text()
        self.radiance      = self.dlg.singleAsterRadiance.text()
        self.bt            = self.dlg.singleAsterBriTemp.text()
        self.atmWaterVapor = float(self.dlg.singleAsterAtmWaterVapor.text())
        self.bandNo        = self.dlg.singleAsterBandNo.currentText()
        self.outputRaster  = self.dlg.singleAsterOutputLocation.text()
        self.unit          = str(self.dlg.singleAsterUnit.currentText())
        self.rasterType    = str(self.dlg.singleAsterRasterType.currentText())
        
        #Check if the add to project checkbox has been selected
        if (self.dlg.singleAsterAddToProject.isChecked()):
            self.addToQGIS = 'Yes'
        else:
            self.addToQGIS = 'No'
        
        #Check which MODTRAN4 database has been selected
        if (self.dlg.singleAsterStd66.isChecked()):
            self.modtran = 'STD66'
        elif (self.dlg.singleAsterTigr61.isChecked()):
            self.modtran = 'TIGR61'
        
        #Validate the inputs inserted by the user
        if self.lse == '':
            self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                                                "Land surface emissivity is required",
                                                QgsMessageBar.WARNING, 3)
        elif self.radiance == '':
            self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                                                "Radiance is required",
                                                QgsMessageBar.WARNING, 3)
        elif self.bt == '':
            self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                                                "Brightness temperature is required",
                                                QgsMessageBar.WARNING, 3)
        elif self.atmWaterVapor == 0.0:
            self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                                                "Atmospheric water vapor is required",
                                                QgsMessageBar.WARNING, 3)
        elif self.bandNo == '':
            self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                                                "The band number is required",
                                                QgsMessageBar.WARNING, 3)
        elif self.outputRaster == '':
            self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                                                "The output raster is required",
                                                QgsMessageBar.WARNING, 3)
        elif (self.lse != '' or self.radiance != '' or self.atmWaterVapor != '' or self.bandNo != '' or self.outputRaster != ''):
            self.rasterType = 'GTiff'
            self.argList = [self.lse, self.radiance, self.bt, self.atmWaterVapor, self.bandNo, self.modtran, self.outputRaster, self.unit, self.rasterType, self.addToQGIS]
            self.startWorker('ASTERSCA', self.argList, 'Calculating land surface temperature')
        self.closePlugin()
    
    def uiNDVIthresholdLSEcalc(self):
        self.ndviRaster = self.dlg.lseNDVIthresholdNDVI.text()
        self.outputPath = self.dlg.lseNDVIthresholdOutputRaster.text()
        self.rasterType = str(self.dlg.lseNDVIthresholdRasterFormat.currentText())
        #Loading the raster to the QGIS project
        if (self.dlg.lseNDVIthresholdAddToProject.isChecked()):
            self.addToQGIS = 'Yes'
        else:
            self.addToQGIS = 'No'
        #Validate the inputs
        if self.ndviRaster == '':
            self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                                                "NDVI is required",
                                                QgsMessageBar.WARNING, 3)
        elif self.outputPath == '':
            self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                                                "Specify output to be saved",
                                                QgsMessageBar.WARNING, 3)
        elif self.outputPath != '' and self.ndviRaster !='':
            self.argList = [self.ndviRaster, self.outputPath, self.rasterType, self.addToQGIS]
            self.startWorker('ndviThresholdLSE', self.argList, 'Estimating LSE from NDVI')
        self.closePlugin()
                    
    def zhangLSEalgorithm(self):
        self.ndviRaster   = self.dlg.zhangNDVILineEdit.text()
        self.outputRaster = self.dlg.zhangOutputLineEdit.text()
        self.rasterType   = str(self.dlg.zhangRasterType.currentText())
        if self.dlg.zhangLSEAddToProject.isChecked():
            self.addToQGIS = 'Yes'
        else:
            self.addToQGIS = 'No'
        #Validate the inputs
        if self.ndviRaster == '':
            self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                                                "NDVI is required",
                                                QgsMessageBar.WARNING, 3)
        elif self.outputRaster == '':
            self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                                                "Specify output to be saved",
                                                QgsMessageBar.WARNING, 3)
        elif self.outputRaster != '' and self.ndviRaster !='':
            self.argList = [self.ndviRaster, self.outputRaster, self.rasterType, self.addToQGIS]
            self.startWorker('ZhangLSE', self.argList, 'Estimating the LSE from NDVI')
        self.closePlugin()
        
    def brwZhangNDVI(self):
        self.ndvi = QFileDialog.getOpenFileName(self.dlg, 'Browse for NDVI', '.')
        self.dlg.zhangNDVILineEdit.setText(self.ndvi)
    
    def brwZhangOutput(self):
        self.output = QFileDialog.getSaveFileName(self.dlg, 'Save LSE', '.')
        self.dlg.zhangOutputLineEdit.setText(self.output)
        
    def clearZhangFields(self):
        self.dlg.lseNDVIthresholdNDVI.setText('')
        self.dlg.lseNDVIthresholdOutputRaster.setText('') 
        
    def calcRTE(self):
        self.rteSensor   = self.dlg.rteSensor.currentText()
        self.rteBandNo   = self.dlg.rteBandNo.currentText()
        self.rteUpRad    = self.dlg.rteUpRad.text()
        self.rteDownRad  = self.dlg.rteDownRad.text()
        self.rteAtmTrans = self.dlg.rteAtmTrans.text()
        self.rteTOA      = self.dlg.rteTOA.text()
        self.rteLSE      = self.dlg.rteLSE.text()
        self.rteOutput   = self.dlg.rteOutput.text()
        self.rteFormat   = self.dlg.rteFormat.currentText()
        self.rteUnit     = self.dlg.rteUnit.currentText()
        if (self.dlg.rteAddToProject.isChecked()):
            self.addToQGIS = 'Yes'
        #Validate the inputs
        if self.rteSensor == '':
            self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                                                    "Sensor type must be selected",
                                                    QgsMessageBar.WARNING, 3)
        elif self.rteBandNo == '':
            self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                                                "Band number must be selected",
                                                QgsMessageBar.WARNING, 3)
        elif self.rteUpRad == '0.0':
            self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                                                "Upwelling radiance is required",
                                                QgsMessageBar.WARNING, 3)
        elif self.rteDownRad == '0.0':
            self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                                                "Downwelling radiance is required",
                                                QgsMessageBar.WARNING, 3)
        elif self.rteAtmTrans == '0.0':
            self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                                                "Atmospheric transmission is required",
                                                QgsMessageBar.WARNING, 3)
        elif self.rteTOA == '':
            self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                                                "The radiance is required",
                                                QgsMessageBar.WARNING, 3)
        elif self.rteLSE == '':
            self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                                                "The land surface emissivity is required",
                                                QgsMessageBar.WARNING, 3)
        elif self.rteOutput == '':
            self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                                                "Specify output to be saved",
                                                QgsMessageBar.WARNING, 3)
        else:
            self.argList = [self.rteSensor, self.rteBandNo, self.rteUpRad , self.rteDownRad, self.rteTOA, \
                            self.rteAtmTrans, self.rteLSE, self.rteOutput, self.rteUnit, self.rteFormat, \
                            self.addToQGIS]
            self.startWorker('RTE', self.argList, 'Processing the Radiative Transfer Equation')
        self.closePlugin()
    
    def clearRTEFields(self):
        self.dlg.rteSensor.setCurrentIndex(1)
        self.dlg.rteUpRad.setText('')
        self.dlg.rteDownRad.setText('')
        self.dlg.rteAtmTrans.setText('')
        self.dlg.rteTOA.setText('')
        self.dlg.rteLSE.setText('')
        self.dlg.rteOutput.setText('')
        self.dlg.rteFormat.setCurrentIndex(6)
        self.dlg.rteAddToProject.setChecked(False)
        
    def uiBrwRTEtoa(self):
        self.toa = QFileDialog.getOpenFileName(self.dlg, 'Open the radiance raster file', '.')
        self.dlg.rteTOA.setText(self.toa)

    def uiBrwRTElse(self):
        self.lse = QFileDialog.getOpenFileName(self.dlg, 'Open the land surface emissivity raster file', '.')
        self.dlg.rteLSE.setText(self.lse)
        
    def uiBrwRTEout(self):
        self.out = QFileDialog.getSaveFileName(self.dlg, 'Output save location', '.')
        self.dlg.rteOutput.setText(self.out)

    def getGdalRasterFormats(self):
        gdal.AllRegister()
        gdalRasters = ['GTiff']
        '''
        for i in range(0, gdal.GetDriverCount()):
            metadata = gdal.GetDriverCount()
            drv = gdal.GetDriver(i)
            drv_meta = drv.GetMetadata()
            if ('DMD_EXTENSION' in drv_meta):
                gdalRasters.append(drv.ShortName)
        '''
        return gdalRasters
    
    def clearSingleChannedlAlgFields(self):
        self.dlg.singleWaterVapour.setText('0.0')
        self.dlg.singleRad.setText('')
        self.dlg.singleBriTemp.setText('')
        self.dlg.singleLSE.setText('')
        self.dlg.singleOutput.setText('')
        self.dlg.singleAddToProject.setChecked(False)
        
    def uiBrwSingleRad(self):
        self.rad = QFileDialog.getOpenFileName(self.dlg, 'Open the radiance raster file', '.')
        self.dlg.singleRad.setText(self.rad)
    
    def uiBrwSingleBriTemp(self):
        self.bt = QFileDialog.getOpenFileName(self.dlg, 'Open the brightness temperature raster file', '.')
        self.dlg.singleBriTemp.setText(self.bt)
    
    def uiBrwSingleLse(self):
        self.lse = QFileDialog.getOpenFileName(self.dlg, 'Open the land surface emissivity raster file', '.')
        self.dlg.singleLSE.setText(self.lse)
    
    def uiBrwOutputRaster(self):
        self.outputRaster = QFileDialog.getSaveFileName(self.dlg, 'Select the output file location', '.')
        self.dlg.singleOutput.setText(self.outputRaster)
    
    def calcSingleChannelAlgorithm(self):
        self.atmWaterVapour = self.dlg.singleWaterVapour.text()
        self.radiance       = self.dlg.singleRad.text()
        self.briTemp        = self.dlg.singleBriTemp.text()
        self.lse            = self.dlg.singleLSE.text()
        self.outputRaster   = self.dlg.singleOutput.text()
        self.rasterType     = str(self.dlg.singleFormat.currentText())
        self.unit           = self.dlg.singleUnit.currentText()
        self.sensorType     = str(self.dlg.singleSensorType.currentText())
        if (self.dlg.singleAddToProject.isChecked()):
            self.addToQGIS = 'Yes'
        else:
            self.addToQGIS = 'No'
        #Validate the inputs
        if self.atmWaterVapour == '0.0':
            self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                                                "The atmospheric water vapor is required",
                                                QgsMessageBar.WARNING, 3)
        elif self.radiance == '':
            self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                                                "The radiance is required",
                                                QgsMessageBar.WARNING, 3)
        elif self.briTemp == '':
            self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                                                "The brightness temperature is required",
                                                QgsMessageBar.WARNING, 3)
        elif self.lse == '':
            self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                                                "The land surface emissivity is required",
                                                QgsMessageBar.WARNING, 3)
        elif self.outputRaster == '':
            self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                                                "Specify output to be saved",
                                                QgsMessageBar.WARNING, 3)
        elif self.atmWaterVapour != '' and self.radiance != '' and self.briTemp !='' and self.lse !='' and self.outputRaster!='': 
            self.argList = [self.sensorType, self.atmWaterVapour, self.radiance,  self.briTemp, self.lse, self.outputRaster, self.unit, self.rasterType, self.addToQGIS]
            self.startWorker('Single', self.argList, 'Processing the Single Channel Algorithm')
        self.closePlugin()
    
    def uiBrwMonoBriTemp(self):
        self.bt = QFileDialog.getOpenFileName(self.dlg, 'Open the brightness temperature raster file', '.')
        self.dlg.monoBriTemp.setText(self.bt)
    
    def uiBrwMonoLSE(self):
        self.lse = QFileDialog.getOpenFileName(self.dlg, 'Open the land surface emissivity raster file', '.')
        self.dlg.monoLSE.setText(self.lse)
    
    def uiBrwMonoOutput(self):
        self.outputRaster = QFileDialog.getSaveFileName(self.dlg, 'Select the output file location', '.')
        self.dlg.monoOutputRaster.setText(self.outputRaster)

    def clearMonoWindowFields(self):
        self.dlg.monoAtmTran.setText('0.0')
        self.dlg.monoEffMeanAtmTemp.setText('0.0')
        self.dlg.monoAtmProfile.currentText()
        self.dlg.monoBriTemp.setText('')
        self.dlg.monoLSE.setText('')
        self.dlg.monoOutputRaster.setText('')
        self.dlg.monoAddToProj.setChecked(False)
    
    def monoWindowAlgorithm(self):
        self.atmTrans       = self.dlg.monoAtmTran.text()
        self.nearSurfTemp   = self.dlg.monoEffMeanAtmTemp.text()
        self.atmProfile     = str(self.dlg.monoAtmProfile.currentText())
        self.briTemp        = self.dlg.monoBriTemp.text()
        self.lse            = self.dlg.monoLSE.text()
        self.outputPath     = self.dlg.monoOutputRaster.text()
        self.rasterType     = str(self.dlg.monoFormat.currentText())
        self.unit           = self.dlg.monoUnit.currentText()
        if (self.dlg.monoAddToProj.isChecked()):
            self.addToQGIS = 'Yes'
        else:
            self.addToQGIS = 'No'
        #Validate the inputs
        if self.atmTrans == '0.0':
            self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                                                "Atmosperic transmittance is required",
                                                QgsMessageBar.WARNING, 3)
        elif self.nearSurfTemp == '0.0':
            self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                                                "The near surface temperature is required",
                                                QgsMessageBar.WARNING, 3)
        elif self.atmProfile == '':
            self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                                                "The atmospheric profile is required",
                                                QgsMessageBar.WARNING, 3)
        elif self.briTemp == '':
            self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                                                "The brightness temperature is required",
                                                QgsMessageBar.WARNING, 3)
        elif self.lse == '':
            self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                                                "The land surface emissivity is required",
                                                QgsMessageBar.WARNING, 3)
        elif self.outputPath == '':
            self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                                                "Specify output to be saved",
                                                QgsMessageBar.WARNING, 3)
        elif self.atmTrans != '' and self.nearSurfTemp != '' and self.atmProfile != '' and self.briTemp != '' and self.lse != '' and self.outputPath !='':
            self.argList = [self.atmTrans, self.nearSurfTemp, self.atmProfile, self.briTemp, self.lse, self.outputPath, self.unit, self.rasterType, self.addToQGIS]
            self.startWorker('MWA', self.argList, 'Processing the Mono-Window Algorithm')
        self.closePlugin()
    
    def changeRTESensor(self):
        #Capture the variables from the interface
        self.rteSensorType   = self.dlg.rteSensor.currentText()
        self.rteBandNo       = self.dlg.rteBandNo.currentText()

        #Change the interface according to the selected sensor
        if (self.rteSensorType == 'Landsat TIRS'):
            self.tirsBands = [10,11]
            #Add the Landsat TIRS bands to the combo box
            self.dlg.rteBandNo.clear()
            for self.i in range(len((self.tirsBands))):
                self.dlg.rteBandNo.addItem(str(self.tirsBands[self.i]))
        
        elif (self.rteSensorType == 'Landsat ETM+') or (self.rteSensorType == 'Landsat TM'):
            self.tmBands = [6]
            #Add the Landsat TM/ETM+ bands to the combo box
            self.dlg.rteBandNo.clear()
            for self.i in range(len((self.tmBands))):
                self.dlg.rteBandNo.addItem(str(self.tmBands[self.i]))
    
    def changePlankSensor(self):
        #Capture the variables from the interface
        self.plkSensorType   = self.dlg.plankSensor.currentText()
        self.plkBandNo       = self.dlg.plkBandNo.currentText()

        #Change the interface according to the selected sensor
        if (self.plkSensorType == 'Landsat TIRS'):
            self.tirsBands = [10,11]
            #Add the Landsat TIRS bands to the combo box
            self.dlg.plkBandNo.clear()
            for self.i in range(len((self.tirsBands))):
                self.dlg.plkBandNo.addItem(str(self.tirsBands[self.i]))
        
        elif (self.plkSensorType == 'Landsat ETM+') or (self.plkSensorType == 'Landsat TM'):
            self.tmBands = [6]
            #Add the Landsat TIRS bands to the combo box
            self.dlg.plkBandNo.clear()
            for self.i in range(len((self.tmBands))):
                self.dlg.plkBandNo.addItem(str(self.tmBands[self.i]))
    
        elif (self.plkSensorType == 'ASTER'):
            self.tirsBands = [10,11,12,13,14]
            #Add the Landsat TIRS bands to the combo box
            self.dlg.plkBandNo.clear()
            for self.i in range(len((self.tirsBands))):
                self.dlg.plkBandNo.addItem(str(self.tirsBands[self.i]))
                
    def uiPlkBtBrw(self):
        self.bt = QFileDialog.getOpenFileName(self.dlg, 'Open the brightness temperature raster file', '.')
        self.dlg.plankBt.setText(self.bt)
    
    def uiPlkLSEBrw(self):
        self.lse = QFileDialog.getOpenFileName(self.dlg, 'Open the Land Surface Emissivity raster file', '.')
        self.dlg.plankLSE.setText(self.lse)
    
    def uiPlkOutBrw(self):
        self.lst = QFileDialog.getSaveFileName(self.dlg, 'Select an output file location', '.')
        self.dlg.plankOutput.setText(self.lst)
    
    def uiCalcPlankEqn(self):
        self.sensorType = str(self.dlg.plankSensor.currentText())
        self.bandNo = int(self.dlg.plkBandNo.currentText())
        self.bt = str(self.dlg.plankBt.text())
        self.lse = str(self.dlg.plankLSE.text())
        self.outputPath = str(self.dlg.plankOutput.text())
        self.rasterType = str(self.dlg.plankFormat.currentText())
        self.unit = self.dlg.plankUnit.currentText()
        self.addToQGIS = ''
        if (self.dlg.plankAdd.isChecked()):
            self.addToQGIS = 'Yes'
        else:
            self.addToQGIS = 'No'
        #Validate the inputs
        if self.bandNo =='':
            self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                                                "The band number is required",
                                                QgsMessageBar.WARNING, 3)
        elif self.bt == '':
            self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                                                "The brightness temperature is required",
                                                QgsMessageBar.WARNING, 3)
        elif self.lse == '':
            self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                                                "The land surface emissivity is required",
                                                QgsMessageBar.WARNING, 3)
        elif self.outputPath == '':
            self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                                                "Select the output save location",
                                                QgsMessageBar.WARNING, 3)
        elif self.bandNo !='' and self.bt != '' and self.lse != '' and self.outputPath != '':
            self.argList = [self.sensorType, self.bandNo, self.bt, self.lse, self.outputPath, self.unit, self.rasterType, self.addToQGIS]
            self.startWorker('Planck', self.argList, 'Doing Land Surface Temperature Emissivity Correction')
        self.closePlugin()
        
    def clearPlankFields(self):
        self.changePlankSensor()
        self.dlg.plankOutput.setText('')
        self.dlg.plankLSE.setText('')
        self.dlg.plankBt.setText('')
        self.dlg.plankAdd.setChecked(False)
    
    def uiCalcBrightnessTemp(self):
        self.sensorType      = self.dlg.btSensorType.currentText()
        self.bandNo          = self.dlg.btBandNo.currentText()
        self.radianceRaster  = self.dlg.btRadianceRaster.text()
        self.outputRaster    = self.dlg.btOutputRaster.text()
        self.fileType        = str(self.dlg.btFormat.currentText())
        
        if (self.dlg.btAddToProject.isChecked()):
            self.addToQGIS = 'Yes'
        else:
            self.addToQGIS = 'No'
        #Validate the inputs
        if self.radianceRaster =='':
            self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                                                "The radiance is required",
                                                QgsMessageBar.WARNING, 3)
        elif self.outputRaster == '':
            self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                                                "Specify output to be saved",
                                                QgsMessageBar.WARNING, 3)
        elif self.radianceRaster != '' and self.outputRaster != '':
            self.argList = [self.sensorType, self.bandNo, self.radianceRaster, self.outputRaster, self.fileType, self.addToQGIS]
            self.startWorker('BT', self.argList, 'Calculating TOA Brightness Temperature')
        self.closePlugin()

    def uiBtBrwBtOutput(self):
        self.outputRaster = QFileDialog.getSaveFileName(self.dlg, 'Output file file location', '.')
        self.dlg.btOutputRaster.setText(self.outputRaster)
        
    def uiBtBrwRadiance(self):
        self.radiance = QFileDialog.getOpenFileName(self.dlg, 'Select a radiance raster file', '.')
        self.dlg.btRadianceRaster.setText(self.radiance)
        
    def uiChangeNDVISensorInput(self):
        #Capture the variables from the interface
        self.sensorType = self.dlg.ndviSensorType.currentText()
        #Change the interface according to the sensor selected
        if (self.sensorType == 'Landsat'):
            self.dlg.ndviLineEditRed.setEnabled(True)
            self.dlg.ndviLineEditNIR.setEnabled(True)
            self.dlg.ndviBrwRedBand.setEnabled(True)
            self.dlg.ndviBrwNIRBand.setEnabled(True)
            self.dlg.ndviBrwVNIRBand.setEnabled(False)
            self.dlg.ndviLineEditVNIR.setEnabled(False)
            self.dlg.ndviLblVNIR.setEnabled(False)
        elif (self.sensorType == 'ASTER'):
            self.dlg.ndviLineEditRed.setEnabled(False)
            self.dlg.ndviLineEditNIR.setEnabled(False)
            self.dlg.ndviBrwRedBand.setEnabled(False)
            self.dlg.ndviBrwNIRBand.setEnabled(False)
            self.dlg.ndviBrwVNIRBand.setEnabled(True)
            self.dlg.ndviLineEditVNIR.setEnabled(True)
            self.dlg.ndviLblVNIR.setEnabled(True)
    
    def uiChangeBrightnessTempInput(self):
        #Capture the variables from the interface
        self.btSensorType    = self.dlg.btSensorType.currentText()
        self.btBandNo        = self.dlg.btBandNo.currentText()

        #Change the interface according to the selected sensor
        if (self.btSensorType == 'Landsat TIRS'):
            self.tirsBands = [10,11]
            #Add the Landsat TIRS bands to the combo box
            self.dlg.btBandNo.clear()
            for self.i in range(len((self.tirsBands))):
                self.dlg.btBandNo.addItem(str(self.tirsBands[self.i]))

        elif (self.btSensorType == 'Landsat ETM+'):
            self.etmBands = [6]
            self.dlg.lblGain.setEnabled(True)
            #Add the Landsat ETM+ bands to the combo box
            self.dlg.btBandNo.clear()
            for self.i in range(len((self.etmBands))):
                self.dlg.btBandNo.addItem(str(self.etmBands[self.i]))
            
        elif (self.btSensorType == 'Landsat TM'):
            self.tmBands = [6]
            #Add the Landsat ETM+ bands to the combo box
            self.dlg.btBandNo.clear()
            for self.i in range(len((self.tmBands))):
                self.dlg.btBandNo.addItem(str(self.tmBands[self.i]))
                
        elif (self.btSensorType == 'ASTER'):
            self.tmBands = [10,11,12,13,14]
            #Add the ASTER TIR bands to the combo box
            self.dlg.btBandNo.clear()
            for self.i in range(len((self.tmBands))):
                self.dlg.btBandNo.addItem(str(self.tmBands[self.i]))
        
    def uiCalcNDVI(self):
        self.sensorType   = self.dlg.ndviSensorType.currentText()
        self.NIRBand      = self.dlg.ndviLineEditNIR.text()
        self.VNIRBand     = self.dlg.ndviLineEditVNIR.text()
        self.RedBand      = self.dlg.ndviLineEditRed.text()
        self.outputRaster = self.dlg.ndviLineEditOutputRaster.text()
        self.rasterType   = str(self.dlg.ndviFormat.currentText())
        
        #Loading the raster to the QGIS project
        if (self.dlg.ndviAddToProject.isChecked()):
            self.addToQGIS = 'Yes'
        else:
            self.addToQGIS = 'No'
        if self.sensorType == 'Landsat':
            #Validate the inputs when the selected sensor is Landsat 
            if self.NIRBand == '':
                self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                                        "The near infrared band is required",
                                        QgsMessageBar.WARNING, 3)
            elif self.RedBand == '':
                self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                                        "The red band is required",
                                        QgsMessageBar.WARNING, 3)
            elif self.outputRaster == '':
                self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                                        "The output save location is required",
                                        QgsMessageBar.WARNING, 3)
            elif self.NIRBand != '' and self.RedBand != '' and self.outputRaster != '':
                self.argList = [self.RedBand, self.NIRBand, self.outputRaster, self.rasterType, self.addToQGIS]
                self.startWorker('LSTNDVI', self.argList, 'Calculating NDVI')
        elif self.sensorType == 'ASTER':
            #Validate the inputs when the selected sensor is ASTER 
            if self.VNIRBand == '':
                self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                                        "The the visible/near infrared band is required",
                                        QgsMessageBar.WARNING, 3)
            elif self.outputRaster == '':
                self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                                        "Specify output to be saved",
                                        QgsMessageBar.WARNING, 3)
            elif self.VNIRBand != '' and self.outputRaster != '':
                self.argList = [self.VNIRBand, self.outputRaster, self.rasterType, self.addToQGIS]
                self.startWorker('ASTERNDVI', self.argList, 'Calculating NDVI')            
        self.closePlugin()
        
    def uiChangeRadianceInput(self):
        #Capture the variables from the interface
        self.radSensorType   = self.dlg.radSensorType.currentText()
        self.radGain         = self.dlg.radGain.currentText()
        self.radBandNo       = self.dlg.radBandNo.currentText()
        self.radThermalBand  = self.dlg.radThermalBand.text()
        self.radOutputRaster = self.dlg.radOutputRaster.text()
        self.radMetadata     = self.dlg.radMetadata.text()
        
        #Change the interface according to the selected sensor
        if (self.radSensorType == 'Landsat TIRS'):
            self.tirsBands = [10,11]
            self.dlg.lblGain.setEnabled(False)
            self.dlg.radGain.setEnabled(False)
            self.dlg.radOffset.setEnabled(True)
            self.dlg.radLabelOffset.setEnabled(True)
            self.dlg.radMetadata.setEnabled(True)
            self.dlg.lblRadianceMeta.setEnabled(True)
            self.dlg.radBrwMeta.setEnabled(True)
            #Add the Landsat TIRS bands to the combo box
            self.dlg.radBandNo.clear()
            for self.i in range(len((self.tirsBands))):
                self.dlg.radBandNo.addItem(str(self.tirsBands[self.i]))

        elif (self.radSensorType == 'Landsat ETM+'):
            self.dlg.lblGain.setEnabled(True)
            self.dlg.radGain.setEnabled(True)
            self.dlg.radOffset.setEnabled(False)
            self.dlg.radLabelOffset.setEnabled(False)
            self.dlg.radMetadata.setEnabled(True)
            self.dlg.lblRadianceMeta.setEnabled(True)
            self.dlg.radBrwMeta.setEnabled(True)
            self.etmBands = [6]
            self.dlg.lblGain.setEnabled(True)
            #Add the Landsat ETM+ bands to the combo box
            self.dlg.radBandNo.clear()
            for self.i in range(len((self.etmBands))):
                self.dlg.radBandNo.addItem(str(self.etmBands[self.i]))
            
        elif (self.radSensorType == 'Landsat TM'):
            self.dlg.lblGain.setEnabled(False)
            self.dlg.radGain.setEnabled(False)
            self.dlg.radOffset.setEnabled(False)
            self.dlg.radLabelOffset.setEnabled(False)
            self.dlg.radMetadata.setEnabled(True)
            self.dlg.lblRadianceMeta.setEnabled(True)
            self.dlg.radBrwMeta.setEnabled(True)
            self.tmBands = [6]
            #Add the Landsat ETM+ bands to the combo box
            self.dlg.radBandNo.clear()
            for self.i in range(len((self.tmBands))):
                self.dlg.radBandNo.addItem(str(self.tmBands[self.i]))
        
        elif (self.radSensorType == 'ASTER'):
            self.tirsBands = [10,11,12,13,14]
            self.dlg.lblGain.setEnabled(False)
            self.dlg.radGain.setEnabled(False)
            self.dlg.radOffset.setEnabled(False)
            self.dlg.radLabelOffset.setEnabled(True)
            self.dlg.lblRadianceMeta.setEnabled(False)
            self.dlg.radMetadata.setEnabled(False)
            self.dlg.radBrwMeta.setEnabled(False)
            #Add the ASTER TIR bands to the combo box
            self.dlg.radBandNo.clear()
            for self.i in range(len((self.tirsBands))):
                self.dlg.radBandNo.addItem(str(self.tirsBands[self.i]))
                
    def asterLSEOutputFile(self):
        self.rasterFormats = self.getGdalRasterFormats()
        for i in range(len(self.rasterFormats)):
            self.dlg.asterLSErasterType.addItem(str(self.rasterFormats[i]))
            
    def asterSWAOutputFile(self):
        self.rasterFormats = self.getGdalRasterFormats()
        for i in range(len(self.rasterFormats)):
            self.dlg.swaRasterType.addItem(str(self.rasterFormats[i]))
                
    def asterSCAOutputFile(self):
        self.rasterFormats = self.getGdalRasterFormats()
        for i in range(len(self.rasterFormats)):
            self.dlg.singleAsterRasterType.addItem(str(self.rasterFormats[i]))
                
    def uiNDVIthresholdOutputFile(self):
        self.rasterFormats = self.getGdalRasterFormats()
        for i in range(len(self.rasterFormats)):
            self.dlg.lseNDVIthresholdRasterFormat.addItem(str(self.rasterFormats[i]))
    
    def uiRTEOutputFile(self):
        self.rasterFormats = self.getGdalRasterFormats()
        for i in range(len(self.rasterFormats)):
            self.dlg.rteFormat.addItem(str(self.rasterFormats[i]))  
                
    def uiSingleOutputFile(self, ):
        self.rasterFormats = self.getGdalRasterFormats()
        for i in range(len(self.rasterFormats)):
            self.dlg.singleFormat.addItem(str(self.rasterFormats[i]))            
                
    def uiMonoOutputFile(self):
        self.rasterFormats = self.getGdalRasterFormats()
        for i in range(len(self.rasterFormats)):
            self.dlg.monoFormat.addItem(str(self.rasterFormats[i]))
                
    def uiPlankOutputFile(self, ):
        self.rasterFormats = self.getGdalRasterFormats()
        for i in range(len(self.rasterFormats)):
            self.dlg.plankFormat.addItem(str(self.rasterFormats[i]))
                
    def uiBtOutputFile(self):
        self.rasterFormats = self.getGdalRasterFormats()
        for i in range(len(self.rasterFormats)):
            self.dlg.btFormat.addItem(str(self.rasterFormats[i]))
                
    def uiRadOutputFile(self):
        self.rasterFormats = self.getGdalRasterFormats()
        for i in range(len(self.rasterFormats)):
            self.dlg.radFormat.addItem(str(self.rasterFormats[i]))
    
    def uiRTEOutputFile(self):
        self.rasterFormats = self.getGdalRasterFormats()
        for i in range(len(self.rasterFormats)):
            self.dlg.rteFormat.addItem(str(self.rasterFormats[i]))
                
    def uiLSEOutputFile(self):
        self.rasterFormats = self.getGdalRasterFormats()
        for i in range(len(self.rasterFormats)):
            self.dlg.zhangRasterType.addItem(str(self.rasterFormats[i]))
    
    def uiNDVIOutputFile(self):
        self.rasterFormats = self.getGdalRasterFormats()
        for i in range(len(self.rasterFormats)):
            self.dlg.ndviFormat.addItem(str(self.rasterFormats[i]))

    def uiMonoWindowOutputFile(self):
        self.rasterFormats = self.getGdalRasterFormats()
        for i in range(len(self.rasterFormats)):
            self.dlg.monoFormat.addItem(str(self.rasterFormats[i]))
    
    def calcRadiance(self):
        self.sensorType = self.dlg.radSensorType.currentText()
        self.thermalBand = self.dlg.radThermalBand.text()
        self.bandNumber = self.dlg.radBandNo.currentText()
        self.outputPath = self.dlg.radOutputRaster.text()
        self.radOffset = self.dlg.radOffset.text()
        self.gain = self.dlg.radGain.currentText()
        self.fileType = str(self.dlg.radFormat.currentText())
        if (self.dlg.radAddToQGIS.isChecked()):
            self.addToQGIS = 'Yes'
        else:
            self.addToQGIS = 'No'
        #Change the method to be called according to a sensor selected
        if (self.sensorType == 'Landsat TM'):
            #Validate the inputs
            if self.thermalBand == '':
                self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                        "The thermal infared band is required",
                        QgsMessageBar.WARNING, 3)
            elif self.outputPath == '':
                self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                        "Specify output to be saved",
                        QgsMessageBar.WARNING, 3)
            elif self.metadata == '':
                self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                        "The metadata is required",
                        QgsMessageBar.WARNING, 3)
            else:
                self.argList = [self.thermalBand, self.outputPath, self.fileType, self.metadata, self.addToQGIS]
                self.startWorker('TMRadiance', self.argList, 'Calculating Landsat TM Radiance')
                
        elif (self.sensorType == 'Landsat ETM+'):
            if self.thermalBand == '':
                self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                        "The thermal infared band is required",
                        QgsMessageBar.WARNING, 3)
            elif self.outputPath == '':
                self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                        "Specify output to be saved",
                        QgsMessageBar.WARNING, 3)
            elif self.metadata == '':
                self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                        "The metadata is required",
                        QgsMessageBar.WARNING, 3)
            elif self.gain == '':
                self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                        "The gain is required",
                        QgsMessageBar.WARNING, 3)
            else:
                self.argList = [self.thermalBand, self.gain, self.outputPath, self.fileType, self.metadata, self.addToQGIS]
                self.startWorker('ETMRadiance', self.argList, 'Calculating Landsat ETM+ Radiance')
                
        elif (self.sensorType == 'Landsat TIRS'):
            if self.thermalBand == '':
                self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                        "The thermal infared band is required",
                        QgsMessageBar.WARNING, 3)
            elif self.outputPath == '':
                self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                        "Specify output to be saved",
                        QgsMessageBar.WARNING, 3)
            elif self.metadata == '':
                self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                        "The metadata is required",
                        QgsMessageBar.WARNING, 3)
            elif self.bandNumber == '':
                self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                        "The gain is required",
                        QgsMessageBar.WARNING, 3)
            else:
                self.argList = [self.thermalBand, self.bandNumber, self.radOffset, self.outputPath, self.fileType, self.metadata, self.addToQGIS ]
                self.startWorker('TIRSRadiance', self.argList, 'Calculating Landsat TIRS Radiance')
                
        elif (self.sensorType == 'ASTER'):
            if self.thermalBand == '':
                self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                        "The thermal infared band is required",
                        QgsMessageBar.WARNING, 3)
            elif self.outputPath == '':
                self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                        "Specify output to be saved",
                        QgsMessageBar.WARNING, 3)
            elif self.bandNumber == '':
                self.iface.messageBar().pushMessage("Land Surface Temperature Plugin",
                        "The gain is required",
                        QgsMessageBar.WARNING, 3)
            else:
                self.argList = [self.thermalBand, self.bandNumber, self.outputPath, self.fileType, self.addToQGIS ]
                self.startWorker('ASTERRAD', self.argList, 'Calculating ASTER Radiance')
        self.closePlugin()
    
    def clearAsterSCAFields(self):
        self.dlg.singleAsterLSE.setText('')
        self.dlg.singleAsterRadiance.setText('')
        self.dlg.singleAsterBriTemp.setText('')
        self.dlg.singleAsterAtmWaterVapor.setText('0.0')
        self.dlg.singleAsterOutputLocation.setText('')
        
    def clearBtFields(self):
        self.dlg.btRadianceRaster.setText('')
        self.dlg.btOutputRaster.setText('')
        self.dlg.btAddToProject.setChecked(False)
            
    def clearRadFields(self):
        self.dlg.radSensorType.currentText()
        self.dlg.radThermalBand.setText('')
        self.dlg.radOutputRaster.setText('')
        self.dlg.radOffset.setText('0.0')
        self.dlg.radMetadata.setText('')
        self.dlg.radAddToQGIS.setChecked(False)
        
    def clearNDVIFields(self):
        self.dlg.ndviLineEditRed.setText('')
        self.dlg.ndviLineEditNIR.setText('')
        self.dlg.ndviLineEditOutputRaster.setText('')
        self.dlg.ndviLineEditVNIR.setText('')
        self.dlg.ndviAddToProject.setChecked(False)
     
    def clearZhangLSEFields(self):
        self.dlg.zhangNDVILineEdit.setText('')
        self.dlg.zhangOutputLineEdit.setText('')
        self.dlg.zhangLSEAddToProject.setChecked(False)
        
    def clearNDVIthresholdLSEFields(self):
        self.dlg.lseNDVIthresholdNDVI.setText('')
        self.dlg.lseNDVIthresholdOutputRaster.setText('')
        self.dlg.lseNDVIthresholdAddToProject.setChecked(False)
     
    def uiRadMetadataBrw(self):
        self.metadata = QFileDialog.getOpenFileName(self.dlg, 'Select a metadata file', "",'*.txt')
        self.dlg.radMetadata.setText(self.metadata)
    
    def uiRadOutputBrw(self):
        self.outputRaster = QFileDialog.getSaveFileName(self.dlg, 'Select the radiance output file location ', '.')
        self.dlg.radOutputRaster.setText(self.outputRaster)
        
    def uiRadThermalBrw(self):
        self.thermalBandPath = QFileDialog.getOpenFileName(self.dlg, 'Select a thermal infrared rasterfile ', '.')
        self.dlg.radThermalBand.setText(self.thermalBandPath)
    
    def uiNDVIBrwNIR(self):
        self.NIRBandPath = QFileDialog.getOpenFileName(self.dlg, 'Select a near infrared raster file', '.')
        self.dlg.ndviLineEditNIR.setText(self.NIRBandPath)
        
    def uiNDVIBrwVNIR(self):
        self.vnirBandPath = QFileDialog.getOpenFileName(self.dlg, 'Select a visible and near Infrared raster file', '.')
        self.dlg.ndviLineEditVNIR.setText(self.vnirBandPath)
    
    def uiNDVIBrwRed(self):
        self.RedBandPath = QFileDialog.getOpenFileName(self.dlg, 'Select a red raster file', '.')
        self.dlg.ndviLineEditRed.setText(self.RedBandPath)
    
    def uiNDVIBrwOut(self):
        self.outBandPath = QFileDialog.getSaveFileName(self.dlg, 'Select NDVI file location', '.')
        self.dlg.ndviLineEditOutputRaster.setText(self.outBandPath)
    
    def uiNDVIThresholdLSEBrwNDVI(self):
        self.outBandPath = QFileDialog.getOpenFileName(self.dlg, 'Select the NDVI raster file', '.')
        self.dlg.lseNDVIthresholdNDVI.setText(self.outBandPath)
        
    def uiNDVIThresholdLSEBrwSave(self):
        self.outBandPath = QFileDialog.getSaveFileName(self.dlg, 'Select LSE file save location', '.')
        self.dlg.lseNDVIthresholdOutputRaster.setText(self.outBandPath)
    
    def closePlugin(self):
        self.clearNDVIFields()
        self.clearRadFields()
        self.clearPlankFields()
        self.clearMonoWindowFields()
        self.clearZhangLSEFields()
        self.clearNDVIthresholdLSEFields()
        self.clearBtFields()
        self.clearSingleChannedlAlgFields()
        self.clearRTEFields()
        self.clearZhangFields()
        self.clearAsterSCAFields()
        self.dlg.close()
    
    def unload(self):
        """Removes the plugin menu item and icon from QGis Gui."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Land Surface Temperature'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def startWorker(self, processName, argList, message):
        self.processName = processName
        self.argList     = argList
        self.message     = message
        worker = EstimateLST(self.processName, self.argList)
        #Configure the QgsMessageBar
        messageBar  = self.iface.messageBar().createMessage(message)
        progressBar = QtGui.QProgressBar()
        progressBar.setAlignment(QtCore.Qt.AlignVCenter)
        cancelButton = QtGui.QPushButton()
        cancelButton.setText('Cancel')
        cancelButton.clicked.connect(worker.kill)
        messageBar.layout().addWidget(progressBar)
        messageBar.layout().addWidget(cancelButton)
        self.iface.messageBar().pushWidget(messageBar, self.iface.messageBar().INFO)
        self.messageBar = messageBar

        #start the worker in a new thread
        thread = QtCore.QThread()
        worker.moveToThread(thread)
        worker.finished.connect(self.workerFinished)
        worker.error.connect(self.workerError)
        worker.progress.connect(progressBar.setValue)
        thread.started.connect(worker.run)
        thread.start()
        self.thread = thread
        self.worker = worker

    def workerFinished(self, ret):
        #Clean up the worker and thread
        self.worker.deleteLater()
        self.thread.quit()
        self.thread.wait()
        self.thread.deleteLater()

        #Remove widget from messagebar
        self.iface.messageBar().popWidget(self.messageBar)
        if ret is not None:
            #Add the project to the map
            iface.addRasterLayer(ret, self.processName)
        else:
            #Notify the user that an error has occurred
            self.iface.messageBar().pushMessage('Something went wrong! See the message log for more information.', level=QgsMessageBar.CRITICAL, duration = 5)

    def workerError(self, e, exception_string):
        QgsMessageLog.logMessage('Worker thread raised an exception: \n'.format(exception_string), level = QgsMessageLog.CRITICAL)
        
    def run(self):
        """Run method that performs all the real work"""
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass
