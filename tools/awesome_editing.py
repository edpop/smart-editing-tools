# -*- coding: utf-8 -*-

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *
from math import *
from common import *

simpleColor = QColor(192,168,70)
prettyColor = QColor(255,0,127)
prettiestColor = QColor(92,40,159)

class AwesomeEditingTool(QgsMapTool):
    def __init__(self, iface):
        self.iface = iface
        self.canvas = self.iface.mapCanvas()
        QgsMapTool.__init__(self,self.canvas)
        self.layer = None
        self.fId = None
        self.pId = None
        self.vId = None
        self.pList = []
        self.x = None
        self.y = None
        self.TAnb = 4
        self.mouseClicked = None
        self.rb = QgsRubberBand(self.canvas, True)
        self.rb.setColor(prettyColor)
        self.rb.setWidth(2)
        self.rbAcc = QgsRubberBand(self.canvas, True)
        self.rbAcc.setColor(simpleColor)
        self.rbAcc.setWidth(1)
        self.rbAcc.setLineStyle(Qt.DashLine)
        self.accMPL = []
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
        self.layer = self.canvas.currentLayer()
        self.canvas.setCursor(self.cursor)

    def deactivate(self):
        self.rb.reset(True)
        self.rbAcc.reset(True)

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
            self.rbAcc.setColor(simpleColor)
        self.rbAcc.setToGeometry(QgsGeometry.fromMultiPolyline(self.accMPL),self.layer)

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
            point = self.toLayerCoordinates(self.layer,QgsPoint(self.x,self.y))
            self.layer.beginEditCommand('awesome_editing')
            self.layer.moveVertex(point.x(),point.y(),self.fId,self.vId)
            self.layer.endEditCommand()
            self.resetTool(point)
            self.canvas.refresh()


    def resetTool(self,point):
        self.fId = None
        self.pId = None
        self.vId = None
        self.pList = []
        width = self.width()

        rect = QgsRectangle(QgsPoint(point.x()+width,point.y()+width),
                            QgsPoint(point.x()-width,point.y()-width))
        featureIt = self.layer.getFeatures(QgsFeatureRequest().setFilterRect(self.toLayerCoordinates(self.layer,rect)))

        d = None
        for feature in featureIt:
            geom = feature.geometry()
            if not geom:
                continue

            if geom.type()==1:
                pList = geom.asPolyline()
                pList = convertToMapCoordinates(self,self.layer,pList)
                for i in range(len(pList)):
                    Td = distance(pList[i], point)
                    if d is  None:
                        if Td<width:
                            d = Td
                            self.pList = pList
                            self.fId = feature.id()
                            self.pId = i
                            self.vId = self.pId
                    else:
                        if Td < d:
                            d=Td
                            self.pList = pList
                            self.fId = feature.id()
                            self.pId = i
                            self.vId = self.pId

            elif geom.type() == 2:
                polygons = geom.asPolygon()
                di = 0
                for polygon in polygons:
                    pList = polygon[:-1]
                    pList = convertToMapCoordinates(self,self.layer,pList)
                    for i in range(len(pList)):
                        Td = distance(pList[i], point)
                        if d is  None:
                            if Td<width:
                                d = Td
                                self.pList = pList
                                self.fId = feature.id()
                                self.pId = i
                                self.vId = self.pId+di
                        else:
                            if Td < d:
                                d=Td
                                self.pList = pList
                                self.fId = feature.id()
                                self.pId = i
                                self.vId = self.pId+di
                    di+=len(pList)+1

        self.rb.reset(True)
        if not (None in [self.fId,self.pId]):
            r = self.width()
            p = self.pList[self.pId]
            self.rb.setToGeometry(QgsGeometry.fromPolyline([QgsPoint(p.x()+r,p.y()),
                                                            QgsPoint(p.x(),p.y()+r),
                                                            QgsPoint(p.x()-r,p.y()),
                                                            QgsPoint(p.x(),p.y()-r),
                                                            QgsPoint(p.x()+r,p.y())]),self.layer)


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
                self.rbAcc.setColor(prettyColor)
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
                    self.rbAcc.setColor(prettiestColor)
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
                    self.rbAcc.setColor(prettiestColor)
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
            self.rbAcc.setColor(prettyColor)
            return True
        #даём возможность делать красивые углы слоям с геометрией LINESTRING с другими сущностями
        elif self.layer.geometryType() == 1:
            if self.pId == 1:
                llp = self.findCross(lp)
                if llp:
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
                                self.rbAcc.setColor(prettiestColor)
                                self.x, self.y = newpoint.x(), newpoint.y()
                                self.accMPL = [[lp,newpoint,rp]]
                                return True
                            else:
                                newpoint = LLPoint
                                self.accMPL = [[lp,newpoint]]
                        else:
                            newpoint = LLPoint
                            self.accMPL = [[lp,newpoint]]
            elif self.pId == len(self.pList)-2:
                rrp = self.findCross(rp)
                if rrp:
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
                                self.rbAcc.setColor(prettiestColor)
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
            self.rbAcc.setColor(prettyColor)
            return True

        return False

    def findCross(self, point):
        pointGeom = QgsGeometry.fromPoint(point)
        width = self.width()
        rect = QgsRectangle(QgsPoint(point.x()+width,point.y()+width),
                            QgsPoint(point.x()-width,point.y()-width))

        featureIt = self.layer.getFeatures(QgsFeatureRequest().setFilterRect(rect))
        for feature in featureIt:
            if feature.id() == self.fId:
                continue
            pList = feature.geometry().asPolyline()
            for i in range(len(pList)-1):
                line = QgsGeometry.fromPolyline(pList[i:i+2])
                if line.intersects(pointGeom):
                    return pList[i]

        return None
