# -*- coding: utf-8 -*-
from common import *

class MultiEditingTool(QgsMapTool):
    def __init__(self, iface, parent):
        self.parent = parent
        self.iface = iface
        self.canvas = self.iface.mapCanvas()
        QgsMapTool.__init__(self,self.canvas)

        #Mode and its options
        self.mode = None
        self.vertex = None
        self.segments = []
        self.brainySpinOptions = {"segment1": None}
        self.rbBrainySpin = rbInit(self.canvas, QColor(160,189,255), width=5)
        self.rbBrainySpin.setOpacity(0.7)

        #Hold down keys
        self.ctrl = None
        self.shift = None

        #Snapping
        self.rbSnap = rbInit(self.canvas, QColor(118,226,255), width=5)

        #Rect
        self.rect = None
        self.point = None
        self.rbRect = rbInit(self.canvas, QColor(255,235,206), lineStyle=Qt.DashLine, brushStyle=Qt.SolidPattern)
        self.rbRect.setBorderColor(QColor(0,0,0))
        self.rbRect.setOpacity(0.2)

        #Selected features
        self.features = []
        self.buffer = []
        self.rbFeatures = rbInit(self.canvas, QColor(187,255,128), width=2, lineStyle=Qt.DashLine, brushStyle=Qt.SolidPattern)
        self.rbFeatures.setOpacity(0.8)

        #Interface
        self.multiSelectionCheckBox = QCheckBox(self.tr(u'Multi-\nselect'))
        self.transformModeComboBox = QComboBox()
        self.transformModeComboBox.addItem(QIcon(":/plugins/smart_editing_tools/images/none.png"),
                                           self.tr(u'None'), editModes.none)
        self.transformModeComboBox.addItem(QIcon(":/plugins/smart_editing_tools/images/resize.png"),
                                           self.tr(u'Resize'), editModes.resize)
        self.transformModeComboBox.addItem(QIcon(":/plugins/smart_editing_tools/images/skew.png"),
                                           self.tr(u'Skew'), editModes.skew)

        flipHorizontal = QAction(QIcon(":/plugins/smart_editing_tools/images/flip_horizontal.png"),
                                 self.tr(u'Flip Horizontal'), self.iface.mainWindow())
        flipHorizontal.triggered.connect(self.flipHorizontal)
        flipVertical = QAction(QIcon(":/plugins/smart_editing_tools/images/flip_vertical.png"),
                               self.tr(u'Flip Vertical'), self.iface.mainWindow())
        flipVertical.triggered.connect(self.flipVertical)
        flipToolButton = QToolButton()
        flipToolButton.setPopupMode(QToolButton.MenuButtonPopup)
        flipToolButton.addActions([flipHorizontal, flipVertical])
        flipToolButton.setDefaultAction(flipHorizontal)
        flipToolButton.triggered.connect(flipToolButton.setDefaultAction)

        self.toolbarItems = [
            self.parent.toolbar.addSeparator(),
            self.parent.toolbar.addWidget(self.multiSelectionCheckBox),
            self.parent.toolbar.addAction(QIcon(":/plugins/smart_editing_tools/images/attributes_dlg.png"),
                                          self.tr(u'Set attributes'), self.attributesDlg),
            self.parent.toolbar.addSeparator(),
            self.parent.toolbar.addWidget(flipToolButton),
            self.parent.toolbar.addWidget(self.transformModeComboBox),

            self.parent.toolbar.addSeparator(),
            self.parent.toolbar.addAction(QIcon(":/plugins/smart_editing_tools/images/copy.png"),
                                          self.tr(u'Copy'), self.copy),
            self.parent.toolbar.addAction(QIcon(":/plugins/smart_editing_tools/images/paste.png"),
                                          self.tr(u'Paste'), self.paste),

            self.parent.toolbar.addSeparator(),
            self.parent.toolbar.addAction(QIcon(":/plugins/smart_editing_tools/images/save_edits.png"),
                                          self.tr(u'Save edits'), self.saveEdits),
            self.parent.toolbar.addAction(QIcon(":/plugins/smart_editing_tools/images/remove_edits.png"),
                                          self.tr(u'Remove edits'), self.removeEdits),

            self.parent.toolbar.addSeparator()
        ]
        self.brainySpin = self.parent.toolbar.addAction(QIcon(":/plugins/smart_editing_tools/images/multi_brainy_spin.png"),
                                                        self.tr(u'Brainy spin'))
        self.brainySpin.setCheckable(True)
        self.toolbarItems.append(self.brainySpin)

        for item in self.toolbarItems:
            item.setVisible(False)

        #It's hart to name this variables
        self.waiting = False
        self.pressFinished = True
        self.releaseFinished = True
        self.releaseEvent = None

    def tr(self, message):
        return QCoreApplication.translate("MultiEditingTool", message)

    def isTransient(self):
        return False

    def isEditTool(self):
        #this is a lie, but the tool does not have to be deactivated
        return False

    def width(self):
        return self.canvas.mapUnitsPerPixel()*10

    def activate(self):
        self.mode = editModes.standart
        self.resetCursor()
        for item in self.toolbarItems:
            if item == self.brainySpin: continue
            item.setVisible(True)

        proj = QgsProject.instance()
        self.multiSelectionCheckBox.setCheckState( proj.readNumEntry("mapvlru_tools", "multi_selection_on", 2)[0] )
        self.transformModeComboBox.setCurrentIndex(
            self.transformModeComboBox.findData( proj.readNumEntry("mapvlru_tools", "editMode", 0)[0] ) )

    def deactivate(self):
        self.reset()
        for item in self.toolbarItems:
            item.setVisible(False)

        proj = QgsProject.instance()
        proj.writeEntry("mapvlru_tools", "multi_selection_on", self.multiSelectionCheckBox.checkState())
        proj.writeEntry("mapvlru_tools", "editMode",
                        self.transformModeComboBox.itemData( self.transformModeComboBox.currentIndex() ) )

    def reset(self):
        self.setRect(None)
        self.point = None

        self.features = []
        self.buffer = []
        self.rbFeatures.reset()
        self.rbRect.reset()
        self.rbSnap.reset()
        self.rbBrainySpin.reset()

        self.setMode(editModes.standart)


    #EVENTS
    def keyPressEvent(self, keyEvent):
        if keyEvent.key() == Qt.Key_Control:
            self.ctrl = True
            self.setMode(editModes.standart)
        if keyEvent.key() == Qt.Key_Shift:
            self.shift = True

    def keyReleaseEvent(self, keyEvent):
        if keyEvent.key() == Qt.Key_Control:
            self.ctrl = False
            self.setMode(self.calcMode(self.toMapCoordinates(self.canvas.mouseLastXY())))
        if keyEvent.key() == Qt.Key_Shift:
            self.shift = False

    def canvasPressEvent(self, mouseEvent):
        self.pressFinished = False
        self.waiting = True

        if mouseEvent.button() == 1:
            self.point = self.toMapCoordinates(mouseEvent.pos())
            if self.mode == editModes.move:
                #use snapper
                if not self.shift:
                    snapPoint = self.calcSnapPoint(mouseEvent.pos())
                    if snapPoint: self.point = snapPoint

            elif self.mode == editModes.resize:
                #init mode options and attract self.point to rect
                num = self.calcVertexNum(self.point)
                if num is not None:
                    movingSegments = [ [num-1,num],[num-3,num] ]
                    rectPoint = self.rect.vertexAt(num)
                    self.vertex = {"point": rectPoint, "num": num}
                else:
                    segmentNum = self.calcSegmentNum(self.point)
                    movingSegments = [ segmentNum ]
                    rectPoint = pointOnSegment( self.point, [self.rect.vertexAt(segmentNum[0]),self.rect.vertexAt(segmentNum[1])] )
                    self.vertex = None

                self.segments = self.makePairs( movingSegments )
                self.point = rectPoint

            elif self.mode == editModes.skew:
                self.segments = self.makePairs( [ self.calcSegmentNum(self.point) ] )
                segmentNum = self.calcSegmentNum(self.point)
                rectPoint = pointOnSegment( self.point, [self.rect.vertexAt(segmentNum[0]),self.rect.vertexAt(segmentNum[1])] )
                self.point = rectPoint

            elif self.mode == editModes.brainySpin:
                segment = self.findSelectedSegment(self.point)
                self.brainySpinOptions["segment1"] = segment

        elif mouseEvent.button() == 2:
            self.reset()

        if not self.releaseFinished:
            self.release(self.releaseEvent)

        self.waiting = False
        self.pressFinished = True

    def canvasMoveEvent(self, mouseEvent):
        if self.waiting:
            return
        self.waiting = True

        mapPos = self.toMapCoordinates(mouseEvent.pos())
        if self.mode == editModes.standart:
            if self.point:
                if self.point <> mapPos:
                    rect = QgsRectangle(self.point, mapPos)
                    self.rbRect.setToGeometry(QgsGeometry.fromRect(rect),QgsVectorLayer())
                else:
                    self.rbRect.reset()

        elif self.point and self.point <> mapPos:
            if self.mode == editModes.move:
                if not self.shift:
                    snapPoint = self.calcSnapPoint(mouseEvent.pos())
                    if snapPoint: mapPos = snapPoint
                dx = mapPos.x()-self.point.x()
                dy = mapPos.y()-self.point.y()
                self.moveRbRect(dx, dy)

                self.moveRbFeatures(dx,dy)

            elif self.mode == editModes.rotate:
                relPoint = self.centerRect()
                alpha = calcAngle(mapPos,relPoint)-calcAngle(self.point, relPoint)
                if self.shift:
                    alpha = nearestAngle(leadAngle(alpha), 8)
                self.rotateRbRect(relPoint, alpha)

                self.rotateRbFeatures(relPoint, alpha)

            elif self.mode == editModes.resize:
                if self.shift and self.vertex:
                    num = self.vertex["num"]-2
                    if num < 0: num+=4
                    mapPos = pointOnLine(mapPos, [ self.rect.vertexAt(num),self.vertex["point"] ])
                dx = mapPos.x()-self.point.x()
                dy = mapPos.y()-self.point.y()
                self.resizeRbRect(dx, dy)

                self.resizeRbFeatures(dx, dy)

            elif self.mode == editModes.skew:
                pair = self.segments[0]
                sSegment = pair["static"]
                mSegment = pair["moving"]
                mapPos = pointOnLine( mapPos, mSegment )
                dx = mapPos.x()-self.point.x()
                dy = mapPos.y()-self.point.y()
                s0, s1 = sSegment[0], sSegment[1]
                m0 = mSegment[0]
                gamma = calcAngle(s0,s1)
                alpha = calcAngle(m0, s0) - gamma
                beta = calcAngle(QgsPoint(m0.x()+dx,m0.y()+dy),s0) - gamma
                self.skewRbRect(alpha, beta, gamma)

                self.skewRbFeatures(alpha, beta, gamma)

            elif self.mode == editModes.brainySpin:
                if self.brainySpinOptions["segment1"] is not None:
                    s1 = self.brainySpinOptions["segment1"]
                    s2 = self.findSegment(mapPos)
                    if s2 and s1 <> s2:
                        p1 = QgsPoint( (s1[0].x()+s1[1].x())/2, (s1[0].y()+s1[1].y())/2 )
                        p2 = QgsPoint( (s2[0].x()+s2[1].x())/2, (s2[0].y()+s2[1].y())/2 )
                        dx = p2.x() - p1.x()
                        dy = p2.y() - p1.y()
                        alpha = calcAngle(s2[0], s2[1]) - calcAngle(s1[0],s1[1]) + pi
                        self.brainySpinRbRect(dx,dy,p2,alpha)

                        self.brainySpinRbFeatures(dx,dy,p2,alpha)

        else:
            self.rbBrainySpin.reset()
            if self.mode == editModes.brainySpin:
                segment = self.findSelectedSegment(mapPos)
                if segment:
                    self.rbBrainySpin.setToGeometry(QgsGeometry.fromPolyline(segment), QgsVectorLayer())

            self.setMode(self.calcMode(mapPos))

        self.rbSnap.reset()
        if self.mode == editModes.move:
            if not self.shift:
                snapResult = self.getSnapResult(mouseEvent.pos())
                if snapResult:
                    self.rbSnap.setToGeometry(QgsGeometry.fromPoint(snapResult.snappedVertex), snapResult.layer)

        self.waiting = False

    def canvasReleaseEvent(self, mouseEvent):
        self.waiting = True
        if not self.pressFinished:
            self.releaseFinished = False
            self.releaseEvent = mouseEvent
            return

        self.release(mouseEvent)
        self.waiting = False

    def release(self, mouseEvent):
        mapPos = self.toMapCoordinates(mouseEvent.pos())
        if mouseEvent.button() == 1:
            if self.mode == editModes.standart:
                if self.point and self.point <> mapPos:
                    rect = QgsRectangle(self.point, mapPos)
                    self.updateFeatures(rect)

                    self.refreshRect()

                    self.refreshRb()

                if not self.ctrl:
                    self.setMode(self.calcMode(mapPos))

            elif self.mode == editModes.move:
                snapPoint = self.calcSnapPoint(mouseEvent.pos())
                if snapPoint: mapPos = snapPoint
                if self.point and self.point <> mapPos:
                    dx = mapPos.x()-self.point.x()
                    dy = mapPos.y()-self.point.y()
                    self.moveRect(dx, dy)

                    self.moveFeatures(dx,dy)

                    self.canvas.refresh()

            elif self.mode == editModes.rotate:
                if self.point and self.point <> mapPos:
                    relPoint = self.centerRect()
                    alpha = calcAngle(mapPos,relPoint)-calcAngle(self.point, relPoint)
                    if self.shift:
                        alpha = nearestAngle(leadAngle(alpha), 8)
                    self.rotateRect(relPoint, alpha)

                    self.rotateFeatures(relPoint, alpha)

                    self.canvas.refresh()

            elif self.mode == editModes.resize:
                if self.point and self.point <> mapPos:
                    if self.vertex and self.shift:
                        num = self.vertex["num"]-2
                        if num < 0: num+=4
                        mapPos = pointOnLine(mapPos, [ self.rect.vertexAt(num),self.vertex["point"] ])
                    dx = mapPos.x()-self.point.x()
                    dy = mapPos.y()-self.point.y()
                    self.resizeRect(dx, dy)

                    self.resizeFeatures(dx,dy)

                    self.canvas.refresh()

            elif self.mode == editModes.skew:
                if self.point and self.point <> mapPos:
                    pair = self.segments[0]
                    sSegment = pair["static"]
                    mSegment = pair["moving"]
                    mapPos = pointOnLine( mapPos, mSegment )
                    dx = mapPos.x()-self.point.x()
                    dy = mapPos.y()-self.point.y()
                    s0, s1 = sSegment[0], sSegment[1]
                    m0 = mSegment[0]
                    gamma = calcAngle(s0,s1)
                    alpha = calcAngle(m0, s0) - gamma
                    beta = calcAngle(QgsPoint(m0.x()+dx,m0.y()+dy),s0) - gamma
                    self.skewRect(alpha, beta, gamma)

                    self.skewFeatures(alpha, beta, gamma)

                    self.canvas.refresh()

            elif self.mode == editModes.brainySpin:
                if self.brainySpinOptions["segment1"] is not None:
                    s1 = self.brainySpinOptions["segment1"]
                    self.brainySpinOptions["segment1"] = None
                    s2 = self.findSegment(mapPos)
                    if s2 and s1 <> s2:
                        p1 = QgsPoint( (s1[0].x()+s1[1].x())/2, (s1[0].y()+s1[1].y())/2 )
                        p2 = QgsPoint( (s2[0].x()+s2[1].x())/2, (s2[0].y()+s2[1].y())/2 )
                        dx = p2.x() - p1.x()
                        dy = p2.y() - p1.y()
                        alpha = calcAngle(s2[0], s2[1]) - calcAngle(s1[0],s1[1]) + pi
                        self.brainySpinRect(dx,dy,p2,alpha)

                        self.brainySpinFeatures(dx,dy,p2,alpha)

                        self.canvas.refresh()

        self.point = None
        self.releaseFinished = True


    #BRAINING
    def calcSnapPoint(self, mousePos):
        result = self.getSnapResult(mousePos)
        if result:
            return result.snappedVertex
        else:
            return None

    def getSnapResult(self, mousePos):
        snapper = QgsMapCanvasSnapper(self.canvas)
        (retval, result) = snapper.snapToBackgroundLayers(mousePos)
        if len(result)>0:
            return result[0]
        else:
            return None

    def calcVertex(self, point):
        vertex = None
        dist = self.width()
        for i in range(4):
            Td = distance(point, self.rect.vertexAt(i))
            if Td < dist:
                dist = Td
                vertex = self.rect.vertexAt(i)

        return vertex

    def calcVertexNum(self, point):
        num = None
        dist = self.width()
        for i in range(4):
            Td = distance(point, self.rect.vertexAt(i))
            if Td < dist:
                dist = Td
                num = i

        return num

    def calcSegment(self, point):
        segment = None
        dist = self.width()
        for i in range(4):
            Td = distancePS( point, [self.rect.vertexAt(i),self.rect.vertexAt(i+1)] )
            if Td < dist:
                dist = Td
                segment = [self.rect.vertexAt(i),self.rect.vertexAt(i+1)]

        return segment

    def calcSegmentNum(self, point):
        num = None
        dist = self.width()
        for i in range(4):
            Td = distancePS( point, [self.rect.vertexAt(i),self.rect.vertexAt(i+1)] )
            if Td < dist:
                dist = Td
                num = [i,i+1 if i < 3 else 0]

        return num

    def makePairs(self, segments):
        pairs = []
        for segment in segments:
            pairs.append( {"moving": segment, "static": [segment[1]-2, segment[0]-2]} )
        for i in range(len(pairs)):
            for key in pairs[i].keys():
                for j in range(len(pairs[i][key])):
                    num = pairs[i][key][j]
                    while num < 0:
                        num+=4
                    pairs[i][key][j] = self.rect.vertexAt(num)

        return pairs

    def findSelectedSegment(self, point):
        segment = None
        d = None
        width = self.width()
        rect = QgsRectangle(QgsPoint(point.x()+width,point.y()+width),
                            QgsPoint(point.x()-width,point.y()-width))
        for row in self.features:
            layer, fIds = row["layer"], row["fIds"]
            lRect = self.toLayerCoordinates(layer, rect)
            if layer.wkbType() == QGis.WKBLineString:
                for feature in layer.getFeatures(QgsFeatureRequest().setFilterFids(fIds)):
                    geom = feature.geometry()
                    if not geom.intersects(lRect):
                        continue
                    polyline = geom.asPolyline()
                    for i in range(len(polyline)-1):
                        p1 = self.toMapCoordinates(layer, polyline[i])
                        p2 = self.toMapCoordinates(layer, polyline[i+1])
                        Td = distancePS(point, [p1,p2])
                        if (d is None and Td < width) or (Td < d):
                            d = Td
                            segment = [p1,p2]

            elif layer.wkbType() == QGis.WKBPolygon:
                for feature in layer.getFeatures(QgsFeatureRequest().setFilterFids(fIds)):
                    geom = feature.geometry()
                    if not geom.intersects(lRect):
                        continue
                    polygon = geom.asPolygon()
                    for polygonling in polygon:
                        for i in range(len(polygonling)-1):
                            p1 = self.toMapCoordinates(layer, polygonling[i])
                            p2 = self.toMapCoordinates(layer, polygonling[i+1])
                            Td = distancePS(point, [p1,p2])
                            if (d is None and Td < width) or (Td < d):
                                d = Td
                                segment = [p1,p2]

            elif layer.wkbType() == QGis.WKBMultiLineString:
                for feature in layer.getFeatures(QgsFeatureRequest().setFilterFids(fIds)):
                    geom = feature.geometry()
                    if not geom.intersects(lRect):
                        continue
                    lines = geom.asMultiPolyline()
                    for line in lines:
                        for i in range(len(line)-1):
                            p1 = self.toMapCoordinates(layer, line[i])
                            p2 = self.toMapCoordinates(layer, line[i+1])
                            Td = distancePS(point, [p1,p2])
                            if (d is None and Td < width) or (Td < d):
                                d = Td
                                segment = [p1,p2]

            elif layer.wkbType() == QGis.WKBMultiPolygon:
                for feature in layer.getFeatures(QgsFeatureRequest().setFilterFids(fIds)):
                    geom = feature.geometry()
                    if not geom.intersects(lRect):
                        continue
                    polygons = geom.asMultiPolygon()
                    for polygon in polygons:
                        for polygonling in polygon:
                            for i in range(len(polygonling)-1):
                                p1 = self.toMapCoordinates(layer, polygonling[i])
                                p2 = self.toMapCoordinates(layer, polygonling[i+1])
                                Td = distancePS(point, [p1,p2])
                                if (d is None and Td < width) or (Td < d):
                                    d = Td
                                    segment = [p1,p2]

        return segment

    def findSegment(self, point):
        segment = None
        d = None
        width = self.width()
        rect = QgsRectangle(QgsPoint(point.x()+width,point.y()+width),
                            QgsPoint(point.x()-width,point.y()-width))
        for layer in self.canvas.layers():
            if layer.type() <> 0:
                continue

            lRect = self.toLayerCoordinates(layer, rect)
            if layer.wkbType() == QGis.WKBLineString:
                for feature in layer.getFeatures(QgsFeatureRequest(lRect)):
                    geom = feature.geometry()
                    polyline = geom.asPolyline()
                    for i in range(len(polyline)-1):
                        p1 = self.toMapCoordinates(layer, polyline[i])
                        p2 = self.toMapCoordinates(layer, polyline[i+1])
                        Td = distancePS(point, [p1,p2])
                        if (d is None and Td < width) or (Td < d):
                            d = Td
                            segment = [p1,p2]

            elif layer.wkbType() == QGis.WKBPolygon:
                for feature in layer.getFeatures(QgsFeatureRequest(lRect)):
                    geom = feature.geometry()
                    polygon = geom.asPolygon()
                    for polygonling in polygon:
                        for i in range(len(polygonling)-1):
                            p1 = self.toMapCoordinates(layer, polygonling[i])
                            p2 = self.toMapCoordinates(layer, polygonling[i+1])
                            Td = distancePS(point, [p1,p2])
                            if (d is None and Td < width) or (Td < d):
                                d = Td
                                segment = [p1,p2]

            elif layer.wkbType() == QGis.WKBMultiLineString:
                for feature in layer.getFeatures(QgsFeatureRequest(lRect)):
                    geom = feature.geometry()
                    lines = geom.asMultiPolyline()
                    for line in lines:
                        for i in range(len(line)-1):
                            p1 = self.toMapCoordinates(layer, line[i])
                            p2 = self.toMapCoordinates(layer, line[i+1])
                            Td = distancePS(point, [p1,p2])
                            if (d is None and Td < width) or (Td < d):
                                d = Td
                                segment = [p1,p2]

            elif layer.wkbType() == QGis.WKBMultiPolygon:
                for feature in layer.getFeatures(QgsFeatureRequest(lRect)):
                    geom = feature.geometry()
                    polygons = geom.asMultiPolygon()
                    for polygon in polygons:
                        for polygonling in polygon:
                            for i in range(len(polygonling)-1):
                                p1 = self.toMapCoordinates(layer, polygonling[i])
                                p2 = self.toMapCoordinates(layer, polygonling[i+1])
                                Td = distancePS(point, [p1,p2])
                                if (d is None and Td < width) or (Td < d):
                                    d = Td
                                    segment = [p1,p2]

        return segment

    #MODES
    def setMode(self, mode):
        if self.mode <> mode:
            if mode == editModes.move:
                self.iface.mainWindow().statusBar().showMessage( self.tr('Hold down "Shift" before moving to ignore snapping.') )
            elif self.mode == editModes.move:
                self.iface.mainWindow().statusBar().clearMessage()

            self.mode = mode
            self.resetCursor()
        elif self.mode in [editModes.resize, editModes.skew]:
            self.resetCursor()

    def calcMode(self, point):
        if not self.rect:
            return editModes.standart
        else:
            if self.rectDist(point) < self.width():
                if self.brainySpin.isChecked():
                    return editModes.brainySpin
                mode = self.transformModeComboBox.itemData(self.transformModeComboBox.currentIndex())
                if mode <> editModes.none:
                    return mode

            if self.rect.contains(point):
                if self.brainySpin.isChecked():
                    return editModes.brainySpin
                return editModes.move
            else:
                return editModes.rotate

    def resetCursor(self):
        cursor = QCursor(Qt.ArrowCursor)

        if self.mode == editModes.standart:
            cursor = QCursor(Qt.CrossCursor)
        elif self.mode == editModes.move:
            cursor = QCursor(Qt.SizeAllCursor)
        elif self.mode == editModes.rotate:
            cursor = QCursor(QPixmap(":/plugins/smart_editing_tools/images/cursor_rotating.png"))
        elif self.mode == editModes.brainySpin:
            cursor = QCursor(QPixmap(["15 15 3 1",
                                      "      c None",
                                      ".     c #22CAFF",
                                      "+     c #000000",
                                      "      +++      ",
                                      "      +.+      ",
                                      "      +.+      ",
                                      "      +.+      ",
                                      "      +.+      ",
                                      "      +.+      ",
                                      "++++++   ++++++",
                                      "+..... + .....+",
                                      "++++++   ++++++",
                                      "      +.+      ",
                                      "      +.+      ",
                                      "      +.+      ",
                                      "      +.+      ",
                                      "      +.+      ",
                                      "      +++      "
                                      ]))
        else:
            mousePos = self.toMapCoordinates(self.canvas.mouseLastXY())
            cent = self.centerRect()
            segment = self.calcSegment(mousePos)
            sCent = QgsPoint( (segment[0].x()+segment[1].x())/2, (segment[0].y()+segment[1].y())/2 )
            dx = cent.x()-sCent.x()
            dy = cent.y()-sCent.y()
            orientation = Qt.Vertical if abs(dx) > abs(dy) else Qt.Horizontal

            if self.mode == editModes.resize:
                #check vertex
                vertex = self.calcVertex(mousePos)
                if vertex:
                    if tan(calcAngle(vertex, cent)) > 0:
                        cursor = QCursor(QPixmap(":/plugins/smart_editing_tools/images/cursor_resize_45.png"))
                    else:
                        cursor = QCursor(QPixmap(":/plugins/smart_editing_tools/images/cursor_resize_135.png"))
                else:
                    if orientation == Qt.Horizontal:
                        cursor = QCursor(QPixmap(":/plugins/smart_editing_tools/images/cursor_resize_vertical.png"))
                    elif orientation == Qt.Vertical:
                        cursor = QCursor(QPixmap(":/plugins/smart_editing_tools/images/cursor_resize_horizontal.png"))

            elif self.mode == editModes.skew:
                if orientation == Qt.Horizontal:
                    cursor = QCursor(QPixmap(":/plugins/smart_editing_tools/images/cursor_skew_horizontal.png"))
                elif orientation == Qt.Vertical:
                    cursor = QCursor(QPixmap(":/plugins/smart_editing_tools/images/cursor_skew_vertical.png"))

        self.canvas.setCursor(cursor)


    #RECT
    def refreshRect(self):
        rect = None
        for row in self.features:
            layer, fIds = row["layer"], row["fIds"]
            layerRect = None
            for feature in layer.getFeatures(QgsFeatureRequest().setFilterFids(fIds)):
                featureRect = feature.geometry().boundingBox()
                if layerRect is None:
                    layerRect = featureRect
                else:
                    layerRect.unionRect(featureRect)
            formatRect = QgsRectangle(self.toMapCoordinates(layer, QgsPoint(layerRect.xMinimum(),layerRect.yMinimum())),
                                      self.toMapCoordinates(layer, QgsPoint(layerRect.xMaximum(),layerRect.yMaximum())))
            if rect is None:
                rect = formatRect
            else:
                rect.unionRect(formatRect)

        if rect:
            self.setRect(QgsGeometry.fromRect(rect))
        else:
            self.setRect(None)

    def setRect(self,rect):
        self.rect = rect
        if self.rect:
            self.rbRect.setToGeometry(rect, QgsVectorLayer())
        else:
            self.rbRect.reset()

    def moveRect(self, dx, dy):
        rect = QgsGeometry(self.rect)
        for i in range(4):
            vertex = rect.vertexAt(i)
            rect.moveVertex(vertex.x()+dx,vertex.y()+dy,i)

        self.setRect(rect)

    def moveRbRect(self, dx, dy):
        rect = QgsGeometry(self.rect)
        for i in range(4):
            vertex = rect.vertexAt(i)
            rect.moveVertex(vertex.x()+dx,vertex.y()+dy,i)

        self.rbRect.setToGeometry(rect, QgsVectorLayer())

    def rotateRect(self, relPoint, alpha):
        rect = QgsGeometry(self.rect)
        for i in range(4):
            vertex = self.rect.vertexAt(i)
            vertex = self.rotatePoint(vertex, relPoint, alpha)
            rect.moveVertex(vertex.x(), vertex.y(), i)

        self.setRect(rect)

    def rotateRbRect(self, relPoint, alpha):
        rect = QgsGeometry(self.rect)
        for i in range(4):
            vertex = self.rect.vertexAt(i)
            vertex = self.rotatePoint(vertex, relPoint, alpha)
            rect.moveVertex(vertex.x(), vertex.y(), i)

        self.rbRect.setToGeometry(rect, QgsVectorLayer())

    def resizeRect(self, dx, dy):
        rect = QgsGeometry(self.rect)
        for i in range(4):
            vertex = rect.vertexAt(i)
            vertex = self.resizePoint(vertex, dx, dy)
            rect.moveVertex(vertex.x(),vertex.y(),i)

        self.setRect(rect)

    def resizeRbRect(self, dx, dy):
        rect = QgsGeometry(self.rect)
        for i in range(4):
            vertex = rect.vertexAt(i)
            vertex = self.resizePoint(vertex, dx, dy)
            rect.moveVertex(vertex.x(),vertex.y(),i)

        self.rbRect.setToGeometry(rect, QgsVectorLayer())

    def skewRect(self, alpha, beta, gamma):
        rect = QgsGeometry(self.rect)
        for i in range(4):
            vertex = rect.vertexAt(i)
            vertex = self.skewPoint(vertex, alpha, beta, gamma)
            rect.moveVertex(vertex.x(),vertex.y(),i)

        self.setRect(rect)

    def skewRbRect(self, alpha, beta, gamma):
        rect = QgsGeometry(self.rect)
        for i in range(4):
            vertex = rect.vertexAt(i)
            vertex = self.skewPoint(vertex, alpha, beta, gamma)
            rect.moveVertex(vertex.x(),vertex.y(),i)

        self.rbRect.setToGeometry(rect, QgsVectorLayer())

    def brainySpinRect(self, dx, dy, relPoint, alpha):
        rect = QgsGeometry(self.rect)
        for i in range(4):
            vertex = rect.vertexAt(i)
            vertex = self.brainySpinPoint(vertex, dx, dy, relPoint, alpha)
            rect.moveVertex(vertex.x(),vertex.y(),i)

        self.setRect(rect)

    def brainySpinRbRect(self, dx, dy, relPoint, alpha):
        rect = QgsGeometry(self.rect)
        for i in range(4):
            vertex = rect.vertexAt(i)
            vertex = self.brainySpinPoint(vertex, dx, dy, relPoint, alpha)
            rect.moveVertex(vertex.x(),vertex.y(),i)

        self.rbRect.setToGeometry(rect, QgsVectorLayer())

    def centerRect(self):
        A = self.rect.vertexAt(0)
        C = self.rect.vertexAt(2)
        return QgsPoint((A.x()+C.x())/2,(A.y()+C.y())/2)

    def rectDist(self, point):
        dist=None
        for i in range(4):
            Td = distancePS(point, [self.rect.vertexAt(i), self.rect.vertexAt(i+1)])
            if dist is None:
                dist = Td
            else:
                dist = min(dist,Td)

        return dist

    def prettyAngle(self, angle):
        return angle

    #FEATURES
    def updateFeatures(self, rect):
        li = self.iface.legendInterface()
        for layer in self.iface.editableLayers():
            if self.multiSelectionCheckBox.checkState() == Qt.Unchecked and self.canvas.currentLayer() <> layer:
                continue
            if not li.isLayerVisible(layer):
                continue
            selectRect = self.toLayerCoordinates(layer, rect)

            index = None
            for i in range(len(self.features)):
                if self.features[i]["layer"] == layer:
                    index = i
            if index is None:
                currentRow = {"layer": layer, "fIds": []}
            else:
                currentRow = self.features[index]

            fIds = currentRow["fIds"]
            for feature in layer.getFeatures(QgsFeatureRequest(selectRect)):
                if feature in fIds:
                    continue
                geom = feature.geometry()
                if not geom.intersects(selectRect):
                    continue
                fIds.append(feature.id())

            if index is None:
                if len(fIds)>0:
                    self.features.append({"layer": layer, "fIds": fIds})
            else:
                if len(fIds)>0:
                    self.features[index] = currentRow
                else:
                    del self.features[index]

    def iterateFeatures(self, pointChangeMethod):
        for row in self.features:
            layer, fIds = row["layer"], row["fIds"]
            layer.beginEditCommand("multiEdit")
            if layer.wkbType() == QGis.WKBPoint:
                for feature in layer.getFeatures(QgsFeatureRequest().setFilterFids(fIds)):
                    point = self.toMapCoordinates(layer, feature.geometry().asPoint())
                    point = self.toLayerCoordinates(layer, pointChangeMethod(point))
                    layer.moveVertex(point.x(), point.y(), feature.id(), 0)
            elif layer.wkbType() == QGis.WKBLineString:
                for feature in layer.getFeatures(QgsFeatureRequest().setFilterFids(fIds)):
                    polyline = feature.geometry().asPolyline()
                    for i in range(len(polyline)):
                        point = self.toMapCoordinates(layer, polyline[i])
                        point = self.toLayerCoordinates(layer, pointChangeMethod(point))
                        layer.moveVertex(point.x(), point.y(), feature.id(), i)
            elif layer.wkbType() == QGis.WKBPolygon:
                for feature in layer.getFeatures(QgsFeatureRequest().setFilterFids(fIds)):
                    polygon = feature.geometry().asPolygon()
                    i=0
                    for polygonling in polygon:
                        for vertex in polygonling:
                            point = self.toMapCoordinates(layer, vertex)
                            point = self.toLayerCoordinates(layer, pointChangeMethod(point))
                            layer.moveVertex(point.x(), point.y(), feature.id(), i)
                            i+=1
                #QGIS does not want to move multipoints
                """
            elif layer.wkbType() == QGis.WKBMultiPoint:
                for feature in layer.getFeatures(QgsFeatureRequest().setFilterFids(fIds)):
                    points = feature.geometry().asMultiPoint()
                    for i in range(len(points)):
                        point = self.toMapCoordinates(layer, points[i])
                        points[i] = self.toLayerCoordinates(layer, pointChangeMethod(point))
                        #point = self.toLayerCoordinates(layer, pointChangeMethod(point))
                        #layer.moveVertex(point.x(), point.y(), feature.id(), i)
                    #layer.changeGeometry(feature.id(), QgsGeometry.fromMultiPoint(points))
                    feature.setGeometry(QgsGeometry.fromMultiPoint(points))
                    layer.updateFeature(feature)
                """
            elif layer.wkbType() == QGis.WKBMultiLineString:
                for feature in layer.getFeatures(QgsFeatureRequest().setFilterFids(fIds)):
                    lines = feature.geometry().asMultiPolyline()
                    i=0
                    for line in lines:
                        for vertex in line:
                            point = self.toMapCoordinates(layer, vertex)
                            point = self.toLayerCoordinates(layer, pointChangeMethod(point))
                            layer.moveVertex(point.x(), point.y(), feature.id(), i)
                            i+=1
            elif layer.wkbType() == QGis.WKBMultiPolygon:
                for feature in layer.getFeatures(QgsFeatureRequest().setFilterFids(fIds)):
                    polygons = feature.geometry().asMultiPolygon()
                    i=0
                    for polygon in polygons:
                        for polygonling in polygon:
                            for vertex in polygonling:
                                point = self.toMapCoordinates(layer, vertex)
                                point = self.toLayerCoordinates(layer, pointChangeMethod(point))
                                layer.moveVertex(point.x(), point.y(), feature.id(), i)
                                i+=1
            else:
                dlg = QMessageBox()
                dlg.setText("Unknown geometry type: "+str(layer.wkbType())+".")
                dlg.exec_()

            layer.endEditCommand()

    def iterateRbFeatures(self, pointChangeMethod):
        self.rbFeatures.reset()

        for row in self.features:
            layer, fIds = row["layer"], row["fIds"]
            if layer.wkbType() == QGis.WKBPoint:
                for feature in layer.getFeatures(QgsFeatureRequest().setFilterFids(fIds)):
                    point = self.toMapCoordinates(layer, feature.geometry().asPoint())
                    point = self.toLayerCoordinates(layer, pointChangeMethod(point))
                    geom = QgsGeometry.fromPoint(point)
                    self.rbFeatures.addGeometry(geom, layer)
            elif layer.wkbType() == QGis.WKBLineString:
                for feature in layer.getFeatures(QgsFeatureRequest().setFilterFids(fIds)):
                    polyline = feature.geometry().asPolyline()
                    for i in range(len(polyline)):
                        point = self.toMapCoordinates(layer, polyline[i])
                        polyline[i] = self.toLayerCoordinates(layer, pointChangeMethod(point))
                    geom = QgsGeometry.fromPolyline(polyline)
                    self.rbFeatures.addGeometry(geom, layer)
            elif layer.wkbType() == QGis.WKBPolygon:
                for feature in layer.getFeatures(QgsFeatureRequest().setFilterFids(fIds)):
                    polygon = feature.geometry().asPolygon()
                    multipolygon = []
                    for polygonling in polygon:
                        for i in range(len(polygonling)):
                            point = self.toMapCoordinates(layer, polygonling[i])
                            polygonling[i] = self.toLayerCoordinates(layer, pointChangeMethod(point))
                        multipolygon.append([polygonling])
                    geom = QgsGeometry.fromMultiPolygon(multipolygon)
                    self.rbFeatures.addGeometry(geom, layer)
                """
            elif layer.wkbType() == QGis.WKBMultiPoint:
                for feature in layer.getFeatures(QgsFeatureRequest().setFilterFids(fIds)):
                    points = feature.geometry().asMultiPoint()
                    for i in range(len(points)):
                        point = self.toMapCoordinates(layer, points[i])
                        points[i] = self.toLayerCoordinates(layer, pointChangeMethod(point))
                    geom = QgsGeometry.fromMultiPoint(points)
                    self.rbFeatures.addGeometry(geom, layer)
                """
            elif layer.wkbType() == QGis.WKBMultiLineString:
                for feature in layer.getFeatures(QgsFeatureRequest().setFilterFids(fIds)):
                    lines = feature.geometry().asMultiPolyline()
                    for i in range(len(lines)):
                        for j in range(len(lines[i])):
                            point = self.toMapCoordinates(layer, lines[i][j])
                            lines[i][j] = self.toLayerCoordinates(layer, pointChangeMethod(point))
                    geom = QgsGeometry.fromMultiPolyline(lines)
                    self.rbFeatures.addGeometry(geom, layer)
            elif layer.wkbType() == QGis.WKBMultiPolygon:
                for feature in layer.getFeatures(QgsFeatureRequest().setFilterFids(fIds)):
                    polygons = feature.geometry().asMultiPolygon()
                    multipolygon = []
                    for polygon in polygons:
                        for polygonling in polygon:
                            for i in range(len(polygonling)):
                                point = self.toMapCoordinates(layer, polygonling[i])
                                polygonling[i] = self.toLayerCoordinates(layer, pointChangeMethod(point))
                            multipolygon.append([polygonling])
                    geom = QgsGeometry.fromMultiPolygon(multipolygon)
                    self.rbFeatures.addGeometry(geom, layer)

    #move
    def movePoint(self, point, dx, dy):
        return QgsPoint(point.x()+dx,point.y()+dy)

    def moveFeatures(self, dx, dy):
        function = lambda point: self.movePoint(point, dx, dy)
        self.iterateFeatures(function)

    def moveRbFeatures(self, dx, dy):
        function = lambda point: self.movePoint(point, dx, dy)
        self.iterateRbFeatures(function)

    #rotate
    def rotatePoint(self, point, relPoint, alpha):
        [point] = moveCoords(relPoint, [point])
        [point] = rotateCoords(alpha, [point])
        [point] = moveCoords(relPoint, [point], reverse=-1)
        return point

    def rotateFeatures(self, relPoint, alpha):
        function = lambda point: self.rotatePoint(point, relPoint, alpha)
        self.iterateFeatures(function)

    def rotateRbFeatures(self, relPoint, alpha):
        function = lambda point: self.rotatePoint(point, relPoint, alpha)
        self.iterateRbFeatures(function)

    #resize
    def resizePoint(self, point, dx, dy):
        for pair in self.segments:
            p0 = self.point
            p1 = QgsPoint( p0.x()+dx, p0.y()+dy )
            sSegment = pair["static"]
            s0, s1 = sSegment[0], sSegment[1]

            [point, p0, p1, s1] = moveCoords(s0, [point, p0, p1, s1])
            alpha = calcAngle(s1,QgsPoint(0,0))
            [point, p0, p1] = rotateCoords(-alpha, [point, p0, p1])

            point = QgsPoint( point.x(), point.y()*p1.y()/p0.y() )

            [point] = rotateCoords(alpha, [point])
            [point] = moveCoords(s0, [point], reverse=-1)

        return point

    def resizeFeatures(self, dx, dy):
        function = lambda point: self.resizePoint(point, dx, dy)
        self.iterateFeatures(function)

    def resizeRbFeatures(self, dx, dy):
        function = lambda point: self.resizePoint(point, dx, dy)
        self.iterateRbFeatures(function)

    #skew
    def skewPoint(self, point, alpha, beta, gamma):
        if tan(alpha) == 0:
            # this is not parallelogram
            return point

        pair = self.segments[0]
        sSegment = pair["static"]
        s0 = sSegment[0]
        p = point

        [p] = moveCoords(s0, [p])
        [p] = rotateCoords(-gamma, [p])

        projX = p.x() - p.y()/tan(alpha)
        newX = projX + p.y()/tan(beta)

        p = QgsPoint(newX, p.y())

        [p] = rotateCoords(gamma, [p])
        [p] = moveCoords(s0, [p], reverse=-1)

        return p

    def skewFeatures(self, alpha, beta, gamma):
        function = lambda point: self.skewPoint(point, alpha, beta, gamma)
        self.iterateFeatures(function)

    def skewRbFeatures(self, alpha, beta, gamma):
        function = lambda point: self.skewPoint(point, alpha, beta, gamma)
        self.iterateRbFeatures(function)

    #flip
    def flipPoint(self, point, line):
        A,B = line[0],line[1]
        alpha = calcAngle(A,B)

        [point] = moveCoords(B, [point])
        [point] = rotateCoords(-alpha, [point])
        point = QgsPoint(point.x(),-point.y())
        [point] = rotateCoords(alpha, [point])
        [point] = moveCoords(B, [point], reverse=-1)

        return point

    def flipFeatures(self, line):
        function = lambda point: self.flipPoint(point, line)
        self.iterateFeatures(function)

    def refreshRb(self):
        self.rbFeatures.reset()
        #Rubber band does not want to draw a polygons with rings. We have to draw rings as polygons.
        #There is not trouble if we do not fill them (brushStyle = Qt.NoBrush).
        for row in self.features:
            layer, fIds = row["layer"], row["fIds"]
            if layer.wkbType() == QGis.WKBPolygon:
                for feature in layer.getFeatures(QgsFeatureRequest().setFilterFids(fIds)):
                    polygon = feature.geometry().asPolygon()
                    multipolygon = []
                    for polygonling in polygon:
                        multipolygon.append([polygonling])
                    geom = QgsGeometry.fromMultiPolygon(multipolygon)
                    self.rbFeatures.addGeometry(geom, layer)
            elif layer.wkbType() == QGis.WKBMultiPolygon:
                for feature in layer.getFeatures(QgsFeatureRequest().setFilterFids(fIds)):
                    polygons = feature.geometry().asMultiPolygon()
                    multipolygon = []
                    for polygon in polygons:
                        for polygonling in polygon:
                            multipolygon.append([polygonling])
                    geom = QgsGeometry.fromMultiPolygon(multipolygon)
                    self.rbFeatures.addGeometry(geom, layer)
            else:
                for feature in layer.getFeatures(QgsFeatureRequest().setFilterFids(fIds)):
                    self.rbFeatures.addGeometry(feature.geometry(), layer)

    #brainy spin
    def brainySpinPoint(self, point, dx, dy, relPoint, alpha):
        point = QgsPoint(point.x()+dx,point.y()+dy)

        [point] = moveCoords(relPoint, [point])
        [point] = rotateCoords(alpha, [point])
        [point] = moveCoords(relPoint, [point], reverse=-1)
        return point

    def brainySpinFeatures(self, dx, dy, relPoint, alpha):
        function = lambda point: self.brainySpinPoint(point, dx, dy, relPoint, alpha)
        self.iterateFeatures(function)

    def brainySpinRbFeatures(self, dx, dy, relPoint, alpha):
        function = lambda point: self.brainySpinPoint(point, dx, dy, relPoint, alpha)
        self.iterateRbFeatures(function)

    #ACTIONS
    def attributesDlg(self):
        layer = self.canvas.currentLayer()
        if not (layer and layer.isEditable()):
            return

        for row in self.features:
            if row["layer"] == layer:
                dlg = MultiAttributeDialog(layer, self.iface.mainWindow())
                if not dlg.exec_():
                    del dlg
                    return

                attributes = dlg.attributes
                del dlg

                layer.beginEditCommand("multiEdit")

                count = 0
                for feature in layer.getFeatures(QgsFeatureRequest().setFilterFids(row["fIds"])):
                    for attribute in attributes:
                        feature.setAttribute(attribute["idx"], attribute["value"])

                    if layer.updateFeature(feature):
                        count+=1

                layer.endEditCommand()

                self.iface.mainWindow().statusBar().showMessage( str(count) + self.tr(" feature(s) updated.") )

                return

    def flipHorizontal(self):
        if not self.rect:
            return
        p0,p1,p2,p3 = self.rect.vertexAt(0),self.rect.vertexAt(1),self.rect.vertexAt(2),self.rect.vertexAt(3)
        line = [ QgsPoint( (p0.x()+p1.x())/2, (p0.y()+p1.y())/2 ), QgsPoint( (p3.x()+p2.x())/2, (p3.y()+p2.y())/2 ) ]
        self.flipFeatures(line)

        self.refreshRb()

        self.canvas.refresh()

    def flipVertical(self):
        if not self.rect:
            return
        p0,p1,p2,p3 = self.rect.vertexAt(0),self.rect.vertexAt(1),self.rect.vertexAt(2),self.rect.vertexAt(3)
        line = [ QgsPoint( (p0.x()+p3.x())/2, (p0.y()+p3.y())/2 ), QgsPoint( (p1.x()+p2.x())/2, (p1.y()+p2.y())/2 ) ]
        self.flipFeatures(line)

        self.refreshRb()

        self.canvas.refresh()

    def copy(self):
        self.buffer = []
        count = 0
        for row in self.features:
            layer = row["layer"]
            fIds = row["fIds"]
            features = []
            for feature in layer.getFeatures(QgsFeatureRequest().setFilterFids(fIds)):
                features.append(QgsFeature(feature))

            self.buffer.append({"layer": layer, "features": features})
            count+=len(features)

        self.iface.mainWindow().statusBar().showMessage( str(count) + self.tr(" feature(s) copied.") )

    def paste(self):
        count = 0
        for row in self.buffer:
            layer, features = row["layer"], row["features"]
            layer.beginEditCommand("paste")

            newFeatures = []
            for feature in features:
                f = QgsFeature(feature)
                idColumn = 0
                f.setAttribute(idColumn,layer.dataProvider().defaultValue(idColumn))
                newFeatures.append(f)

            layer.addFeatures(newFeatures, False)

            layer.endEditCommand()
            count+=len(features)

        #self.buffer = []
        self.canvas.refresh()

        self.iface.mainWindow().statusBar().showMessage( str(count) + self.tr(" feature(s) pasted.") )

    def saveEdits(self):
        if not self.question(self.tr("Save edits"), self.tr("Edits will be saved. Continue?")):
            return

        for row in self.features:
            layer = row["layer"]
            if layer.isEditable():
                layer.commitChanges()

        self.reset()

    def removeEdits(self):
        if not self.question(self.tr("Remove edits"), self.tr("Edits will be removed. Continue?")):
            return

        for row in self.features:
            layer = row["layer"]
            if layer.isEditable():
                layer.rollBack()

        self.reset()

    def question(self, title, text):
        return QMessageBox().question(QWidget(), title, text, QMessageBox.Ok, QMessageBox.Cancel) == QMessageBox.Ok


class editModes():
    none = 0
    standart = 1
    move = 2
    rotate = 3

    resize = 4
    skew = 5

    brainySpin = 6


class MultiAttributeDialog(QDialog):
    def __init__(self, layer, parent=None):
        super(MultiAttributeDialog,self).__init__(parent)
        self.layer = layer
        self.setWindowTitle(self.layer.name() + " - Multi-feature Attributes")
        self.attributes = []
        self.wrappers = []

        self.initDlg()

    def initDlg(self):
        formLayout = QFormLayout(self)

        for field in self.layer.pendingFields().toList():
            #The best bicycle I found in my mind
            idx = self.layer.fieldNameIndex( field.name() )
            if idx < 0:
                continue
            if not self.layer.fieldEditable(idx):
                continue

            displayName = self.layer.attributeDisplayName(idx)
            widgetType = self.layer.editorWidgetV2(idx)

            if widgetType == "Hidden":
                continue

            widgetConfig = self.layer.editorWidgetV2Config(idx)

            eww = QgsEditorWidgetRegistry.instance().create(widgetType, self.layer, idx, widgetConfig, None, self)
            if not eww:
                continue

            self.wrappers.append(eww)

            widget = eww.widget()

            checkBox = QCheckBox()

            hbox = QHBoxLayout()
            hbox.addWidget(checkBox)
            hbox.addWidget(widget)

            formLayout.addRow(displayName, hbox)

            widget.setEnabled(checkBox.isChecked())
            checkBox.stateChanged.connect(widget.setEnabled)

        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.validate)
        buttonBox.rejected.connect(self.reject)

        formLayout.addRow(buttonBox)

    def validate(self):
        self.attributes = []
        for eww in self.wrappers:
            if eww.widget().isEnabled():
                self.attributes.append( {"idx": eww.fieldIdx(), "value": eww.value()} )

        self.accept()