# -*- coding: utf-8 -*-
from common import *

def rbInit(canvas, color, width=1, lineStyle = Qt.SolidLine, brushStyle=Qt.NoBrush):
    rb = QgsRubberBand(canvas)
    rb.setColor(color)
    rb.setWidth(width)
    rb.setLineStyle(lineStyle)
    rb.setBrushStyle(brushStyle)
    return rb

class MultiEditingTool(QgsMapTool):
    def __init__(self, iface):
        self.iface = iface
        self.canvas = self.iface.mapCanvas()
        QgsMapTool.__init__(self,self.canvas)

        self.mode = None
        self.ctrl = None

        #RECT
        self.rect = None
        self.point = None
        self.rbRect = rbInit(self.canvas, QColor(255,235,206), lineStyle=Qt.DashLine, brushStyle=Qt.SolidPattern)
        self.rbRect.setBorderColor(QColor(0,0,0))
        self.rbRect.setOpacity(0.3)

        #SELECTED FEATURES
        self.features = []
        self.rbFeatures = rbInit(self.canvas, QColor(187,255,128), width=3, brushStyle=Qt.SolidPattern)
        self.rbRect.setOpacity(0.3)

        self.waiting = False

    def isTransient(self):
        return False

    def isEditTool(self):
        return True

    def activate(self):
        self.mode = editModes.standart
        self.resetCursor()

    def deactivate(self):
        self.reset()

    def reset(self):
        self.setRect(None)
        self.point = None

        self.features = []
        self.rbFeatures.reset()

        self.setMode(editModes.standart)


    #EVENTS
    def keyPressEvent(self, keyEvent):
        if keyEvent.key() == Qt.Key_Control:
            self.ctrl = True
            self.setMode(editModes.standart)

    def keyReleaseEvent(self, keyEvent):
        if keyEvent.key() == Qt.Key_Control:
            self.ctrl = False
            self.setMode(self.calcMode(self.toMapCoordinates(self.canvas.mouseLastXY())))

    def canvasPressEvent(self, mouseEvent):
        while self.waiting:
            pass
        self.waiting = True

        if mouseEvent.button() == 1:
            self.point = self.toMapCoordinates(mouseEvent.pos())

        elif mouseEvent.button() == 2:
            self.reset()

        self.waiting = False

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
                dx = mapPos.x()-self.point.x()
                dy = mapPos.y()-self.point.y()
                rect = QgsRectangle(QgsPoint(self.rect.xMinimum()+dx,self.rect.yMinimum()+dy),
                                    QgsPoint(self.rect.xMaximum()+dx,self.rect.yMaximum()+dy))
                self.rbRect.setToGeometry(QgsGeometry.fromRect(rect),QgsVectorLayer())

                self.moveRbFeatures(dx,dy)

            elif self.mode == editModes.rotate:
                relPoint = self.rect.center()
                alpha = calcAngle(mapPos,relPoint)-calcAngle(self.point, relPoint)
                self.rotateRbFeatures(relPoint, alpha)

        else:
            self.setMode(self.calcMode(mapPos))

        self.waiting = False

    def canvasReleaseEvent(self, mouseEvent):
        while self.waiting:
            pass
        self.waiting = True

        mapPos = self.toMapCoordinates(mouseEvent.pos())
        if mouseEvent.button() == 1:
            if self.mode == editModes.standart:
                if self.point and self.point <> mapPos:
                    self.setRect(QgsRectangle(self.point, mapPos))
                    self.updateFeatures()
                else:
                    self.setRect(None)
                if not self.ctrl:
                    self.setMode(self.calcMode(mapPos))

            elif self.mode == editModes.move:
                if self.point <> mapPos:
                    dx = mapPos.x()-self.point.x()
                    dy = mapPos.y()-self.point.y()
                    self.moveRect(dx, dy)

                    self.moveFeatures(dx,dy)

                    self.canvas.refresh()

            elif self.mode == editModes.rotate:
                if self.point <> mapPos:
                    relPoint = self.rect.center()
                    alpha = calcAngle(mapPos,relPoint)-calcAngle(self.point, relPoint)

                    self.rotateFeatures(relPoint, alpha)

                    self.canvas.refresh()

        self.point = None

        self.waiting = False


    #MODES
    def setMode(self, mode):
        if self.mode <> mode:
            self.mode = mode
            self.resetCursor()

    def calcMode(self, point):
        if not self.rect:
            return editModes.standart
        else:
            if self.rect.contains(point):
                return editModes.move
            else:
                return editModes.rotate

    def resetCursor(self):
        if self.mode == editModes.standart:
            cursor = QCursor(Qt.CrossCursor)
        elif self.mode == editModes.move:
            cursor = QCursor(Qt.SizeAllCursor)
        elif self.mode == editModes.rotate:
            cursor = QCursor(QPixmap(":/plugins/qgis-mapvlru-tools/tools/cursor_rotating.png"))
        else:
            cursor = QCursor(Qt.ArrowCursor)
        self.canvas.setCursor(cursor)


    #RECT
    def setRect(self,rect):
        self.rect = rect
        if self.rect:
            self.rbRect.setToGeometry(QgsGeometry.fromRect(self.rect), QgsVectorLayer())
        else:
            self.rbRect.reset()

    def moveRect(self, dx, dy):
        rect = QgsRectangle(QgsPoint(self.rect.xMinimum()+dx,self.rect.yMinimum()+dy),
                            QgsPoint(self.rect.xMaximum()+dx,self.rect.yMaximum()+dy))
        self.setRect(rect)


    #FEATURES
    def updateFeatures(self):
        li = self.iface.legendInterface()
        for layer in self.iface.editableLayers():
            if not li.isLayerVisible(layer):
                continue
            rect = self.toLayerCoordinates(layer, self.rect)

            fIds = []
            for feature in layer.getFeatures(QgsFeatureRequest(rect)):
                if feature in self.features:
                    continue
                geom = feature.geometry()
                if not geom.intersects(rect):
                    continue
                fIds.append(feature.id())
                #if layer.geometryType() == 0: this is wrong
                    #self.rbFeatures.addPoint(self.toMapCoordinates(layer,geom.asPoint()))
                #else:
                self.rbFeatures.addGeometry(geom, layer)
            if len(fIds)>0:
                self.features.append({"layer": layer, "fIds": fIds})

    def moveFeatures(self, dx, dy):
        for row in self.features:
            layer, fIds = row["layer"], row["fIds"]
            layer.beginEditCommand("move")
            if layer.geometryType() == 0:
                for feature in layer.getFeatures(QgsFeatureRequest().setFilterFids(fIds)):
                    point = self.toMapCoordinates(layer, feature.geometry().asPoint())
                    point = self.toLayerCoordinates(layer, QgsPoint(point.x()+dx,point.y()+dy))
                    layer.moveVertex(point.x(), point.y(), feature.id(), 0)
            elif layer.geometryType() == 1:
                for feature in layer.getFeatures(QgsFeatureRequest().setFilterFids(fIds)):
                    polyline = feature.geometry().asPolyline()
                    for i in range(len(polyline)):
                        point = self.toMapCoordinates(layer, polyline[i])
                        point = self.toLayerCoordinates(layer, QgsPoint(point.x()+dx,point.y()+dy))
                        layer.moveVertex(point.x(), point.y(), feature.id(), i)
            elif layer.geometryType() == 2:
                for feature in layer.getFeatures(QgsFeatureRequest().setFilterFids(fIds)):
                    polygon = feature.geometry().asPolygon()
                    for i in range(len(polygon[0])):
                        point = self.toMapCoordinates(layer, polygon[0][i])
                        point = self.toLayerCoordinates(layer, QgsPoint(point.x()+dx,point.y()+dy))
                        layer.moveVertex(point.x(), point.y(), feature.id(), i)
            else:
                dlg = QMessageBox()
                dlg.setText("Unknown geometry type: "+str(layer.geometryType())+".")
                dlg.exec_()

            layer.endEditCommand()

    def moveRbFeatures(self, dx, dy):
        self.rbFeatures.reset()

        for row in self.features:
            layer, fIds = row["layer"], row["fIds"]
            if layer.geometryType() == 0:
                for feature in layer.getFeatures(QgsFeatureRequest().setFilterFids(fIds)):
                    point = self.toMapCoordinates(layer, feature.geometry().asPoint())
                    point = self.toLayerCoordinates(layer, QgsPoint(point.x()+dx,point.y()+dy))
                    geom = QgsGeometry.fromPoint(point)
                    self.rbFeatures.addGeometry(geom, layer)
            elif layer.geometryType() == 1:
                for feature in layer.getFeatures(QgsFeatureRequest().setFilterFids(fIds)):
                    polyline = feature.geometry().asPolyline()
                    for i in range(len(polyline)):
                        point = self.toMapCoordinates(layer, polyline[i])
                        polyline[i] = self.toLayerCoordinates(layer, QgsPoint(point.x()+dx,point.y()+dy))
                    geom = QgsGeometry.fromPolyline(polyline)
                    self.rbFeatures.addGeometry(geom, layer)
            elif layer.geometryType() == 2:
                for feature in layer.getFeatures(QgsFeatureRequest().setFilterFids(fIds)):
                    polygon = feature.geometry().asPolygon()
                    for i in range(len(polygon[0])):
                        point = self.toMapCoordinates(layer, polygon[0][i])
                        polygon[0][i] = self.toLayerCoordinates(layer, QgsPoint(point.x()+dx,point.y()+dy))
                    geom = QgsGeometry.fromPolygon(polygon)
                    self.rbFeatures.addGeometry(geom, layer)

    def rotatePoint(self, point, relPoint, alpha):
        [point] = moveCoords(relPoint, [point])
        [point] = rotateCoords(alpha, [point])
        [point] = moveCoords(relPoint, [point], reverse=-1)
        return point

    def rotateFeatures(self, relPoint, alpha):
        for row in self.features:
            layer, fIds = row["layer"], row["fIds"]
            layer.beginEditCommand("move")
            if layer.geometryType() == 0:
                for feature in layer.getFeatures(QgsFeatureRequest().setFilterFids(fIds)):
                    point = self.toMapCoordinates(layer, feature.geometry().asPoint())
                    point = self.toLayerCoordinates(layer, self.rotatePoint(point, relPoint, alpha))
                    layer.moveVertex(point.x(), point.y(), feature.id(), 0)
            elif layer.geometryType() == 1:
                for feature in layer.getFeatures(QgsFeatureRequest().setFilterFids(fIds)):
                    polyline = feature.geometry().asPolyline()
                    for i in range(len(polyline)):
                        point = self.toMapCoordinates(layer, polyline[i])
                        point = self.toLayerCoordinates(layer, self.rotatePoint(point, relPoint, alpha))
                        layer.moveVertex(point.x(), point.y(), feature.id(), i)
            elif layer.geometryType() == 2:
                for feature in layer.getFeatures(QgsFeatureRequest().setFilterFids(fIds)):
                    polygon = feature.geometry().asPolygon()
                    for i in range(len(polygon[0])):
                        point = self.toMapCoordinates(layer, polygon[0][i])
                        point = self.toLayerCoordinates(layer, self.rotatePoint(point, relPoint, alpha))
                        layer.moveVertex(point.x(), point.y(), feature.id(), i)
            else:
                dlg = QMessageBox()
                dlg.setText("Unknown geometry type: "+str(layer.geometryType())+".")
                dlg.exec_()

            layer.endEditCommand()

    def rotateRbFeatures(self, relPoint, alpha):
        self.rbFeatures.reset()

        for row in self.features:
            layer, fIds = row["layer"], row["fIds"]
            if layer.geometryType() == 0:
                for feature in layer.getFeatures(QgsFeatureRequest().setFilterFids(fIds)):
                    point = self.toMapCoordinates(layer, feature.geometry().asPoint())
                    point = self.toLayerCoordinates(layer, self.rotatePoint(point, relPoint, alpha))
                    geom = QgsGeometry.fromPoint(point)
                    self.rbFeatures.addGeometry(geom, layer)
            elif layer.geometryType() == 1:
                for feature in layer.getFeatures(QgsFeatureRequest().setFilterFids(fIds)):
                    polyline = feature.geometry().asPolyline()
                    for i in range(len(polyline)):
                        point = self.toMapCoordinates(layer, polyline[i])
                        polyline[i] = self.toLayerCoordinates(layer, self.rotatePoint(point, relPoint, alpha))
                    geom = QgsGeometry.fromPolyline(polyline)
                    self.rbFeatures.addGeometry(geom, layer)
            elif layer.geometryType() == 2:
                for feature in layer.getFeatures(QgsFeatureRequest().setFilterFids(fIds)):
                    polygon = feature.geometry().asPolygon()
                    for i in range(len(polygon[0])):
                        point = self.toMapCoordinates(layer, polygon[0][i])
                        polygon[0][i] = self.toLayerCoordinates(layer, self.rotatePoint(point, relPoint, alpha))
                    geom = QgsGeometry.fromPolygon(polygon)
                    self.rbFeatures.addGeometry(geom, layer)


class editModes():
    standart = 1
    move = 2
    rotate = 3
