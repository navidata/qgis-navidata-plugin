# -*- coding: utf-8 -*-
"""
/***************************************************************************
 NaviDataGeocoder
                                 A QGIS plugin
 This plugin implements geocoding service for Poland
                              -------------------
        begin                : 2015-01-05
        git sha              : $Format:%H$
        copyright            : (C) 2015 by navidata.pl
        email                : kontakt@navidata.pl
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
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import QAction, QIcon
# Initialize Qt resources from file resources.py
import resources_rc
# Import the code for the dialog
from navidata_geocoder_dialog import NaviDataGeocoderDialog
from geocoderWorker import geocoderWorker
from qgis.core import *

from PyQt4.QtGui import *
from PyQt4.QtCore import *

import os.path
import sys


class NaviDataGeocoder:
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
            'NaviDataGeocoder_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = NaviDataGeocoderDialog()

        #signal bindings

        self.dlg.layerCombo.currentIndexChanged.connect(self.geocoderPopulateAttributeList)
        self.dlg.fileChoose.released.connect(self.geocoderSelectFile)
        self.dlg.geocodeButton.released.connect(self.startGeocoding)
        self.dlg.abortWork.released.connect(self.abortGeocoding)
        self.dlg.api_key.textEdited.connect(self.saveApiKey)
        self.dlg.pushButton.released.connect(self.dlg.accept)



        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&navidata.pl geocoder')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'NaviDataGeocoder')
        self.toolbar.setObjectName(u'NaviDataGeocoder')

        self.settings = QSettings()

        self.geocoding_worker = None
        self.geocoding_thread = None


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

        return QCoreApplication.translate('NaviDataGeocoder', message)


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
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/NaviDataGeocoder/location.png'
        self.add_action(
            icon_path,
            text=self.tr(u'geocoding'),
            callback=self.run_geocode,
            parent=self.iface.mainWindow())



    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr('&navidata.pl geocoder'),
                action)
            self.iface.removeToolBarIcon(action)


    def run_geocode(self):
        """Run method that performs all the real work"""
        # show the dialog

        #remove old data

        self.dlg.sourceAttributeSelection.clear()
        self.dlg.outputSHP.clear()

        self.dlg.geocodeButton.setEnabled(True)
        self.dlg.abortWork.setEnabled(False)
        self.dlg.progressBar.setValue(0)
        self.dlg.statusText.clear()

        #populate layer list

        layers = QgsMapLayerRegistry.instance().mapLayers().values()

        layer_count = 0

        self.dlg.layerCombo.clear()

        for layer in layers:

            if layer.type() == QgsMapLayer.VectorLayer:
                self.dlg.layerCombo.addItem( layer.name(), layer )
                layer_count += 1


        if layer_count == 0:
            msgBox = QMessageBox()
            msgBox.information(None, self.tr('Information'), self.tr('Before running geocoder, please add at least one vector layer'))
            return

        selected_layer = self.dlg.layerCombo.itemData(self.dlg.layerCombo.currentIndex())

        #populate saved form data

        self.dlg.api_key.clear()
        self.dlg.api_key.insert(self.settings.value('navidata/api_key'))

        self.geocoderPopulateAttributeList(self.dlg.layerCombo.currentIndex())


        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass


    def run_revgeocode(self):
        """Run method that performs all the real work"""
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass



    def startGeocoding(self):


        layer_file = self.dlg.outputSHP.text()
        #source_field = self.dlg.sourceAttributeSelection.itemData(self.dlg.sourceAttributeSelection.currentIndex())
        source_field = self.dlg.sourceAttributeSelection.currentText()
        source_layer = selected_layer = self.dlg.layerCombo.itemData(self.dlg.layerCombo.currentIndex())

        self.geocoding_worker = None
        self.geocoding_thread = None


        if len(layer_file) == 0:
            QMessageBox.warning(self.dlg, self.tr('Information'), self.tr('Select output layer'))
            return


        feature_count = source_layer.featureCount()

        if feature_count == 0:
            QMessageBox.warning(self.dlg, self.tr('Information'), self.tr('Selected layer is empty'))
            return

        #create or overwrite layer

        fields = QgsFields()

        #attr 0
        fields.append(QgsField(source_field, QVariant.String))
        #attr 1  - navidata -> description
        fields.append(QgsField('descr', QVariant.String))
        #attr 2 - navidata -> region1
        fields.append(QgsField('region1', QVariant.String))
        #attr 3 - navidata -> region2
        fields.append(QgsField('region2', QVariant.String))
        #attr 4 - navidata -> region3
        fields.append(QgsField('region3', QVariant.String))
        #attr 5 - navidata -> city
        fields.append(QgsField('city', QVariant.String))
        #attr 6 - navidata -> district
        fields.append(QgsField('discrict', QVariant.String))
        #attr 7 - navidata -> street
        fields.append(QgsField('street', QVariant.String))
        #attr 8 - navidata -> housenumber
        fields.append(QgsField('housenumber', QVariant.String))
        #attr 9 - navidata -> type
        fields.append(QgsField('type', QVariant.String))



        writer = QgsVectorFileWriter(layer_file, "UTF-8", fields, QGis.WKBPoint, QgsCoordinateReferenceSystem(4326), "ESRI Shapefile")

        if writer.hasError() != QgsVectorFileWriter.NoError:
            QMessageBox.warning(self.dlg, self.tr('Information'), self.tr('Error writing SHP file: ') + str(writer.hasError))
            del writer
            return

        self.dlg.progressBar.setRange(0, feature_count)
        self.dlg.progressBar.setValue(0)
        self.dlg.statusText.clear()

        self.dlg.abortWork.setEnabled(True)
        self.dlg.geocodeButton.setEnabled(False)

        worker = geocoderWorker(source_layer, source_field, writer)

        thread = QThread(self.dlg)
        worker.moveToThread(thread)
        worker.progress.connect(self.dlg.progressBar.setValue)
        worker.statusText.connect(self.geocoderStatusText)
        worker.finished.connect(self.geocodingFinished)
        worker.aborted.connect(self.geocodingAborted)
        worker.error.connect(self.geocodingError)


        thread.started.connect(worker.run)
        thread.start()

        self.geocoding_worker = worker
        self.geocoding_thread = thread


    def geocodingFinished(self):
        QMessageBox.information(self.dlg, self.tr('Information'), self.tr('Geocoding finished'))
        self.dlg.geocodeButton.setEnabled(True)
        self.dlg.abortWork.setEnabled(False)
        self.geocoderStatusText(self.tr('Geocoding finished'))

    def geocodingAborted(self):
        QMessageBox.information(self.dlg, self.tr('Information'), self.tr('Geocoding aborted'))
        self.dlg.geocodeButton.setEnabled(True)
        self.dlg.abortWork.setEnabled(False)
        self.dlg.progressBar.setValue(0)
        self.geocoderStatusText(self.tr('Geocoding aborted'))



    def geocodingError(self, e):
        QMessageBox.critical(self.dlg, self.tr('Error'), self.tr('Error: ') + str(e))
        self.dlg.geocodeButton.setEnabled(True)
        self.dlg.abortWork.setEnabled(False)


    def cleanGeocodingWorker(self):

        self.geocoding_worker.deleteLater()
        self.geocoding_thread.quit()
        self.geocoding_thread.wait()
        self.geocoding_thread.deleteLater()


    def geocoderSelectFile(self, event = None):

        filename = QFileDialog.getSaveFileName(self.dlg, self.tr("Save SHP file:"),
self.settings.value("navidata/save_dir"),self.tr("ShapeFile (*.shp)"))

        if filename:
            self.settings.setValue("navidata/save_dir", os.path.dirname(filename))
            self.dlg.outputSHP.clear()
            self.dlg.outputSHP.insert(filename)

    def geocoderPopulateAttributeList(self, current):

        self.dlg.sourceAttributeSelection.clear()

        if current == -1:
            return

        layer = self.dlg.layerCombo.itemData(current)


        for f in layer.pendingFields():

            self.dlg.sourceAttributeSelection.addItem(f.name())

    def abortGeocoding(self, event = None):
        self.geocoding_worker.kill()


    def geocoderStatusText(self, txt):
        self.dlg.statusText.setText(txt)

    def saveApiKey(self, txt):
        self.settings.setValue('navidata/api_key', txt)







