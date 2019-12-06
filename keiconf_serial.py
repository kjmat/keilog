#/usr/bin/python3
# -*- coding: utf-8 -*-
"""シリアルポートから入力されるデータを読み込み、ファイルに記録する設定

keiconf.py にリネームして使用

SerialReader:
    データフォーマット
        [UNITID],[SENSORID],[VALUE],[DATAID]<改行>
    UNITID:   Auduino などのユニットを識別するID
    SENSORID: UNIT上でセンサを識別するID
    VALUE:    センサの読み取り値
    DATAID:   重複データを排除するためのID（無線の場合、複数のコピーを受信することがある）

    IDはいずれも半角英数字とハイフン'-'のみ、VALUEは数値として解釈できる文字列であること
"""

import queue
from keilib.recorder import FileRecorder
from keilib.serial   import SerialReader

#スレッド間でデータを共有する Queue
record_que    = queue.Queue(50)
# 保存するファイル名のベースを指定
fname_base  = 'mylogfile'
# シリアルポート情報
serial_port = '/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_YYYYYYYY-if00-port0'
baud_rate   = 115200

# ここで指定したクラスインスタンスが作成され、スレッドで並列動作する
# オブジェクト間で共有する queue を使って互いにデータを交換する
# 同一クラスの複数のインスタンスを作成することも可能
worker_def = [
    {
        'class': FileRecorder,
        'args': {
            'record_que': record_que,
            'fname_base': fname_base,
        }
    },

    {
        'class': SerialReader,
        'args': {
            'port': serial_port,
            'baudrate': baud_rate,
            'record_que': record_que,
        }
    },
]
