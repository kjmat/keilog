#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""スレッドで動作するオブジェクトの雛形
"""

import threading

class Worker ( threading.Thread ):
    """Woker はスレッドを停止するためのイベントを設定するための抽象クラス。
    """
    def __init__( self ):
        super().__init__()
        self.stopEvent = threading.Event()

    def stop ( self ):
        """ストップイベントをセットする。
        """
        self.stopEvent.set()
        self.join()

    def run(self):
        """ストップイベントがセットされていない限り、繰り返し実行する。
        この関数はオーバーライドする。
        """
        while not self.stopEvent.is_set():
            # do something
            pass
