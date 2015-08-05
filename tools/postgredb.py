# -*- coding: utf-8 -*-
import psycopg2

class postgreDB():
    def __init__(self,source,DoConnect=False):#,host='',dbname='',user='',password=''):
        """
        self.host = host
        self.dbname = dbname
        self.user = user
        self.password = password
        """
        self.connText = ''
        self.cur = None
        self.conn = None
        try:
            if source:
                if not self.parce(source):
                    raise
                if DoConnect:
                    self.connect()
        except:
            pass
            #self.showMessage("Failed to connect database.")

    def parce(self,source):
        t = source.find("sslmode=")
        if t<0:
            return False
        self.connText = source[:t]

        return True

    def connect(self):
        try:
            pass
            #self.conn = psycopg2.connect(self.connText)
            #self.cur = self.conn.cursor()
        except:
            pass

    ########
    #QUERYS#
    ########

    def query(self,text):
        if self.conn:
            try:
                self.cur.execute(text)
            except:
                #max_locks_per_transaction error
                self.connect()
                self.cur.execute(text)
            try:
                return self.cur.fetchall()
            except:
                return []
        else: return []