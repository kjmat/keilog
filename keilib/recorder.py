#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""データを保存するためのクラスを定義

ToDo:
    * リレーショナルデータベースへの保存
    * データの流れをもっと細かく制御するクラスなど

"""

import threading
import datetime
import time
from keilib.worker import Worker

from logging import getLogger, StreamHandler, DEBUG
logger = getLogger(__name__)

class FileRecorder ( Worker ):
    """record_queからデータを取り出し、それをファイルに保存する。

    * 2つのファイルに保存する
        - すべてのデータの記録: [YYYYMMDD]-[fnameBase].txt
        - 10分ごとの平均を記録: sum[YYYYMMDD]-[fnameBase].txt
        - ファイルは日毎に作成。ファイル名には日付の情報が含まれる

    * 保存に際して
        - record_que から取り出したときのタイムスタンプを追加
        − 保存形式は、TIMESTAMP、UNIT_ID, SENSOR_ID, VALUE, DATA_ID
        - タイムスタンプは YYYY/MM/DD hh:mm:ss の形式
        例) 2019/12/01 19:12:03,A,T1,12.3,0F<LF>

    * upload_que が指定されていれば 10分平均データを追加

    * disp_def に指定されたデータは disp_queに追加

    ToDo:
        * 機能が固定的で柔軟性がない、もっと柔軟かつシンプルに設定できればよい
        * アップロードやディスプレイへ送信するなどの機能は、他のクラスに担当させるべき
        * 10分平均の計算なども別クラスがよいかも、さらに柔軟に5分平均などへの対応も
    """

    def __init__( self , record_que, fname_base='data', upload_que=None, disp_def=[] ,disp_que=None):
        """コンストラクタ

        引数：
            record_que (Queue): 保存するデータをここから取り出す
            fname_base (str):   ファイル名の基本文字列（これに日付情報が付加される）
            upload_que (Queue): アップロードする場合に指定。アップロードは HttpPostUploader オブジェクトが担当
            -- 以下未実装機能 --
            disp_def (list):    外部表示機 Displayer に送るためのデータを定義。
            disp_queue (Queue): Displayer オブジェクトにデータを送るための Queue
        """
        super().__init__()
        self.fileNameBase = fname_base
        self.record_que = record_que
        self.upload_que = upload_que
        self.disp_que = disp_que

        self.sum10m = {}
        now = datetime.datetime.today()
        self.datePre = now.strftime('%Y/%m/%d')
        self.key10mPre = now.strftime('%Y%m%d%H%M%S')[:11] + '0'
        self.disp_def = disp_def
        self._update_timestamp()

    def _update_timestamp( self ):
        """タイムスタンプ値のアップデート"""
        now = datetime.datetime.today()
        self.date = now.strftime('%Y/%m/%d')
        self.mytime = now.strftime('%H:%M:%S')
        self.key01m = now.strftime('%Y%m%d%H%M%S')
        self.key10m = self.key01m[:11] + '0'

    def _write10m( self ):
        """10分ごとの処理

        10分平均をファイルに書き出す
        upload_queにデータを送る
        """
        data = ''
        for u in self.sum10m:
            for s in self.sum10m[u]:
                count = self.sum10m[u][s]['count']
                mysum = self.sum10m[u][s]['sum']
                avr = mysum / count
                d = self.key10mPre
                date10m = d[:4]+'/'+d[4:6]+'/'+d[6:8]+' '+d[8:10]+':'+d[10:12]
                outtext = date10m + ',' + u + ',' + s + ',' + str(avr) + '\n'
                data += outtext

        if data != '':
            #filename = 'sum'+self.key01m[:8]+'-'+self.fileNameBase+'.txt'
            filename = 'sum'+self.key10mPre[:8]+'-'+self.fileNameBase+'.txt'
            with open(filename, 'a') as f:
                f.write(data)

            if self.upload_que is not None:
                try:
                    self.upload_que.put([filename, data], block=False)
                except:
                    #print ('upload queue is full')
                    pass

        self.sum10m = {}
        self.key10mPre = self.key10m

    def _writeline( self, unit, sensor, value, id='x' ):
        """データにタイムスタンプを追加してファイルに書き出す

        引数：
            unit (str): ユニットID
            sensor (str): センサーID
            value (number): センサー値
            id (str): VALUEID

        CSV形式で一行追加される。

            [timestamp],[unit],[sensor],[value],[id]
        """
        #print(self.disp_que)
        if unit not in self.sum10m:
            self.sum10m[unit] = {}
        if sensor not in self.sum10m[unit]:
            self.sum10m[unit][sensor] = {'count':0, 'sum':0.0}
        self.sum10m[unit][sensor]['count'] += 1
        self.sum10m[unit][sensor]['sum'] += value
        # ファイルへの書き出し（1行）
        linedata = self.date+' '+self.mytime+','+unit+','+sensor+','+str(round(value,4))+','+id+'\n'
        filename = self.key01m[:8]+'-'+self.fileNameBase+'.txt'

        with open(filename, 'a') as f:
            f.write(linedata)

        self._send_disp( unit, sensor, value )

    def _send_disp( self, unit, sensor, value ):
        """データが disp_def に一致するとき disp_queue に送信する
        """
        if type(self.disp_def) != list:
            return False

        for disp in self.disp_def:
            if unit == disp['unit'] and sensor == disp['sensor']:

                if self.disp_que is not None:
                    try:
                        self.disp_que.put([disp['filenumber'], unit, sensor, value], block=False)
                    except:
                        logger.debug('disp queue is full')
                        pass
                else:
                    logger.debug('disp queue is None')
                    pass

                filename = '/tmp/DISP' + disp['filenumber'] + '.txt'
                try:
                    with open(filename, mode='w') as f:
                        f.write(unit + ',' + sensor + ',' + str(value) + '\n')
                    return True
                    break
                except:
                    return False
        return False

    def run( self ):
        logger.info('[START]')
        while not self.stopEvent.is_set():
            # タイムスタンプ更新
            self._update_timestamp()
            # 10分ごとに平均値を書き出す
            if self.key10m != self.key10mPre:
                self._write10m()

            # queueからデータの取得
            try:
                unit, sensor, value, dataid = self.record_que.get(timeout=3)
            except:
                # logger.debug('file queue is empty')
                continue

            # もう一度タイムスタンプ更新
            self._update_timestamp()
            # ファイルへの書き込み
            self._writeline(unit, sensor, value, dataid)

        logger.info('[STOP]')
