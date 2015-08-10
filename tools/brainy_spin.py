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

class BrainySpinTool(QgsMapTool):
    def __init__(self, iface):
        self.iface = iface
        self.canvas = self.iface.mapCanvas()
        QgsMapTool.__init__(self,self.canvas)
        self.layer = None
        self.mouseClicked = None
        self.fId = None
        self.p1 = None
        self.p2 = None
        self.vertex = None
        self.pList = []
        self.sp1 = None
        self.sp2 = None
        self.rb = QgsRubberBand(self.canvas, True)
        self.rb.setColor(QColor(0,102,102))
        self.rb.setWidth(3)
        self.srb = QgsRubberBand(self.canvas, True)
        self.srb.setColor(QColor(235,159,44))
        self.srb.setWidth(3)
        self.fsrb = QgsRubberBand(self.canvas, True)
        self.fsrb.setColor(QColor(0,255,0))
        self.fsrb.setWidth(2)
        self.fsrb.setLineStyle(Qt.DashLine)
        self.fsrb.setBrushStyle(Qt.NoBrush)
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

    def deactivate(self):
        self.rb.reset(True)
        self.srb.reset(True)
        self.fsrb.reset(True)


    def width(self):
        return self.iface.mapCanvas().mapUnitsPerPixel()*10

    def canvasPressEvent(self,event):
        point = self.toMapCoordinates(event.pos())
        if event.button() == 2:
            self.mouseClicked = False
            self.fId = None
            self.p1 = None
            self.p2 = None
            self.pList = []
            self.srb.reset(True)
            self.fsrb.reset(True)
            self.vertex = None
        if event.button() == 1:
            self.mouseClicked = True
            self.resetFeature(point)

    def canvasMoveEvent(self,event):
        point = self.toMapCoordinates(event.pos())
        if not self.mouseClicked:
            self.resetFeature(point)
        if not self.fId:
            return
        if self.mouseClicked:
            self.resetSpinFeature(point)

    def canvasReleaseEvent(self,event):
        if not self.mouseClicked:
            return
        if event.button() == 1:
            self.mouseClicked = False
            self.srb.reset(True)
            self.fsrb.reset(True)
            if not self.p1 and not self.vertex:
                return
            point = self.toMapCoordinates(event.pos())
            newPlist = self.getNewPlist(self.pList,point)
            self.layer.beginEditCommand('brainy_spin')
            for i in range(len(newPlist)):
                self.layer.moveVertex(newPlist[i].x(),newPlist[i].y(),self.fId,i)
            self.layer.endEditCommand()
            self.resetFeature(point)
            self.canvas.refresh()


    def resetFeature(self,point):
        self.fId = None
        self.p1 = None
        self.p2 = None
        self.pList = []
        self.vertex = None
        width = self.width()
        rect = QgsRectangle(QgsPoint(point.x()+width,point.y()+width),
                            QgsPoint(point.x()-width,point.y()-width))
        featureIt = self.layer.getFeatures(QgsFeatureRequest().setFilterRect(self.toLayerCoordinates(self.layer,rect)))

        dS = None
        dP = None
        for feature in featureIt:
            geom = feature.geometry()
            if not geom:
                continue
            if geom.type()==1:
                pList = geom.asPolyline()
                pList = convertToMapCoordinates(self,self.layer,pList)
                if self.layer.geometryType() == 1: s=1
                else: s=0
                for i in range(len(pList)):#check vertex
                    Td = distance(point,pList[i])
                    if dP is  None:
                        if Td<width:
                            self.p1 = None
                            self.p2 = None
                            dP = Td
                            self.pList = pList
                            self.fId = feature.id()
                            self.vertex = pList[i]
                        elif Td<dP:
                            dP=Td
                            self.pList = pList
                            self.fId = feature.id()
                            self.vertex = pList[i]
                if self.vertex:
                    continue
                for i in range(s,len(pList)):#check segment
                    Td = distancePS(point,[pList[i-1],pList[i]])
                    if dS is  None:
                        if Td<width:
                            dS = Td
                            self.pList = pList
                            self.fId = feature.id()
                            self.p1, self.p2 = pList[i-1],pList[i]
                        elif Td<dS:
                            dS=Td
                            self.pList = pList
                            self.fId = feature.id()
                            self.p1, self.p2 = pList[i-1],pList[i]
            elif geom.type() == 2:
                self.pList = []
                for polygon in geom.asPolygon():
                    pList = polygon#[:-1]
                    pList = convertToMapCoordinates(self,self.layer,pList)
                    self.pList+= pList
                    if self.layer.geometryType() == 1: s=1
                    else: s=0
                    for i in range(len(pList)):#check vertex
                        Td = distance(point,pList[i])
                        if dP is  None:
                            if Td<width:
                                self.p1 = None
                                self.p2 = None
                                dP = Td

                                self.fId = feature.id()
                                self.vertex = pList[i]
                            elif Td<dP:
                                dP=Td

                                self.fId = feature.id()
                                self.vertex = pList[i]
                    if self.vertex:
                        continue
                    for i in range(s,len(pList)):#check segment
                        Td = distancePS(point,[pList[i-1],pList[i]])
                        if dS is  None:
                            if Td<width:
                                dS = Td

                                self.fId = feature.id()
                                self.p1, self.p2 = pList[i-1],pList[i]
                            elif Td<dS:
                                dS=Td
                                self.fId = feature.id()
                                self.p1, self.p2 = pList[i-1],pList[i]
            else: continue


        self.rb.reset(True)
        if not (None in [self.p1,self.p2]):
            self.rb.setToGeometry(QgsGeometry.fromPolyline([self.p1,self.p2]),self.layer)
        elif self.vertex:
            self.rb.setToGeometry(QgsGeometry.fromPolyline(makeCircle(self.vertex,width,16)),self.layer)

    def resetSpinFeature(self,point):
        self.sp1 = None
        self.sp2 = None
        if not self.vertex:
            width = self.width()
            rect = QgsRectangle(QgsPoint(point.x()+width,point.y()+width),
                                QgsPoint(point.x()-width,point.y()-width))

            d = None
            legendInterface = self.iface.legendInterface()
            for layer in self.iface.legendInterface().layers():
                if not legendInterface.isLayerVisible(layer):
                    continue
                if layer.type() <> QgsMapLayer.VectorLayer or not layer.hasGeometryType():
                    continue
                featureIt = layer.getFeatures(QgsFeatureRequest().setFilterRect(self.toLayerCoordinates(layer,rect)))
                for feature in featureIt:
                    if feature.id() == self.fId:
                        continue
                    geom = feature.geometry()
                    if not geom:
                        continue
                    if geom.type()==1:
                        pList = geom.asPolyline()
                        pList = convertToMapCoordinates(self,layer,pList)
                        if layer.geometryType() == 1: s=1
                        else: s=0
                        for i in range(s,len(pList)):
                            Td = distancePS(point,[pList[i-1],pList[i]])
                            if d is  None:
                                if Td<width:
                                    d = Td
                                    self.sp1, self.sp2 = pList[i-1],pList[i]
                            else:
                                if Td < d:
                                    d=Td
                                    self.sp1, self.sp2 = pList[i-1],pList[i]
                    elif geom.type() == 2:
                        for polygon in geom.asPolygon():
                            pList = polygon[:-1]
                            pList = convertToMapCoordinates(self,layer,pList)
                            if layer.geometryType() == 1: s=1
                            else: s=0
                            for i in range(s,len(pList)):
                                Td = distancePS(point,[pList[i-1],pList[i]])
                                if d is  None:
                                    if Td<width:
                                        d = Td
                                        self.sp1, self.sp2 = pList[i-1],pList[i]
                                else:
                                    if Td < d:
                                        d=Td
                                        self.sp1, self.sp2 = pList[i-1],pList[i]

        self.srb.reset(True)
        self.fsrb.reset(True)
        if not (None in [self.sp1,self.sp2]):
            self.srb.setToGeometry(QgsGeometry.fromPolyline(convertToLayerCoordinates(self,self.layer,[self.sp1,self.sp2])),self.layer)
        if self.layer.geometryType() == 1:
            self.fsrb.setToGeometry(QgsGeometry.fromPolyline(self.getNewPlist(self.pList,point)),self.layer)
        else:
            self.fsrb.setToGeometry(QgsGeometry.fromPolygon([self.getNewPlist(self.pList,point)]),self.layer)

    def getNewPlist(self,pList,point=None):
        if self.vertex:
            center = self.centerGeom(pList)
        else:
            center = self.centerGeom([self.p1,self.p2])
        if not None in [self.sp1,self.sp2]:
            Tangle = calcAngle(self.sp1,self.sp2)
            [point] = moveCoords(self.sp2,[center])
            [point] = rotateCoords(-Tangle,[point])
            point = QgsPoint(point.x(),0)
            [point] = rotateCoords(Tangle,[point])
            [point] = moveCoords(self.sp2,[point],-1)
        if self.vertex:
            gamma = calcAngle(center,point)-calcAngle(center,self.vertex)
        else:
            gamma = calcAngle(center,point)-pi/2-calcAngle(self.p1,self.p2)
        nPlist = moveCoords(center, pList)
        nPlist = rotateCoords(gamma,nPlist)
        nPlist = moveCoords(center, nPlist, -1)
        nPlist = convertToLayerCoordinates(self,self.layer,nPlist)
        return nPlist


    def centerGeom(self,pList):
        if len(pList) == 0:
            return None
        x = 0
        y = 0
        for p in pList:
            x+=p.x()
            y+=p.y()
        return QgsPoint(x/len(pList),y/len(pList))


    def side(self,pList):
        if (pList[0].y() - pList[1].y())*(self.p1.y()-self.p2.y())<0:
            return pi
        return 0