スマートメーター＆計測ロガー
====================

スマートメーターの情報を取得し、ファイルに記録します。

特徴:
--------------------
- Raspberry Pi + Python3 で動作
  - Raspbian Lite （デスクトップが入ってない。ヘッドレスで運用）
  - SDカード 4G以上（データ量に応じて。16Gもあれば十分）
  - ネットワーク接続（時刻同期のためとかいろいろ）
  - python3, python3-serial, python3-requests
  - （最新ディストリビューションだと serial だけ別途インストール）
  - ラズパイでなくても大丈夫だと思いますが、前提としてつけっぱなしになります。
- スマートメーターBルートデータ取得機能
  - WiSun モジュール RL7023 Stick-D/DSS（デュアルスタック）に対応
  - （シングルスタックの RL7023 Stick-D/IPS を使うには修正が必要。持ってないので未実装です）
  - 取得したいスマートメーターのプロパティと取得間隔を定義できる。
    * 対応プロパティ = D3,D7,E0,E1,E3,E7,E8,(EA,EB)
    * D3: 係数「積算電力量計測値」を実使用量に換算する係数
    * E7: 積算電力量計測値の有効桁数
    * E1: 単位「積算電力量計測値」の単位 (乗率)
    * E0: 積算電力量 計測値 (正方向計測値)
    * E3: 積算電力量 計測値 (逆方向計測値)
    * E7: 瞬時電力計測値（逆潮流のときは負の値）
    * E8: 瞬時電流計測値（Ｔ／Ｒ相別の電流）
    * EA: 定時 積算電力量 計測値 (正方向計測値)
    * EB: 定時 積算電力量 計測値 (逆方向計測値)
  - 状態遷移による振る舞いの管理 → 接続が切れても自動的に再接続
- シリアルポートからのデータ取得機能
  - USBに接続した Arduino などの周辺機器から入力されたデータも記録可能
  - Arduinoはセンサのライブラリや作例が豊富で使いやすいし消費電力も少ない
  - XbeeやTWELiteDIPなどで無線化すれば、離れた場所のセンサも記録できる
  - TWELiteDIPにセンサを直結した場合、電池で数年持つセンサノードが作れる
- リモートの Http サーバーにデータを POST する機能
  - 遠隔地に置いたラズパイのデータを（そこそこ）リアルタイムに取得するため
  - Raspi + Soracom(SIM) + AK020(3Gモデム) で安定動作
- マルチスレッド（シンプルなフレームワーク）
  - 不慮のエラーによる停止からの回復、長期連続運用が可能
  - 機能の追加が容易

設定例:
--------------------
（Bルートのみ記録する構成）
```python
# keiconf.py

import queue
from keilib.recorder import FileRecorder
from keilib.broute   import BrouteReader

# オブジェクト（スレッド）間で通信を行うための Queue
record_que = queue.Queue(50)

# 動作させるオブジェクトの構成
worker_def = [
    {
        'class': FileRecorder,                  # FileRecorderオブジェクトを作成
        'args': {                               # 引数
            'fname_base': 'mydatafile',         # 記録ファイルの名前に使われる文字列
            'record_que': record_que            # 記録するデータをやり取りする Queue
        }
    },
    {
        'class': BrouteReader,                  # BrouteReaderオブジェクトを作成
        'args': {                               # 引数
            'port': '/dev/serial/by-id/usb-FTDI_FT230X_Basic_UART_xxxxxxxx-if00-port0',
                                                # WiSUNドングルのシリアルポート
            'baudrate': 115200,                 # WiSUNドングルのボーレート
            'broute_id': 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
                                                # BルートＩＤ（電力会社に申請）
            'broute_pwd': 'xxxxxxxxxxxx',       # Bルートパスワード（電力会社に申請）
            'requests':[                        # 取得するプロパティ値の定義
                { 'epc':['D3','D7','E1'], 'cycle': 3600 },
                                                #   積算電力量用 係数(D3),有効桁数(D7),単位(E1),3600秒ごと
                { 'epc':['E7'], 'cycle': 10 },  #   瞬時電力(E7),10秒ごと
                { 'epc':['E0','E3'], 'cycle': 300 },
                                                #   積算電力量(E0,E3),300秒ごと
            ],
            'record_que': record_que            # 記録するデータをやり取りする Queue
        }
    },
]
```
上記の設定例では、`worker_def` リストに `FileRecorder` と `BrouteReader`
の2つのクラスがコンストラクタへの引数の構成とともに定義されています。
`key.py` はこの設定ファイルを読み込み、そこに定義されているクラスのインスタンスを作成し管理します。
作成されたオブジェクトはそれぞれ別のスレッドで動作を開始しますが、
スレッド間でデータを受け渡すために `queue.Queue` オブジェクトを利用しています。  
上記の `record_que` は2つのオブジェクト間でファイルに保存するデータを受け渡すために共有されています。
`BrouteReader` はスマートメーターから情報を得ると体裁を整えて `record_que` に投入(put)します。
一方 `FileRecorder` は `recoed_que` に流れてきたデータを取得(get)してファイルに保存します。
Queue オブジェクトはスレッドセーフであるため、排他制御を意識せずに使用できます。

こうした `Queue` を介した連携の中に `SerialReader` など、
また別のスレッドで動作するオブジェクトを加えてやれば、
Arduino 等に接続したセンサーのデータもシリアルポートを通して同様に記録することができます。
また、`HttpPostUploader` を追加すれば、遠隔地のウェブサーバーにデータを送信することもできます。  
さらに例えば、ファイルではなくデータベースへ記録する `SqlRecorder？` クラス（未実装）や、
測定値を監視して一定の条件を満たすとメールなどでアラートを通知する `Watcher？` クラス（未実装）など、
様々な機能を簡単に追加することができます。
機能ごとにスレッドを分けて実行することにより、シンプルで柔軟なフレームワークとなっています。

起動方法:
--------------------
Raspbian Lite にあらかじめ pyserial をインストールしておきます。
```sh
$ sudo apt install python3-serial
```
適当な作業ディレクトリを作成し、以下のようにファイルを配置し、
`keiconf.py` には構成を定義しておきます。

```text
workdir/
    |-- keilib/
    |   |-- __init__.py
    |   |-- broute.py
    |   +-- ....
    |
    |-- keiconf.py
    +-- kei.py
```

プログラムの実行は次のように行います。
```sh
$ python3 kei.py
```
実行すると `workdir/` ディレクトリ内に、計測データを保存するファイルが2つと、
プログラムの実行時の情報を出力するログファイル`kei.log`が作成されます。
ログについては、

```sh
$ DEBUG=0 python3 kei.py
```
のように起動すると、ログレベル = DEBUG となりログの出力先が標準出力になります。
ログレベルは USR1 シグナルを受け取ると INFO <-> DEBUG で反転します。

プログラムの終了については、HUP, INT, TERM シグナルによって各オブジェクトにストップイベントを送っています。
ストップイベントを受けとったオブジェクトのスレッドはリソースを開放してから終了します。

出力ファイルの形式:
--------------------
2つのファイルが作られます。

```
1. [YYYYMMDD]-[mydatafile].txt
2. sum[YYYYMMDD]-[mydatafile].txt
```
1.は1行につき1件のデータが記録されており、行のフォーマットは以下の形をとります。
```text
[YYYY/MM/DD hh:mm:ss],[UnitID],[SensorID],[Value],[DataID]<改行>
```
なお BrouteReader の場合、出力するデータは以下の通りです。
```
[UnitID]    = BR（固定）
[SensorID]  = スマートメーターのプロパティコード(EPC): E7, E0 等
[Value]     = 測定値（数値）
[DataID]    = x（固定）
```
2.は1行に各センサーの10分ごとの平均値が記録されます。
```
[YYYY/MM/DD hh:m0],[UnitID],[SensorID],[AverageValue]<改行>
```
日付のフォーマットに秒がない点に注意です。

参考:
--------------------
* [エコーネット規格](https://echonet.jp/spec_g/)
  - [ECHONET Lite規格書 Ver.1.13（日本語版）](https://echonet.jp/spec_v113_lite/)
    - [第2部 ECHONET Lite 通信ミドルウェア仕様](https://echonet.jp/wp/wp-content/uploads/pdf/General/Standard/ECHONET_lite_V1_13_jp/ECHONET-Lite_Ver.1.13_02.pdf)
  - [APPENDIX ECHONET機器オブジェクト詳細規定Release L Revised](https://echonet.jp/spec_object_rl_revised/)
    - [Appendix_Release_L_revised.pdf](https://echonet.jp/wp/wp-content/uploads/pdf/General/Standard/Release/Release_L_jp/Appendix_Release_L_revised.pdf)
* [経済産業省 スマートハウス・ビル標準・事業促進検討会](https://www.meti.go.jp/committee/kenkyukai/mono_info_service.html#smart_house)
  - [【第9回配布資料】HEMS-スマートメーターBルート(低圧電力メーター)運用ガイドライン［第4.0版］](https://www.meti.go.jp/committee/kenkyukai/shoujo/smart_house/pdf/009_s03_00.pdf)
* blog記事など
  - [スマートメーターの情報を最安ハードウェアで引っこ抜く](https://qiita.com/rukihena/items/82266ed3a43e4b652adb)
  - [Bルートやってみた - スカイリー・ネットワークス](http://www.skyley.com/products/b-route.html)
