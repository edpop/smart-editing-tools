# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Smart_editing_tools
                                 A QGIS plugin
 Get some tools!
                             -------------------
        begin                : 2015-04-29
        copyright            : (C) 2015 by Eduard Popov
        email                : popov@vl.ru
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
    """Load Smart_editing_tools class from file Smart_editing_tools.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .smart_editing_tools import Smart_editing_tools
    return Smart_editing_tools(iface)
