#/usr/bin/python3
# -*- coding: utf-8 -*-
"""
設定ファイルで指定したワーカクラスのインスタンスを作成し、それぞれスレッドで並列動作させる
定期的にスレッドの状態を確認し、停止しているものがあればインスタンスを再度作成し再起動する
オブジェクト間のデータ受け渡しはスレッドセーフな Queue オブジェクトを介して行う
"""
__author__ = "MATSUDA, Koji <kjmatsuda@gmail.com>"
__version__ = "0.0.1"
__date__    = "2019-12-07"

import signal
import atexit
import logging
from logging.handlers import TimedRotatingFileHandler
import os
import time
import sys
import keiconf

# import configuretion file.
# （設定ファイルをインポートする）
worker_def = keiconf.worker_def

# If the environment variable DEBUG is defined, specify DEBUG as the log level.
# DEBUG 環境変数が定義されていたらログレベルをDEBUGとする
if 'DEBUG' in os.environ:
    debug = os.environ['DEBUG']
else:
    debug = 0

# Preparing log files（ログファイルの準備）
fname = __file__.split('.')

if debug:
    LOGLEVEL = logging.DEBUG
    handler = logging.StreamHandler()
else:
    LOGLEVEL = logging.INFO
    LOGFILE = os.getcwd() + '/' + fname[0] + '.log'
    handler = TimedRotatingFileHandler(LOGFILE, when='D', interval=1, backupCount=3)

# Set formatter in handler（ハンドラにフォーマッタをセット）
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# Setting the root logger（ルートロガーの設定）
logger = logging.getLogger('')
logger.setLevel(LOGLEVEL)
logger.addHandler(handler)

# Defining signal handlers（シグナルハンドラの定義）
# 1. End process（終了処理）
def exit_handler(signal, frame):
    logger.info('Stopping all threads. Please wait ...')
    # 動作中の woker にストップイベントをセット
    for wdef in worker_def:
        wdef['instance'].stop()
    sys.exit(0)

# 2. End process（終了処理）
# def goodbye():
#     logger.info('stop ' + fname[0])

# 3. Changing the log level（ログレベルの変更）
def change_loglevel( signal, frame ):
    current_log_level = logging.getLogger('').getEffectiveLevel()
    if current_log_level == logging.DEBUG:
        logger.info('change loglevel to INFO')
        logging.getLogger('').setLevel(logging.INFO)
    else:
        logger.info('change loglevel to DEBUG')
        logging.getLogger('').setLevel(logging.DEBUG)

# Registering signal handlers（シグナルハンドラの登録）
signal.signal( signal.SIGHUP, exit_handler )
signal.signal( signal.SIGINT, exit_handler )
signal.signal( signal.SIGTERM, exit_handler )
signal.signal( signal.SIGUSR1, change_loglevel )
# atexit.register( goodbye )

# Launch each worker instance（各ワーカーインスタンスの起動）
for wdef in worker_def:
    wdef['instance'] = wdef['class']( **wdef['args'] )
    wdef['instance'].start()
logger.info('start ' + fname[0])

# Check if the threads have stopped at intervals, and restart them if stopped.
# 一定間隔でスレッドが停止したかどうかを確認し、停止していた場合は再起動
while True:
    for wdef in worker_def:
        if not wdef['instance'].isAlive():
            logger.warning(wdef['class'].__name__ + ' worker object is stoped. restart again.')
            wdef['instance'] = wdef['class']( ** wdef['args'])
            wdef['instance'].start()

    time.sleep(10)
