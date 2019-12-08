#/usr/bin/python3
# -*- coding: utf-8 -*-

'''Bルート経由で電力情報を取得し、ファイルに記録すると同時に、サーバーにアップロードする設定

keiconf.py にリネームして使用
'''

import queue
from keilib.uploader import HttpPostUploader
from keilib.recorder import FileRecorder
from keilib.broute   import BrouteReader


# settings for FileRecorder
record_que = queue.Queue(50)
fname_base = 'mylogfile'

# settings for HttpPostUploader
upload_que = queue.Queue(50)

# upload.php のサンプルは php フォルダにある
target_url = 'https://example.com/upload.php'
upload_key = 'xxxxxxxxxxxxxxxx'

# settings for BrouteReader
broute_port = '/dev/serial/by-id/usb-FTDI_FT230X_Basic_UART_xxxxxxxx-if00-port0'
broute_baudrate = 115200
broute_id = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
broute_pwd = 'xxxxxxxxxxxx'
requests = [
    { 'epc':['D3','D7','E1'], 'cycle': 3600 },  # 係数(D3),有効桁数(D7),単位(E1),3600秒ごと
    { 'epc':['E7'], 'cycle': 10 },              # 瞬時電力(E7),10秒ごと
    { 'epc':['E0'], 'cycle': 300 },             # 積算電力量(E0),300秒ごと
],
# definition fo worker objects
worker_def = [
    {
        'class': HttpPostUploader,
        'args': {
            'upload_que': upload_que,
            'target_url': target_url,
            'upload_key': upload_key
        }
    },

    {
        'class': FileRecorder,
        'args': {
            'record_que': record_que,
            'fname_base': fname_base,
            'upload_que': upload_que
        }
    },

    {
        'class': BrouteReader,
        'args': {
            'port': broute_port,
            'baudrate': broute_baudrate,
            'broute_id': broute_id,
            'broute_pwd': broute_pwd,
            'requests': requests,
            'record_que': record_que,
        }
    },
]
