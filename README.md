# 計測＆ロガー

スマートメーターのBルート経由で瞬時電力および積算電力量を取得し、ファイルに記録する。

### 特徴:
- Raspberry Pi + Python3 で動作
  - Raspbian Lite + sshdでの運用を想定
  - SDカード 4G以上（データ量に応じて）
  - ネットワーク接続（時刻同期のため）
  - python3, python3-serial, python3-requests
- Bルートデータ取得機能
  - WiSun モジュール RL7023 Stick-D/DSS（デュアルスタック）に対応
  - （シングルスタックの RL7023 Stick-D/IPS を使うには修正が必要）
  - 瞬時電力（E7）は10秒ごとに要求し取得
  - 積算電力量（E0）は3分ごとに要求し取得
  - 単位（E1）、係数（D3）、有効桁数（D7）は10分ごとに要求し取得
  - 積算電力量／正（EA）、積算電力量／逆（EB）の定時通知も取得
  - アクティブスキャンの結果をキャッシュファイルに保持（1時間有効）
- シリアルポートデータ取得機能
  - USBに接続したArduinoなどの周辺機器から入力されたデータも記録
- リモートの Http サーバーにデータを POST する機能
- マルチスレッドのフレームワーク
  - 不慮のエラーによる停止からの回復、長期連続運用が可能
  - 他のセンサー対応など機能の追加が容易

### 設定例:
（Bルートのみ記録する構成）
```python
# keiconf.py

import queue
from keilib.recorder import FileRecorder
from keilib.broute   import BrouteReader

record_que = queue.Queue(50)

worker_def = [
    {
        'class': FileRecorder,
        'args': {
            'fname_base': 'mydatafile',
            'record_que': record_que
        }
    },
    {
        'class': BrouteReader,
        'args': {
            'port': '/dev/serial/by-id/usb-FTDI_FT230X_Basic_UART_xxxxxxxx-if00-port0',
            'baudrate': 115200,
            'broute_id': 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
            'broute_pwd': 'xxxxxxxxxxxx',
            'record_que': record_que
        }
    },
]
```
### 起動方法:


あらかじめ pyserial をインストールしておく。
```sh
$ sudo apt install python3-serial
```

```text
workdir/
    |-- keilib/
    |-- keiconf.py
    |-- kei.py
```

上記ディレクトリ構成にて keiconf.py に構成を定義する。

```sh
$ python3 kei.py
```
で実行する。また、

```sh
$ DEBUG=0 python3 kei.py
```
とすると、デバッグモードでログ出力先が標準出力になる。
