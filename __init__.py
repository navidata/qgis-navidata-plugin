# -*- coding: utf-8 -*-
"""
/***************************************************************************
 NaviDataGeocoder
                                 A QGIS plugin
 This plugin implements geocoding service for Poland
                             -------------------
        begin                : 2015-01-05
        copyright            : (C) 2015 by navidata.pl
        email                : kontakt@navidata.pl
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
    """Load NaviDataGeocoder class from file NaviDataGeocoder.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .navidata_geocoder import NaviDataGeocoder
    return NaviDataGeocoder(iface)
