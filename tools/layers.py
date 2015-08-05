# -*- coding: utf-8 -*-
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *
from postgredb import *
from common import *

class layersDB():
    def __init__(self,layers):
        self.layers = [] #[ class layer() ,..., ]
        self.dataBases = [] #[ [ndb, db] ,..., ]
        for layer in layers:
            if layer.type() <> QgsMapLayer.VectorLayer or not layer.hasGeometryType():
                continue
            l = layerDB()
            db = postgreDB(layer.source())
            l.db = self.findDB(db)
            l.db.connect()
            if l.db.conn:
                l.qgslayer = layer
                l.srid = getLayerSRID(layer)
                l.table = getLayerTable(layer)
                self.layers.append(l)

    def findDB(self,db):
        for dataBase in self.dataBases:
            if dataBase.connText == db.connText:
                return dataBase
        self.dataBases.append(db)
        return db

    def findLayer(self,layer):
        #print(self.layers)
        for l in self.layers:
            if l.qgslayer == layer:
                return l
        return None

class layerDB():
    def __init__(self):
        self.qgslayer = None
        self.srid = None
        self.db = None
        self.table = None