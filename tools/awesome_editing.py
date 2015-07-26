# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Smart_tools
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
from postgredb import *

class AwesomeEditingTool(QgsMapTool):
    def __init__(self, iface):
        self.iface = iface
        self.canvas = self.iface.mapCanvas()
        QgsMapTool.__init__(self,self.canvas)
        self.fId = None
        self.pId = None
        self.pList = []
        self.x = None
        self.y = None
        self.TAnb = 4
        self.mouseClicked = None
        self.rb = QgsRubberBand(self.canvas, True)
        self.rb.setColor(QColor(255,0,127))
        self.rb.setWidth(2)
        self.rbAcc = QgsRubberBand(self.canvas, True)
        self.rbAcc.setColor(QColor(192,168,70))
        self.rbAcc.setWidth(1)
        self.rbAcc.setLineStyle(Qt.DashLine)
        #self.data = []
        self.accMPL = []
        self.db = None
        self.table = None
        self.srid = None
        self.cursor = QCursor(QPixmap(["19 19 3 1",
                                      "      c None",
                                      ".     c #4B126B",
                                      "+     c #1A90C9",
                                      "         .         ",
                                      "         .         ",
                                      "         .         ",
                                      "         .         ",
                                      "         .         ",
                                      "         .         ",
                                      "         .         ",
                                      "        +.+        ",
                                      "       ++.++       ",
                                      ".........+.........",
                                      "       ++.++       ",
                                      "        +.+        ",
                                      "         .         ",
                                      "         .         ",
                                      "         .         ",
                                      "         .         ",
                                      "         .         ",
                                      "         .         ",
                                      "         .         "]))


    def isZoomTool(self):
        return False

    def isTransient(self):
        return False

    def isEditTool(self):
        return True

    def activate(self):
        self.canvas.setCursor(self.cursor)
        QObject.connect(self.iface, SIGNAL("currentLayerChanged(QgsMapLayer*)"), self.toggle)
        self.toggle()
        #QObject.connect(self.canvas, SIGNAL("scaleChanged(double)"), self.loadData)
        #self.loadData()

    def deactivate(self):
        self.rb.reset(True)
        self.rbAcc.reset(True)
        #QObject.disconnect(self.canvas, SIGNAL("scaleChanged(double)"), self.loadData)
        QObject.disconnect(self.iface, SIGNAL("currentLayerChanged(QgsMapLayer*)"), self.toggle)

    def width(self):
        return self.iface.mapCanvas().mapUnitsPerPixel()*10

    def canvasPressEvent(self,event):
        point = self.toMapCoordinates(event.pos())
        if event.button() == 2:
            self.mouseClicked = False
            self.resetTool(point)
            self.rbAcc.reset(True)
        if event.button() == 1:
            self.mouseClicked = True
            self.resetTool(point)

    def canvasMoveEvent(self,event):
        point = self.toMapCoordinates(event.pos())
        if not self.mouseClicked:
            self.resetTool(point)
            return
        if None in [self.fId,self.pId]:
                return
        if not self.calcCurrPoint(point):
            self.rbAcc.setColor(QColor(192,168,70))
        self.rbAcc.setToGeometry(QgsGeometry.fromMultiPolyline(self.accMPL),self.iface.activeLayer())

    def canvasReleaseEvent(self,event):
        if not self.mouseClicked:
            return
        if event.button() == 1:
            self.mouseClicked = False
            self.rbAcc.reset(True)
            if None in [self.fId,self.pId]:
                return
            point = self.toMapCoordinates(event.pos())
            self.calcCurrPoint(point)
            layer = self.iface.activeLayer()
            point = self.toLayerCoordinates(layer,QgsPoint(self.x,self.y))
            layer.beginEditCommand('awesome_editing')
            layer.moveVertex(point.x(),point.y(),self.fId,self.pId)
            layer.endEditCommand()
            self.resetTool(point)
            self.canvas.refresh()
            #self.loadData()

    """
    def loadData(self):
        #unused
        return
        self.data = []
        layer = self.iface.activeLayer()
        rect = QgsRectangle(self.toMapCoordinates(QPoint(0,0)),
                            self.toMapCoordinates(QPoint(self.canvas.size().width(),self.canvas.size().height())))
        features = layer.getFeatures(QgsFeatureRequest().setFilterRect(self.toLayerCoordinates(layer,rect)))
        for feature in features:
            geom = feature.geometry()
            if geom.type()==1:
                self.data.append([feature.id(),geom.asPolyline()])
            elif geom.type() == 2:
                for polygon in geom.asPolygon():
                    self.data.append([feature.id(),polygon[:-1]])


    def loadData1(self):
        self.data = []
        layer = self.iface.activeLayer()
        rect = QgsRectangle(self.toMapCoordinates(QPoint(0,0)),
                            self.toMapCoordinates(QPoint(self.canvas.size().width(),self.canvas.size().height())))
        rect = self.iface.mapCanvas().mapRenderer().mapToLayerCoordinates(layer, rect)
        selectedFeaturesIds = layer.selectedFeaturesIds()
        layer.removeSelection()
        layer.select(rect, False)
        features = layer.selectedFeatures()
        for feature in features:
            geom = feature.geometry()
            if geom.type()==1:
                self.data.append([feature.id(),geom.asPolyline()])
            elif geom.type() == 2:
                for polygon in geom.asPolygon():
                    self.data.append([feature.id(),polygon[:-1]])
        layer.removeSelection()
        layer.select(selectedFeaturesIds)
    """

    def toggle(self):
        layer = self.iface.activeLayer()
        if layer:
            self.db = postgreDB(layer.source())
            self.db.connect()
            self.srid = getLayerSRID(layer)
            self.table = getLayerTable(layer)

    """
    def resetTool(self,point):
        if not self.db.conn:
            self.resetToolNotDB(point)
            return
        self.fId = None
        self.pId = None
        self.pList = []
        width = self.width()
        layer = self.iface.activeLayer()
        rows = self.db.query(
            "DROP TABLE IF EXISTS temppoint;"
            "CREATE TEMP TABLE temppoint AS (SELECT ST_PointFromText('"+point.wellKnownText()+"', "+self.srid+") point);"
            "SELECT ST_AsText(geom) geom, id FROM ("
                "SELECT ST_Distance(b.the_geom,t.point) dist, b.the_geom geom, b.id id FROM "+self.table+" b, temppoint t "
                "WHERE b.the_geom && 'BOX("+str(point.x()-width)+" "+str(point.y()-width)+","+str(point.x()+width)+" "+str(point.y()+width)+")'::box2d"
                ") AS s1 "
            "WHERE dist < "+str(width)+" "
            "ORDER BY dist "
            "LIMIT 1"
            )
        self.db.query("DROP TABLE IF EXISTS temppoint;")
        d = None
        for row in rows:
            geom = QgsGeometry.fromWkt(row[0])
            id = row[1]
            if geom.type()==1:
                pList = geom.asPolyline()
            elif geom.type() == 2:
                for polygon in geom.asPolygon():
                    pList = polygon[:-1]
            else: continue
            pList = convertToMapCoordinates(self,layer,pList)
            for i in range(len(pList)):
                Td = distance(pList[i], point)
                if d is  None:
                    if Td<width:
                        d = Td
                        self.pList = pList
                        self.fId = id
                        self.pId = i
                else:
                    if Td < d:
                        d=Td
                        self.pList = pList
                        self.fId = id
                        self.pId = i
        self.rb.reset(True)
        if not (None in [self.fId,self.pId]):
            r = self.width()
            p = self.pList[self.pId]
            self.rb.setToGeometry(QgsGeometry.fromPolyline([QgsPoint(p.x()+r,p.y()),
                                                            QgsPoint(p.x(),p.y()+r),
                                                            QgsPoint(p.x()-r,p.y()),
                                                            QgsPoint(p.x(),p.y()-r),
                                                            QgsPoint(p.x()+r,p.y())]),self.iface.activeLayer())
    """


    def resetTool(self,point):
        self.fId = None
        self.pId = None
        self.pList = []
        width = self.width()

        layer = self.iface.activeLayer()
        rect = QgsRectangle(QgsPoint(point.x()+width,point.y()+width),
                            QgsPoint(point.x()-width,point.y()-width))
        featureIt = layer.getFeatures(QgsFeatureRequest().setFilterRect(self.toLayerCoordinates(layer,rect)))

        d = None
        for feature in featureIt:
            geom = feature.geometry()
            if not geom:
                continue
            if geom.type()==1:
                pList = geom.asPolyline()
            elif geom.type() == 2:
                multipolygon = geom.asPolygon()
                if len(multipolygon) < 1:
                    continue
                for polygon in multipolygon:
                    pList = polygon[:-1]
            else: continue
            pList = convertToMapCoordinates(self,layer,pList)
            for i in range(len(pList)):
                Td = distance(pList[i], point)
                if d is  None:
                    if Td<width:
                        d = Td
                        self.pList = pList
                        self.fId = feature.id()
                        self.pId = i
                else:
                    if Td < d:
                        d=Td
                        self.pList = pList
                        self.fId = feature.id()
                        self.pId = i
        self.rb.reset(True)
        if not (None in [self.fId,self.pId]):
            r = self.width()
            p = self.pList[self.pId]
            self.rb.setToGeometry(QgsGeometry.fromPolyline([QgsPoint(p.x()+r,p.y()),
                                                            QgsPoint(p.x(),p.y()+r),
                                                            QgsPoint(p.x()-r,p.y()),
                                                            QgsPoint(p.x(),p.y()-r),
                                                            QgsPoint(p.x()+r,p.y())]),self.iface.activeLayer())


    def calcCurrPoint(self, point):
        self.accMPL = []
        self.x, self.y = point.x(), point.y()
        lp = self.pList[self.pId-1]
        self.accMPL.append([lp,point])
        if len(self.pList) < 3:
            return False
        rp = self.pList[self.pId+1-len(self.pList)]
        self.accMPL.append([QgsPoint(self.x,self.y),rp])
        accuracy = 2*pi/self.TAnb/20
        newpoint = None

        alpha = leadAngle(calcAngle(lp,point)-calcAngle(rp,QgsPoint(point.x(),point.y())))
        delta = nearestAngle(alpha,self.TAnb)
        LRPisGood = abs(alpha-delta) < accuracy
        if LRPisGood:
            ld = distance(lp,point)
            rd = distance(rp,point)
            if delta == pi:
                self.x = lp.x()+(rp.x()-lp.x())*ld/(ld+rd)
                self.y = lp.y()+(rp.y()-lp.y())*ld/(ld+rd)
                self.accMPL = [[lp,QgsPoint(self.x,self.y),rp]]
                self.rbAcc.setColor(QColor(255,0,127))
                return True
            if delta <> 0 and delta <> 2*pi:
                d = distance(lp,rp)
                a = d/sqrt(1+(rd/ld)**2)
                b = a*rd/ld
                gamma = atan(a/b)
                XRL = calcAngle(lp,rp)
                if ((point.x()-rp.x())*(lp.y()-rp.y())-(point.y()-rp.y())*(lp.x()-rp.x())) > 0:
                    side = -1
                else: side = 1
                Tangle = XRL+gamma*side
                [Tlp] = moveCoords(rp, [lp])
                [Tlp] = rotateCoords(-Tangle, [Tlp])
                newpoint = QgsPoint(Tlp.x(),0)
                [newpoint] = rotateCoords(Tangle, [newpoint])
                [newpoint] = moveCoords(rp, [newpoint],reverse=-1)
                self.accMPL = [[lp,newpoint,rp]]

        llp = self.pList[self.pId-2]
        alpha = leadAngle(calcAngle(point,lp)-calcAngle(llp,lp))
        delta = nearestAngle(alpha,self.TAnb)
        LLPisGood = abs(alpha-delta) < accuracy
        if LLPisGood:
            XLP = calcAngle(point,lp)
            Tangle = XLP+delta-alpha
            [LLPoint] = moveCoords(lp, [point])
            [LLPoint] = rotateCoords(-Tangle, [LLPoint])
            LLPoint = QgsPoint(LLPoint.x(),0)
            [LLPoint] = rotateCoords(Tangle, [LLPoint])
            [LLPoint] = moveCoords(lp, [LLPoint],reverse=-1)
            if LRPisGood and delta <> pi:
                p = QgsPoint(rp.x()+llp.x()-lp.x(),rp.y()+llp.y()-lp.y())
                newpoint = crossPoint(lp,LLPoint,rp,p)
                if newpoint:
                    self.rbAcc.setColor(QColor(92,40,159))
                    self.x, self.y = newpoint.x(), newpoint.y()
                    self.accMPL = [[lp,newpoint,rp]]
                    return True
                else:
                    newpoint = LLPoint
                    self.accMPL = [[lp,newpoint]]
            else:
                newpoint = LLPoint
                self.accMPL = [[lp,newpoint]]

        rrp = self.pList[self.pId+2-len(self.pList)]
        alpha = leadAngle(calcAngle(point,rp)-calcAngle(rrp,rp))
        delta = nearestAngle(alpha,self.TAnb)
        if abs(alpha-delta) < accuracy:
            XLP = calcAngle(point,rp)
            Tangle = XLP+delta-alpha
            [RRPoint] = moveCoords(rp, [point])
            [RRPoint] = rotateCoords(-Tangle, [RRPoint])
            RRPoint = QgsPoint(RRPoint.x(),0)
            [RRPoint] = rotateCoords(Tangle, [RRPoint])
            [RRPoint] = moveCoords(rp, [RRPoint],reverse=-1)
            if LRPisGood and delta <> pi:
                p = QgsPoint(lp.x()+rrp.x()-rp.x(),lp.y()+rrp.y()-rp.y())
                newpoint = crossPoint(rp,RRPoint,lp,p)
                if newpoint:
                    self.rbAcc.setColor(QColor(92,40,159))
                    self.x, self.y = newpoint.x(), newpoint.y()
                    self.accMPL = [[lp,newpoint,rp]]
                    return True
                else:
                    newpoint=RRPoint
                    self.accMPL = [[rp,newpoint]]
            else:
                newpoint=RRPoint
                self.accMPL = [[rp,newpoint]]
        if newpoint:
            self.x, self.y = newpoint.x(), newpoint.y()
            self.rbAcc.setColor(QColor(255,0,127))
            return True
        return False