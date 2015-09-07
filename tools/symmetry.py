# -*- coding: utf-8 -*-

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *
from math import *
from common import *

colorNoSymmetry = QColor(194, 255, 236)
colorSymmetry = QColor(160,189,255)
colorSymmetryLine = QColor(35,232,73)

class SymmetryTool(QgsMapTool):
    def __init__(self, iface):
        self.iface = iface
        self.canvas = self.iface.mapCanvas()
        QgsMapTool.__init__(self,self.canvas)
        self.layer = None
        self.feature = None
        self.symmetryLines = []
        self.selectedLine = None

        self.rb = rbInit(self.canvas, colorNoSymmetry, width=2, lineStyle=Qt.SolidLine)
        self.rbSL = rbInit(self.canvas, colorSymmetryLine, width=1, lineStyle=Qt.DashLine)

        self.mClicked = None

        self.tolerance = 0.0001

        self.cursor = QCursor(QPixmap(["19 19 3 1",
                                      "      c None",
                                      ".     c #4B126B",
                                      "+     c #1A90C9",
                                      "+                 +",
                                      " +               + ",
                                      "  +      .      +  ",
                                      "   +     .     +   ",
                                      "    +    .    +    ",
                                      "     +   .   +     ",
                                      "      +  .  +      ",
                                      "       + . +       ",
                                      "        +.+        ",
                                      "  .......+.......  ",
                                      "        +.+        ",
                                      "       + . +       ",
                                      "      +  .  +      ",
                                      "     +   .   +     ",
                                      "    +    .    +    ",
                                      "   +     .     +   ",
                                      "  +      .      +  ",
                                      " +               + ",
                                      "+                 +"]))


    def isZoomTool(self):
        return False

    def isTransient(self):
        return False

    def isEditTool(self):
        return True

    def activate(self):
        self.layer = self.canvas.currentLayer()
        self.canvas.setCursor(self.cursor)
        self.mClicked = None
        self.reset()

    def deactivate(self):
        self.reset()

    def canvasPressEvent(self,mouseEvent):
        mapPos = self.toMapCoordinates(mouseEvent.pos())
        if mouseEvent.button() == Qt.LeftButton:
            self.mClicked = True
            self.updateSelectedLine(mapPos)

    def canvasMoveEvent(self,mouseEvent):
        mapPos = self.toMapCoordinates(mouseEvent.pos())
        if self.mClicked:
            self.updateSelectedLine(mapPos)

        else:
            feature = self.findFeautre(self.toLayerCoordinates(self.layer, mouseEvent.pos()))
            id1 = None if self.feature is None else self.feature.id()
            id2 = None if feature is None else feature.id()
            if id1 <> id2:
                self.updateFeature(feature)

    def canvasReleaseEvent(self,mouseEvent):
        if mouseEvent.button() == Qt.LeftButton:
            self.mClicked = False
            if self.selectedLine:
                self.layer.beginEditCommand('symmetry')

                angle = -calcAngle(self.selectedLine[0], self.selectedLine[1])
                geometry = self.feature.geometry()
                if geometry.wkbType() == QGis.WKBLineString:
                    polyline = convertToMapCoordinates(self, self.layer, geometry.asPolyline())
                    point = centerGeom(polyline)
                    for i in range(len(polyline)):
                        vertex = polyline[i]

                        [vertex] = moveCoords(point, [vertex])
                        [vertex] = rotateCoords(angle, [vertex])
                        [vertex] = moveCoords(point, [vertex], reverse=-1)
                        vertex = self.toLayerCoordinates(self.layer, vertex)

                        self.layer.moveVertex(vertex.x(), vertex.y(), self.feature.id(), i)

                elif geometry.wkbType() == QGis.WKBPolygon:
                    polygon = convertToMapCoordinates(self, self.layer, geometry.asPolygon()[0])
                    point = centerGeom(polygon[:-1])
                    for i in range(len(polygon)):
                        vertex = polygon[i]

                        [vertex] = moveCoords(point, [vertex])
                        [vertex] = rotateCoords(angle, [vertex])
                        [vertex] = moveCoords(point, [vertex], reverse=-1)
                        vertex = self.toLayerCoordinates(self.layer, vertex)

                        self.layer.moveVertex(vertex.x(), vertex.y(), self.feature.id(), i)

                self.layer.endEditCommand()
                self.reset()
                self.canvas.refresh()

    def reset(self):
        self.rb.reset()
        self.rbSL.reset()
        self.feature = None
        self.symmetryLines = []
        self.selectedLine = None


    def width(self):
        return self.iface.mapCanvas().mapUnitsPerPixel()*10


    def findFeautre(self, layerPoint):
        width = self.width()
        rect = QgsRectangle(QgsPoint(layerPoint.x()+width,layerPoint.y()+width),
                            QgsPoint(layerPoint.x()-width,layerPoint.y()-width))
        featureIt = self.layer.getFeatures(QgsFeatureRequest(rect))

        if self.layer.geometryType() == QGis.Line:
            for feature in featureIt:
                polyline = feature.geometry().asPolyline()
                if len(polyline) > 1:
                    for i in range(len(polyline)-1):
                        segment = [ polyline[i], polyline[i+1] ]
                        if distancePS(layerPoint,segment) < width:
                            return feature

        elif self.layer.geometryType() == QGis.Polygon:
            for feature in featureIt:
                if feature.geometry().contains(layerPoint):
                    if len(feature.geometry().asPolygon()) == 1:
                        return feature

        return None

    def updateFeature(self, feature):
        self.feature = feature
        self.updateSymmetryLines()
        if self.feature:
            self.rb.setToGeometry(self.feature.geometry(), self.layer)
        else:
            self.rb.reset()

    def updateSymmetryLines(self):
        if self.feature:
            self.symmetryLines = self.findSymmetryLines(self.feature.geometry())
        else:
            self.symmetryLines = []

        if len(self.symmetryLines) == 0:
            self.rbSL.reset()
        else:
            for line in self.symmetryLines:
                self.rbSL.addGeometry(QgsGeometry.fromPolyline(line), self.layer)

    def findSymmetryLines(self, geometry):
        lines = []
        #1. Вычисляем точку и угол предположительной линии симметрии
        #2. Вычисляем пары точек, которые нужно проверить на симметричность
        #3. Проверяем пары на симметричность (антисимметричность) и записываем линию симметрии в массив

        if geometry.wkbType() == QGis.WKBLineString:
            polyline = convertToMapCoordinates(self, self.layer, geometry.asPolyline())
            length = len(polyline)

            even = length%2 == 0
            if even:
                idx = length/2 - 1
                segment = [ polyline[idx], polyline[idx+1] ]

                point = centerGeom(segment)
                angle = -calcAngle(segment[0], segment[1])
                pairs = [ [polyline[i], polyline[-(i+1)]] for i in range(length/2)]
            else:
                idx = (length-1)/2

                point = polyline[idx]
                angle = -calcAngle(polyline[idx-1], polyline[idx+1])
                pairs = [ [polyline[i], polyline[-(i+1)]] for i in range((length-1)/2)]

            line = self.symmetryLine(point, angle, pairs)
            if not line:
                return []
            else:
                lines.append(line)

        elif geometry.wkbType() == QGis.WKBPolygon:
            polygon = convertToMapCoordinates(self, self.layer, geometry.asPolygon()[0][:-1])
            length = len(polygon)

            even = length%2 == 0
            if even:
                idx = length/2 - 1
                for k in range(length/2):
                    segment = [ polygon[idx], polygon[idx+1] ]

                    point = centerGeom(segment)
                    angle = -calcAngle(segment[0], segment[1])
                    pairs = [ [polygon[i], polygon[-(i+1)]] for i in range(length/2)]

                    line = self.symmetryLine(point, angle, pairs)
                    if line:
                        lines.append(line)

                    fullPolygon = [ polygon[-1] ] + polygon
                    point = fullPolygon[idx+1]
                    angle = -calcAngle(fullPolygon[idx], fullPolygon[idx+2])
                    pairs = [ [fullPolygon[i], fullPolygon[-(i+1)]] for i in range((length-1)/2)]

                    line = self.symmetryLine(point, angle, pairs)
                    if line:
                        lines.append(line)

                    polygon = [ polygon[-1] ] + polygon[:-1]

            else:
                idx = (length-1)/2
                for k in range(length):
                    point = polygon[idx]
                    angle = -calcAngle(polygon[idx-1], polygon[idx+1])
                    pairs = [ [polygon[i], polygon[-(i+1)]] for i in range((length-1)/2)]

                    line = self.symmetryLine(point, angle, pairs)
                    if line:
                        lines.append(line)

                    polygon = [ polygon[-1] ] + polygon[:-1]

        return lines

    def symmetryLine(self, point, angle, pairs):
        ys = [0]
        for pair in pairs:
            pair = moveCoords(point, pair)
            pair = rotateCoords(angle, pair)
            if abs(pair[0].y() - pair[1].y()) < self.tolerance and \
               abs(pair[0].x() + pair[1].x()) < self.tolerance:
                   ys.append(pair[0].y())
            else:
                return None

        line = [ QgsPoint(0, max(ys)), QgsPoint(0, min(ys)) ]
        line = rotateCoords(-angle, line)
        line = moveCoords(point, line, reverse=-1)

        return line

    def updateSelectedLine(self, mapPos):
        l = None
        d = self.width()
        for line in self.symmetryLines:
            dist = distancePS(mapPos, line[:])
            if dist < d:
                d = dist
                l = line

        if self.selectedLine <> l:
            self.selectedLine = l
            if self.selectedLine:
                angle = -calcAngle(self.selectedLine[0], self.selectedLine[1])

                geometry = self.feature.geometry()
                if geometry.wkbType() == QGis.WKBLineString:
                    polyline = convertToMapCoordinates(self, self.layer, geometry.asPolyline())
                    point = centerGeom(polyline)

                    polyline = moveCoords(point, polyline)
                    polyline = rotateCoords(angle, polyline)
                    polyline = moveCoords(point, polyline, reverse=-1)

                    self.rb.setToGeometry(QgsGeometry.fromPolyline(polyline), self.layer)

                elif geometry.wkbType() == QGis.WKBPolygon:
                    polygon = convertToMapCoordinates(self, self.layer, geometry.asPolygon()[0][:-1])
                    point = centerGeom(polygon)

                    polygon = moveCoords(point, polygon)
                    polygon = rotateCoords(angle, polygon)
                    polygon = moveCoords(point, polygon, reverse=-1)

                    self.rb.setToGeometry(QgsGeometry.fromPolygon([polygon]), self.layer)

            else:
                self.selectedLine = None
                self.rb.setToGeometry(self.feature.geometry(), self.layer)