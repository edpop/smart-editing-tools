# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Smart_editing_tools
                                 A QGIS plugin
 Get some tools!
                              -------------------
        begin                : 2015-04-29
        git sha              : $Format:%H$
        copyright            : (C) 2015 by Eduard Popov
        email                : popov@vl.ru
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
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QObject
from PyQt4.QtGui import QAction, QIcon
from qgis.core import *
from qgis.gui import *
# Initialize Qt resources from file resources.py
import resources

import os.path

from tools.smart_angle_drawing import *
from tools.awesome_editing import *
from tools.brainy_spin import *
from tools.multi_editing import *

class Smart_editing_tools:
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
        self.canvas = self.iface.mapCanvas()

        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale

        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'smart-editing-tools_{}.qm'.format(locale))
        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.name = self.tr(u'&Smart editing tools')
        self.menu = self.iface.vectorMenu().addMenu(QIcon(":/plugins/smart-editing-tools/icon.png"),self.name)
        self.toolbar = self.iface.addToolBar(u'Smart_editing_tools')
        self.toolbar.setObjectName(u'Smart_editing_tools')
        self.oldTool = None
        self.disconnection = None

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
        return QCoreApplication.translate('Smart_editing_tools', message)


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
        action.setCheckable(True)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.menu.addAction(action)
            #self.iface.addPluginToVectorMenu(
                #self.name,
                #action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        #Smart angles
        self.add_action(
            ':/plugins/smart-editing-tools/tools/smart_angle_drawing.png',
            text=self.tr(u'Smart angle drawing'),
            callback=self.SmartAngleInit,
            add_to_menu = True,
            whats_this="SmartAngle",
            parent=self.iface.mainWindow())
        self.SmartAngle_tool = SmartAngleTool(self.iface)

        #Awesome editing
        self.add_action(
            ':/plugins/smart-editing-tools/tools/awesome_editing.png',
            text=self.tr(u'Awesome editing'),
            callback=self.AgewomeEditingInit,
            add_to_menu = True,
            whats_this="AwesomeEditing",
            parent=self.iface.mainWindow())
        self.AwesomeEditing_tool = AwesomeEditingTool(self.iface)

        #Brainy spin
        self.add_action(
            ':/plugins/smart-editing-tools/tools/brainy_spin.png',
            text=self.tr(u'Brainy spin'),
            callback=self.BrainySpinInit,
            add_to_menu = True,
            whats_this="BrainySpin",
            parent=self.iface.mainWindow())
        self.BrainySpin_tool = BrainySpinTool(self.iface)

        #Multi rotate
        self.add_action(
            ':/plugins/smart-editing-tools/tools/multi_editing.png',
            text=self.tr(u'Multi-editing'),
            callback=self.MultiEditingInit,
            add_to_menu = True,
            whats_this="MultiEditing",
            parent=self.iface.mainWindow())
        self.MultiEditing_tool = MultiEditingTool(self.iface, self)

        self.canvas.mapToolSet.connect(self.deactivate)
        self.iface.currentLayerChanged.connect(self.toggle)
        self.toggle()


    def unload(self):
        self.canvas.mapToolSet.disconnect(self.deactivate)
        self.iface.currentLayerChanged.disconnect(self.toggle)
        #Removes the plugin menu item and icon from QGIS GUI.
        for action in self.actions:
            self.iface.removePluginVectorMenu(
                self.tr(u'&Smart editing tools'),
                action)
            self.iface.removeToolBarIcon(action)

        self.iface.vectorMenu().removeAction(self.menu.menuAction())

        self.canvas.unsetMapTool(self.SmartAngle_tool)
        self.canvas.unsetMapTool(self.AwesomeEditing_tool)
        self.canvas.unsetMapTool(self.BrainySpin_tool)
        self.canvas.unsetMapTool(self.MultiEditing_tool)

        # remove the toolbar
        del self.toolbar

    def deactivate(self):
        for action in self.actions:
            action.setChecked(False)

    def toggle(self):
        layer = self.canvas.currentLayer()
        if self.disconnection:
            self.disconnection()
        #Decide whether the plugin button/menu is enabled or disabled
        if layer is not None and layer.type() == QgsMapLayer.VectorLayer:
            if (layer.isEditable() and (layer.geometryType() == 2 or layer.geometryType() == 1)):
                for action in self.actions:
                    if action.whatsThis() in ["SmartAngle","AwesomeEditing","BrainySpin"]:
                        action.setEnabled(True)

                layer.editingStopped.connect(self.toggle)
                self.disconnection = lambda :layer.editingStopped.disconnect(self.toggle)

            else:
                if layer.type() <> 0:
                    if self.canvas.mapTool() <> self.MultiEditing_tool:
                        self.canvas.unsetMapTool(self.canvas.mapTool())
                        if self.oldTool:
                            self.canvas.setMapTool(self.oldTool)

                for action in self.actions:
                    if action.whatsThis() in ["SmartAngle","AwesomeEditing","BrainySpin"]:
                        action.setEnabled(False)
                        action.setChecked(False)

                layer.editingStarted.connect(self.toggle)
                self.disconnection = lambda :layer.editingStarted.disconnect(self.toggle)

        else:
            self.disconnection = None
            for action in self.actions:
                if action.whatsThis() in ["SmartAngle","AwesomeEditing","BrainySpin"]:
                    action.setEnabled(False)
                    action.setChecked(False)


    def pushToolButton(self, bnName):
        for action in self.actions:
            if action.whatsThis() == bnName:
                action.setChecked(True)
            else:
                action.setChecked(False)

    def setTool(self,tool):
        oldTool = self.canvas.mapTool()
        if oldTool not in [self.SmartAngle_tool,self.AwesomeEditing_tool,self.BrainySpin_tool,self.MultiEditing_tool]:
            self.oldTool = oldTool
        self.canvas.setMapTool(tool)

    #############
    #Smart angle#
    #############
    def SmartAngleInit(self):
        self.setTool(self.SmartAngle_tool)
        self.pushToolButton("SmartAngle")

    #################
    #Awesome editing#
    #################
    def AgewomeEditingInit(self):
        self.setTool(self.AwesomeEditing_tool)
        self.pushToolButton("AwesomeEditing")

    #############
    #Brainy spin#
    #############
    def BrainySpinInit(self):
        self.setTool(self.BrainySpin_tool)
        self.pushToolButton("BrainySpin")

    ###############
    #Multi-editing#
    ###############
    def MultiEditingInit(self):
        self.setTool(self.MultiEditing_tool)
        self.pushToolButton("MultiEditing")