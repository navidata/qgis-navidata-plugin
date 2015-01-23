# -*- coding: utf-8 -*-
from qgis.core import *
from PyQt4 import QtCore, QtGui
import os.path
import traceback
import sys
import types


sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from .geopy import geocoders
from PyQt4.QtGui import *
from PyQt4.QtCore import *


class geocoderWorker(QtCore.QObject):

    def __init__(self, sourceLayer, sourceLayerColumn, destinationWriter):

        super(geocoderWorker,self).__init__()

        self.sourceLayer = sourceLayer
        self.sourceLayerColumn = sourceLayerColumn
        self.destinationWriter = destinationWriter
        self.geocoder = geocoders.NaviData(timeout=1)
        self.killed = False

        self.plugin_dir = os.path.dirname(__file__)
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


    def run(self):

        try:
            self.runGeocoding()
            del self.destinationWriter
        except Exception as e:
            self.error.emit(e)
            del self.destinationWriter


    def kill(self):
        self.killed = True

    def runGeocoding(self):

        processing_count = 0
        feature_count = self.sourceLayer.featureCount()

        idx = self.sourceLayer.fieldNameIndex(self.sourceLayerColumn)

        for feature in self.sourceLayer.getFeatures():

            if self.killed:
                self.aborted.emit()
                return


            processing_count += 1

            self.progress.emit(processing_count)
            self.statusText.emit(self.tr('Geocoding address {0} of {1}').format(processing_count, feature_count))

            geocoded_addr = feature.attributes()[idx]

            new_feature = QgsFeature()
            new_feature.initAttributes(10)


            geocoder_result = self.geocodeAddress(geocoded_addr)

            if geocoder_result is None:
                description = '###'
                region1 = '###'
                region2 = '###'
                region3 = '###'
                city = '###'
                district = '###'
                street = '###'
                housenumber = '###'
                type = '###'
            else:
                description = geocoder_result.address
                region1 = geocoder_result.raw.get('region1')
                region2 = geocoder_result.raw.get('region2')
                region3 = geocoder_result.raw.get('region3')
                city = geocoder_result.raw.get('city')
                district = geocoder_result.raw.get('district')
                street = geocoder_result.raw.get('street')
                housenumber = geocoder_result.raw.get('housenumber')
                type = geocoder_result.raw.get('type')

            new_feature.setAttribute(0, geocoded_addr )
            new_feature.setAttribute(1, description )
            new_feature.setAttribute(2, region1 )
            new_feature.setAttribute(3, region2 )
            new_feature.setAttribute(4, region3 )
            new_feature.setAttribute(5, city )
            new_feature.setAttribute(6, district )
            new_feature.setAttribute(7, street )
            new_feature.setAttribute(8, housenumber )
            new_feature.setAttribute(9, type )


            #insert geometry

            if geocoder_result is not None:
                new_feature.setGeometry( QgsGeometry.fromPoint(QgsPoint(geocoder_result.longitude,geocoder_result.latitude)) )

            self.destinationWriter.addFeature(new_feature)


        #end of process

        self.finished.emit()



    def geocodeAddress(self, addr):

        for i in range(10): #retry count

            try:

                if self.killed:
                    return None

                result = self.geocoder.geocode(addr)
                return result

            except Exception as es:
                QgsMessageLog.logMessage(self.tr('Geocoding error: ') + str(es), 'navidata')

                if i ==9:
                    raise es

        return None


    finished = QtCore.pyqtSignal()
    error = QtCore.pyqtSignal(Exception)
    progress = QtCore.pyqtSignal(int)
    aborted = QtCore.pyqtSignal()
    statusText = QtCore.pyqtSignal(types.UnicodeType)








