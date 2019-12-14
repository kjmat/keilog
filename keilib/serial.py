#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" シリアルポートを通して送られてきたデータを読み取る

データの内容をチェックして、OKならファイルへ送る。チェック内容は
    * データフォーマット、型
    * 重複受信（無線通信での再送を検出）
    * 外れ値（チェッカー）
"""

import re
import io
import os
import time
import threading
import serial
import queue
from abc import ABCMeta, abstractmethod

from keilib.worker import Worker

from logging import getLogger, StreamHandler, DEBUG
logger = getLogger(__name__)

class Checker (metaclass=ABCMeta):
    """センサー値をチェックするクラス（アブストラクト）
    """
    @abstractmethod
    def check(self, unit, sensor, value):
        """ユニット、センサー、その値を受け取りチェックしてTrueまたはFalseを返す
        オーバーライドする
        """
        pass

class OutlierChecker ( Checker ):
    """センサーごとに必要があれば外れ値を定義しチェックする

    外れ値とは、
        * 定義域を外れた値
        * 一定値以上に大きな変動を示した値
    """

    def __init__(self):
        """コンストラクタ"""
        super().__init__()
        self.check_list = {}

    def check(self, unit, sensor, value):
        """引数に与えたセンサーと値の組について、

        外れ値であればFalseを返す
        引数：
            unit (str): ユニットの識別子
            sensor (str): センサーの識別子
            value (number): データの値
        """
        checkid = sensor + '_' + unit
        if checkid in self.check_list.keys():
            sensorData = self.check_list[checkid]
            max = sensorData['max']
            min = sensorData['min']
            variation = sensorData['variation']

            if not(min <= value <= max):
                return False

            # 前回値との比較
            if 'prev' in sensorData.keys():
                prev = sensorData['prev']
                if abs(value - prev) > variation:
                    sensorData['count'] += 1

                    if sensorData['count'] < 3:
                        return False

            sensorData['prev'] = value
            sensorData['count'] = 0
            return True

        else:
            return True

    def add(self, unit, sensor, min, max, variation):
        """チェックリストにセンサーの定義域と変動範囲を指定する
        引数；
            unit (str): ユニット識別子 unitid
            sensor (str): センサーの識別子 sensorid
            min (number): 最小値、これより小さい値は外れ値とみなす
            max (number): 最大値、これより大きい値は外れ値とみなす
            variation (number): 変動範囲、これより大きな変動は外れ値とみなす。
                ただし、３回目以上変動の外れ値が続いたら、それを新しい基準とする。
        """
        checkid = sensor + '_' + unit
        self.check_list[checkid] = {'min': min, 'max': max, 'variation': variation}
        logger.debug('add ' + checkid)
        return True

class SerialReader( Worker ):
    """シリアルポートからデータ（1行）を読み取り、内容をチェックした上で record_queに送信する。

        * 無効な形式のデータを破棄
        * checkerが指定されている場合、それを使用して外れ値を確認
        * 再送されたデータの受信の破棄（無線の場合に起こる）
    """

    def __init__(self, port, baudrate, record_que=None, checker=None ):
        """コンストラクタ

        引数：
            port (str): 記録するシリアルポートのデバイス文字列
            baudrate (int): ボーレート(9600、19200、... )
            record_que (Queue): FileRecorderオブジェクトにデータを送信する
            cheker ( Checker ): 値をチェックする

        シリアル通信の他のパラメータは以下固定
            - データビット: 8bit
            - パリティビット: なし
            - ストップビット: 1bit
            - タイムアウト: 0.1秒
            − フロー制御(ソフト／ハード): OFF
        """
        super().__init__()
        self.fileNameBase = port.split('/').pop(-1)
        self.record_que = record_que
        self.port = port
        self.baudrate = baudrate
        self.recent = []
        # self.buff = []
        self.rechkline = re.compile(r'^[a-zA-Z0-9_;:., -]*$')
        self.rechkid = re.compile(r'^[a-zA-Z0-9-]+$')
        self.dataID = 0
        self.checker = checker
        self.errorcount = 0
        if os.path.exists(self.port):
            ser = serial.Serial(
                port     = self.port,
                baudrate = self.baudrate,
                bytesize = serial.EIGHTBITS,
                parity   = serial.PARITY_NONE,
                stopbits = serial.STOPBITS_ONE,
                timeout  = 0.1,
                xonxoff  = False,
                rtscts   = False,
                dsrdtr   = False
            )
            self.ser = ser

            # テキストIOの作成
            self.ser_io = io.TextIOWrapper(io.BufferedRWPair(ser, ser, 1),
                                          newline = '\n',
                                          line_buffering = False
                                          )


    def run(self):
        """スレッド処理"""

        while not os.path.exists(self.port):
            # ポートが見つかるまで待機
            logger.warning("port not found : " + self.port)
            time.sleep(60)

        logger.info('[START] port=' + self.port + ', boudrate=' + str(self.baudrate))


        while not self.stopEvent.is_set():
            # ストップイベントが設定されるまで繰り返す

            try:
                line = self.ser_io.readline();
                self.errorcount = 0

            except UnicodeDecodeError as err:
                logger.warning('Unicode Decode Error in ser_io.readline(), port=' + self.fileNameBase)
                time.sleep(5)
                self.errorcount += 1
                if self.errorcount > 10:
                    break
                continue

            except:
                logger.error('Unknown Error in ser_io.readline(), port=' + self.fileNameBase)
                time.sleep(5)
                self.errorcount += 1
                if self.errorcount > 10:
                    break
                continue

            # 空行の場合スキップ
            line = line.strip()
            if line == '':
                continue

            # 文字化け等の不正データのスキップ
            if not self.rechkline.match(line):
                logger.warning('Receiving a invalid data, port=' + str(self.fileNameBase))
                continue

            # Data extraction（データ抽出）
            line_list = line.split(',')
            # unit, sensor, valueの３つが必要
            if len(line_list) < 3:
                logger.warning('incomplete data, port=' + str(self.fileNameBase) + ' data=' + line)
                continue

            unit     = line_list.pop(0).strip()
            sensor   = line_list.pop(0).strip() #[:5]
            valueStr = line_list.pop(0).strip()

            # When dataID exists（さらにdataIDがある場合）
            if len(line_list) > 0:
                dataID = line_list.pop(0).strip()
            else:
                dataID = str(self.dataID)
                self.dataID += 1
                if self.dataID > 100:
                    self.dataID = 0

            # unitのチェック
            if not self.rechkid.match(unit):
                logger.warning('invarid unit id. "' + unit + '" port=' + self.fileNameBase)
                continue

            # sensorのチェック
            if not self.rechkid.match(sensor):
                logger.warning('invarid sensor id. "' + sensor + '" port=' + self.fileNameBase)
                continue

            # valueが有効な数値であるか
            try:
                value = float(valueStr)
            except:
                logger.warning('invalid numeric value ="' + valueStr + '", port=' + str(self.fileNameBase))
                continue

            # 重複データのチェック（無線の再送処理等で同じデータを受信した場合）
            line = unit + ',' + sensor + ',' + valueStr + ',' + dataID
            if line in self.recent:
                logger.debug('Receiving a duplicated data, port=' + str(self.fileNameBase) + ', data=' + line)
                continue

            # 受信データの記録（過去１０件分）
            self.recent.insert(0, line)
            if len(self.recent) > 10:
                self.recent.pop()

            # 外れ値のチェック
            if not self.checker is None:
                if not self.checker.check(unit, sensor, value):
                    logger.error('sensor value outlier error ' + sensor + '_' + unit + ': ' + str(value))
                    continue

            # 一行書き出す
            if self.record_que is None:
                logger.error('file queue does not exist.')
            else:
                try:
                    self.record_que.put([unit, sensor, value, dataID], block=False)
                except queue.Full:
                    logger.error('record_queue is full')
                    continue

        self.ser.close()
        logger.info('[STOP] port=' + self.port)
