# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Smart_editing_tools
                                 A QGIS plugin


                              -------------------
        begin                : 2015-04-23
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

# List comprehensions in canvasMoveEvent functions are

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *
from math import *

from common import *

class SmartAngleTool(QgsMapTool):
    def __init__(self, iface):
        self.iface = iface
        self.canvas = self.iface.mapCanvas()
        QgsMapTool.__init__(self,self.canvas)
        self.geometryType = -1
        self.nbPoints = 0

        self.rb = self.rbInit(QColor(22,139,136))
        self.rb.setBrushStyle(Qt.Dense7Pattern)
        self.rb.setFillColor(QColor(192,168,70))

        self.PLArb = self.rbInit(QColor(255,0,0), Qt.DashLine)

        self.SADrb = self.rbInit(QColor(0,0,255), Qt.DashLine)

        self.snapRb = self.rbInit(QColor(0,255,0),width=2)

        self.points = []
        self.length = 0
        self.mShift = None
        self.TAnb = 8 # ways to click with Shift
        self.cursor = QCursor(QPixmap(["16 16 3 1",
                                      "      c None",
                                      ".     c #4B126B",
                                      "+     c #1A90C9",
                                      "                ",
                                      "        .       ",
                                      "       +.+      ",
                                      "     +.....+    ",
                                      "    +.     .+   ",
                                      "   +.   .   .+  ",
                                      "  +.    .    .+ ",
                                      "  +.    .    .+ ",
                                      " ... ...+... ...",
                                      "  +.    .    .+ ",
                                      "  +.    .    .+ ",
                                      "   +.   .   .+  ",
                                      "    +.     .+   ",
                                      "     +.....+    ",
                                      "       +.+      ",
                                      "        .       "]))

        self.snapper = None


    def isZoomTool(self):
        return False

    def isTransient(self):
        return False

    def isEditTool(self):
        return True

    def activate(self):
        self.canvas.setCursor(self.cursor)
        self.updateSnapper()
        self.canvas.layersChanged.connect(self.updateSnapper)
        self.canvas.scaleChanged.connect(self.updateSnapper)
        QgsProject.instance().readProject.connect(self.updateSnapper)
        QgsProject.instance().snapSettingsChanged.connect(self.updateSnapper)

    def deactivate(self):
        self.nbPoints = 0
        self.points = []
        self.rb.reset()
        self.PLArb.reset()
        self.SADrb.reset()
        self.snapRb.reset()

        self.canvas.layersChanged.disconnect(self.updateSnapper)
        self.canvas.scaleChanged.disconnect(self.updateSnapper)
        QgsProject.instance().readProject.disconnect(self.updateSnapper)
        QgsProject.instance().snapSettingsChanged.disconnect(self.updateSnapper)

    def keyPressEvent(self,  event):
        if event.key() == Qt.Key_Shift:
            self.mShift = True
        if event.key() == Qt.Key_Backspace and self.nbPoints>0:
            self.points.pop()
            self.nbPoints-=1
            if self.geometryType == 1 or self.nbPoints == 1:
                self.rb.setToGeometry(QgsGeometry.fromPolyline(self.points), None)
            else:
                self.rb.setToGeometry(QgsGeometry.fromPolygon([self.points]), None)
            event.ignore()

    def keyReleaseEvent(self,  event):
        if event.key() == Qt.Key_Shift:
            self.mShift = False
        if event.key() == Qt.Key_Escape:
            self.nbPoints = 0
            self.points = []
            self.rb.reset()
            self.PLArb.reset()
            self.SADrb.reset()

    def canvasPressEvent(self,event):
        if event.button() == 1:
            layer = self.canvas.currentLayer()

            point = self.calcCurrPoint(event.pos())
            pointMap = self.toMapCoordinates(layer, point)
            if self.nbPoints > 0:
                if pointMap == self.points[self.nbPoints-1] or self.crossCheck(pointMap):
                    return
            self.points.append(pointMap)
            self.nbPoints += 1
        if event.button() == 2:
            self.geometryType = self.canvas.currentLayer().geometryType()
            if self.nbPoints > self.geometryType:
                if self.geometryType == 1:
                    geom = QgsGeometry.fromPolyline(self.points)
                else:
                    geom = QgsGeometry.fromPolygon([self.points])
                self.nbPoints = 0
                self.points = []
                self.createFeature(geom)
                self.rb.reset()
                self.PLArb.reset()
                self.SADrb.reset()
            else:
                self.nbPoints = 0
                self.points = []
                self.rb.reset()
                self.PLArb.reset()
                self.SADrb.reset()

    def canvasMoveEvent(self,event):
        currpoint = self.calcCurrPoint(event.pos())
        layer = self.canvas.currentLayer()
        if layer <> None and layer.type():
            self.geometryType = layer.geometryType()
        else: self.geometryType = -1
        if self.geometryType == 1 or self.nbPoints == 1:
            self.rb.setToGeometry(QgsGeometry.fromPolyline(self.points+[currpoint]), layer)
        else:
            self.rb.setToGeometry(QgsGeometry.fromPolygon([self.points+[currpoint]]), layer)


    def createFeature(self, geom):
        settings = QSettings()
        mc = self.canvas
        layer = mc.currentLayer()
        renderer = mc.mapSettings()
        layerCRSSrsid = layer.crs().srsid()
        projectCRSSrsid = renderer.destinationCrs().srsid()
        provider = layer.dataProvider()
        f = QgsFeature()

        #On the Fly reprojection.
        if layerCRSSrsid != projectCRSSrsid:
            #Popov: If wrong CRS - error
            geom.transform(QgsCoordinateTransform(projectCRSSrsid, layerCRSSrsid))

        # Line or Polygon
        if layer.geometryType() == 2:
            f.setGeometry(geom)
        else:
            f.setGeometry(geom.convertToType(1, False))

        # add attribute fields to feature
        fields = layer.pendingFields()

        # vector api change update
        f.initAttributes(fields.count())
        for i in range(fields.count()):
            f.setAttribute(i,provider.defaultValue(i))

        disable_attributes = settings.value( "/qgis/digitizing/disable_enter_attribute_values_dialog", False, type=bool)

        if not disable_attributes:
            dlg = QgsAttributeDialog(layer, f, False)
            dlg.setIsAddDialog(True)
            dlg.dialog().exec_()
        """
        if disable_attributes:
            cancel = 1
        else:
            dlg = QgsAttributeDialog(layer, f, False)
            dlg.setIsAddDialog(True)
            if not dlg.dialog().exec_():
                cancel = 0
            else:
                layer.destroyEditCommand()
                cancel = 1

        if cancel == 1:
            f.setAttributes(dlg.feature().attributes())
            layer.addFeature(f)
            layer.endEditCommand()
        """

        mc.refresh()


    def calcCurrPoint(self,eventPos):
        snapPoint, snapSegment = self._toMapSnap(eventPos)
        if snapPoint is not None:
            currpoint = QgsPoint(self.toMapCoordinates(self.canvas.currentLayer(),snapPoint))
            self.drawSnapAccessory(currpoint,distance(currpoint,self.toMapCoordinates(eventPos)))
            return currpoint
        elif snapSegment is not None:
            currpoint = snapSegment[0]
            self.drawSnapAccessory(currpoint,distance(currpoint,self.toMapCoordinates(eventPos)))
            return currpoint
        else:
            self.snapRb.reset()

        currpoint = self.toMapCoordinates(eventPos)
        shiftPoint = None
        PLApoint = None

        if self.nbPoints > 1:
            alpha = self.lastAngle(currpoint)
            beta = self.nearestAngle(alpha)
            if abs(beta-alpha) < 2*pi/self.TAnb/10:
                PLApoint = self.calcPLApoint(currpoint, beta)
                if distance(PLApoint,currpoint) > self.canvas.mapUnitsPerPixel()*5: PLApoint = None

        if self.mShift:
            if self.nbPoints > 1:
                shiftPoint = self.calcShiftPoint(currpoint, self.points[self.nbPoints-1], self.points[self.nbPoints-2])
            elif self.nbPoints==1:
                shiftPoint = self.calcShiftPoint(currpoint, self.points[0], QgsPoint(self.points[0].x()+1,self.points[0].y()))

        if PLApoint and shiftPoint:
            point = self.crossPoint(self.points[0], PLApoint, self.points[self.nbPoints-1], shiftPoint)
            if point:
                currpoint = point
        elif shiftPoint:
            currpoint = shiftPoint
        elif PLApoint:
            currpoint = PLApoint

        if PLApoint:
            self.PLArb.setToGeometry(QgsGeometry.fromPolyline([self.points[0],currpoint]), self.canvas.currentLayer())
        elif self.PLArb:
            self.PLArb.reset()
        if shiftPoint:
            self.SADrb.setToGeometry(QgsGeometry.fromPolyline([self.points[self.nbPoints-1],currpoint]), self.canvas.currentLayer())
        elif self.SADrb:
            self.SADrb.reset()

        return currpoint


    def drawSnapAccessory(self,currpoint,r):
        self.snapRb.setToGeometry(QgsGeometry.fromPolyline([QgsPoint(currpoint.x()+r,currpoint.y()),
                                                                QgsPoint(currpoint.x(),currpoint.y()+r),
                                                                QgsPoint(currpoint.x()-r,currpoint.y()),
                                                                QgsPoint(currpoint.x(),currpoint.y()-r),
                                                                QgsPoint(currpoint.x()+r,currpoint.y())]),self.canvas.currentLayer())


    def rbInit(self, color, linestyle = Qt.SolidLine, width=1):
        rb = QgsRubberBand(self.canvas, True)
        rb.setColor(color)
        rb.setWidth(width)
        rb.setLineStyle(linestyle)
        return rb


    def showSettingsWarning(self):
        pass

    def calcShiftPoint(self, p0, p1, p2):
        x0, y0, x1, y1, x2, y2 = p0.x(), p0.y(),p1.x(), p1.y(), p2.x(), p2.y()
        Tangle = calcAngle(p1, p2) #rotate axis
        Tx,Ty = x1,y1   #transpose coords

        #move and rotate (1)
        x0-=Tx
        y0-=Ty
        x=x0*cos(-Tangle)-y0*sin(-Tangle)
        y=x0*sin(-Tangle)+y0*cos(-Tangle)

        #change nearest triangle
        gamma = calcAngle(QgsPoint(0,0),QgsPoint(x,y))
        delta = self.nearestAngle(gamma)

        #move and rotate (2)
        x0=x*cos(-delta)-y*sin(-delta)
        #y0=x*sin(-delta)+y*cos(-delta)

        y0=0

        #rotate and move back (2)
        x=x0*cos(delta)-y0*sin(delta)
        y=x0*sin(delta)+y0*cos(delta)

        #rotate and move back (1)
        x0=x*cos(Tangle)-y*sin(Tangle)
        y0=x*sin(Tangle)+y*cos(Tangle)
        x0+=Tx
        y0+=Ty

        return QgsPoint(x0,y0)


    def crossCheck(self, newpoint):
        if self.nbPoints < 3: return 0
        else:
            for i in range(self.nbPoints-2):
                if self.cross(self.points[i], self.points[i+1],
                              self.points[self.nbPoints-1], newpoint):
                    return 1

        return 0


    def cross(self, p11, p12, p21, p22):
        x11, y11,x12, y12, x21, y21, x22, y22 = p11.x(), p11.y(),p12.x(), p12.y(),\
                                                p21.x(), p21.y(), p22.x(), p22.y()

        """#Require cond
        if True in map(lambda a,b: ((a[0]>b[0] and a[0]>b[1]) and (a[1]>b[0] and a[1]>b[1]))
                                or ((a[0]<b[0] and a[0]<b[1]) and (a[1]<b[0] and a[1]<b[1])),
                      [[x11,x12],[y11,y12]],[[x21,x22],[y21,y22]]):
            return 0"""

        v1 = (x22-x21)*(y11-y21)-(y22-y21)*(x11-x21)
        v2 = (x22-x21)*(y12-y21)-(y22-y21)*(x12-x21)
        v3 = (x12-x11)*(y21-y11)-(y12-y11)*(x21-x11)
        v4 = (x12-x11)*(y22-y11)-(y12-y11)*(x22-x11)
        return (v1*v2<0) and (v3*v4<0)


    def crossPoint(self, p11, p12, p21, p22):
        alpha = calcAngle(p11,p12)
        beta = calcAngle(p21,p22)
        if sin(alpha-beta)==0: return None

        [p21, p22] = self.moveCoords(p12, [p21, p22])
        [p21, p22] = self.rotateCoords(-alpha, [p21, p22])
        if p21.x() == p22.x():
            x = p21.x()
        else:
            beta = calcAngle(p21,p22)
            x = p21.x()+p21.y()/tan(-beta)
        newpoint = QgsPoint(x,0)
        [newpoint] = self.rotateCoords(alpha, [newpoint])
        [newpoint] = self.moveCoords(p12, [newpoint], -1)

        return newpoint


    def rotateCoords(self, angle, QPlist):
        return map(lambda p: QgsPoint(p.x()*cos(angle)-p.y()*sin(angle),
                                      p.x()*sin(angle)+p.y()*cos(angle)), QPlist)

    def moveCoords(self, point, QPlist, reverse = 1):
        return map(lambda p: QgsPoint(p.x()-point.x()*reverse,
                                      p.y()-point.y()*reverse), QPlist)


    def lastAngle(self, currpoint):
        Tangle = -calcAngle(self.points[0],self.points[1])
        x0=currpoint.x()-self.points[0].x()
        y0=currpoint.y()-self.points[0].y()
        x=x0*cos(Tangle)-y0*sin(Tangle)
        y=x0*sin(Tangle)+y0*cos(Tangle)
        return calcAngle(QgsPoint(0,0),QgsPoint(x,y))


    def nearestAngle(self,angle):
        #TAnb - the number of triangles, divides the plane
        sepAngle = 2*pi/self.TAnb
        a=pi*2
        if self.nbPoints==1:
            delta = 0
        else:
            delta = sepAngle
        for i in range(1,self.TAnb):
            if abs(angle - delta) < a:
                a = abs(angle - delta)
                delta+=sepAngle
            else:
                delta-=sepAngle
                break
            if i == self.TAnb-1:
                delta-=sepAngle
        return delta

    def calcPLApoint(self, currpoint, beta):
        Tangle = -(beta+calcAngle(self.points[0],self.points[1]))

        x0 = currpoint.x()-self.points[0].x()
        y0 = currpoint.y()-self.points[0].y()
        x=x0*cos(Tangle)-y0*sin(Tangle)
        #y=x0*sin(Tangle)+y0*cos(Tangle)

        y = 0

        x0=x*cos(-Tangle)-y*sin(-Tangle)
        y0=x*sin(-Tangle)+y*cos(-Tangle)
        x0+=self.points[0].x()
        y0+=self.points[0].y()
        return(QgsPoint(x0,y0))


    ####################
    #Snapping functions#
    ####################
    def updateSnapper(self):
        """
            Updates self.snapper to take into consideration layers changes, layers not displayed because of the scale *TODO* and the user's input */TODO*
            @note : it's a shame we can't get QgsMapCanvasSnapper().mSnapper which would replace all code below (I guess)
        """
        snapperList = []
        scale = self.canvas.mapRenderer().scale()
        curLayer = self.iface.legendInterface().currentLayer()
        layers = self.canvas.layers()
        for layer in layers:
            if layer.type() == QgsMapLayer.VectorLayer and layer.hasGeometryType():
                if not layer.hasScaleBasedVisibility() or layer.minimumScale() < scale <= layer.maximumScale():
                    (layerid, enabled, snapType, tolUnits, tol, avoidInt) = QgsProject.instance().snapSettingsForLayer(layer.id())
                    if not enabled:
                        continue
                    snapLayer = QgsSnapper.SnapLayer()
                    snapLayer.mLayer = layer
                    snapLayer.mSnapTo = snapType
                    snapLayer.mTolerance = tol
                    snapLayer.mUnitType = tolUnits
                    # put current layer on top
                    if layer is curLayer:
                        snapperList.insert(0, snapLayer)
                    else:
                        snapperList.append(snapLayer)
        self.snapper = QgsSnapper(self.canvas.mapRenderer())
        self.snapper.setSnapLayers(snapperList)
        self.snapper.setSnapMode(QgsSnapper.SnapWithResultsWithinTolerances)


    def _toMapSnap(self, qpoint):
        """
        returns the current snapped point (if any) and the current snapped segment (if any) in map coordinates
        The current snapped segment is returned as (snapped point on segment, startPoint, endPoint)
        """
        ok, snappingResults = self.snapper.snapPoint(qpoint, [])
        for result in snappingResults:
            if result.snappedVertexNr != -1:
                return QgsPoint(result.snappedVertex), None
        if len(snappingResults):
            output = (QgsPoint(snappingResults[0].snappedVertex), QgsPoint(snappingResults[0].beforeVertex), QgsPoint(snappingResults[0].afterVertex))
            return None, output
        else:
            return None, None