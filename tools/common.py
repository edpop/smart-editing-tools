from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *
from math import *

def distance(p1,p2):
    return sqrt((p1.x()-p2.x())**2+(p1.y()-p2.y())**2)

def distancePL(p,line):
    if line[0]==line[1]:
        return distance(p,line[0])
    return abs((line[0].y()-line[1].y())*p.x()+(line[1].x()-line[0].x())*p.y()+(line[0].x()*line[1].y()-line[1].x()*line[0].y()))\
           /distance(line[0],line[1])

def distancePS(p,segment):
    if segment[0]==segment[1]:
        return distance(p,segment[0])
    Tangle = calcAngle(segment[1],segment[0])
    [p,segment[1]] = moveCoords(segment[0],[p,segment[1]])
    [p,segment[1]] = rotateCoords(-Tangle,[p,segment[1]])
    if p.x()>segment[1].x():
        return distance(p,segment[1])
    elif p.x()<0:
        return sqrt(p.x()**2+p.y()**2)
    else: return abs(p.y())


def calcAngle(p1, p2):
        """
        returns radians of X^(p2,p1)
        """
        # Avoid division by zero
        num = p1.x() - p2.x()
        denum = p1.y() - p2.y()
        if num == 0:
            if denum > 0:
                angle = pi/2
            elif denum < 0:
                angle = 3*pi/2
            else: angle = 0
        elif denum == 0:
            if num > 0:
                angle = 0
            else: angle = pi
        elif num > 0:
            angle = atan(denum/num)
            if angle < 0:
                angle+=2*pi
        else: angle = pi+atan(denum/num)
        return angle #[0;2*pi)

def leadAngle(angle):
    if angle > 2*pi:
        while angle > 2*pi:
            angle-=2*pi
    elif angle < 0:
        while angle < 0:
            angle+=2*pi
    return angle

def nearestAngle(angle,TAnb):
        #TAnb - the number of triangles, divides the plane
        sepAngle = 2*pi/TAnb
        a=pi*2
        delta = 0
        for i in range(0,TAnb+1):
            if abs(angle - delta) < a:
                a = abs(angle - delta)
                delta+=sepAngle
            else:
                delta-=sepAngle
                break
            if i == TAnb:
                delta-=sepAngle
        return delta

def rotateCoords(angle, QPlist):
    return map(lambda p: QgsPoint(p.x()*cos(angle)-p.y()*sin(angle),
                                  p.x()*sin(angle)+p.y()*cos(angle)), QPlist)

def moveCoords(point, QPlist, reverse = 1):
    return map(lambda p: QgsPoint(p.x()-point.x()*reverse,
                                  p.y()-point.y()*reverse), QPlist)

def crossPoint(p11, p12, p21, p22):
        alpha = calcAngle(p11,p12)
        beta = calcAngle(p21,p22)
        if sin(alpha-beta)==0: return None

        [p21, p22] = moveCoords(p12, [p21, p22])
        [p21, p22] = rotateCoords(-alpha, [p21, p22])
        if p21.x() == p22.x():
            x = p21.x()
        else:
            beta = calcAngle(p21,p22)
            x = p21.x()+p21.y()/tan(-beta)
        newpoint = QgsPoint(x,0)
        [newpoint] = rotateCoords(alpha, [newpoint])
        [newpoint] = moveCoords(p12, [newpoint], -1)

        return newpoint

def convertToMapCoordinates(MapTool,layer,pList):
    for i in range(len(pList)):
        pList[i] = MapTool.toMapCoordinates(layer,pList[i])
    return pList

def convertToLayerCoordinates(MapTool,layer,pList):
    for i in range(len(pList)):
        pList[i] = MapTool.toLayerCoordinates(layer,pList[i])
    return pList
def makeCircle(point,width,nbPoints):#making "circle"
    pList = []
    sepAngle = 2*pi/nbPoints
    angle = 0
    while angle<2*pi:
        pList.append(QgsPoint(width*cos(angle),width*sin(angle)))
        angle+=sepAngle
    pList.append(pList[0])
    return moveCoords(point,pList,-1)

def getLayerSRID(layer):
    t = layer.source()
    return t[t.find("srid=")+5:t.find("type=")-1]

def getLayerTable(layer):
    t = layer.source()
    t = t[t.find('table="')+7:]
    sep = t.find('"."')
    scheme = t[:sep]
    t = t[sep+3:]
    table = t[:t.find('"')]
    return scheme+'.'+table

#######
#OTHER#
#######
def showMessage(text):
    msgBox = QMessageBox()
    msgBox.setText(text)
    msgBox.exec_()