#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""リモートへデータをアップロードする機能をもつクラスを定義する

ToDo:
    http POST 以外でアップロードするもの
    ツイッターへ投稿など（必要があれば）
"""
import threading
import requests
import sys
import queue
from keilib.worker import Worker

from logging import getLogger, StreamHandler, DEBUG
logger = getLogger(__name__)

class HttpPostUploader ( Worker ):
    """upload_queに入っているデータを取り出して、httpサーバーにPOSTする
    """

    def __init__( self , upload_que, target_url, upload_key):
        """コンストラクタ
        引数：
            upload_que (Queue): データ受け取るための queue
            target_url (str): サーバーURL
            upload_key (str): アップロードキー(サーバー側で認証に使う)
        """
        super().__init__()
        self.upload_que = upload_que
        self.target_url = target_url
        self.upload_key = upload_key

    def run ( self ):
        logger.info('[START]')
        # self.upload_que.put(['test.txt', 'This is test data\n'])
        while not self.stopEvent.is_set():
            # get data from upload_que（queueからデータの取得）
            try:
                filename, data = self.upload_que.get(timeout=3)
            except:
                # logger.debug('upload que is empty')
                continue

            payload = {
                'type' : 'text',
                'key'  : self.upload_key,
                'fname': filename,
                'data' : data
            }
            logger.debug(payload)

            # POST execution（POST実行）
            try:
                response = requests.post(self.target_url, payload)
            except:
                logger.error('requests post error')
                continue

        logger.info('[STOP]')
