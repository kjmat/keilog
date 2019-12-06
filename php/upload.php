<?php
// POSTされてきた内容をチェックし保存
// 不正なアクセスはリジェクト

// アップロードキーのチェック
if ($_POST["key"] !== "xxxxxxxxxxxxxxxxxxxx") {
  exit("Error: Invalid key is specified.");
}

// アップロード間隔による制限。頻繁なPOSTによる処理を制限
// 以下の例は前回のアップロードから100秒以上
try {
  $ptime = file_get_contents('ptime.txt');
} catch (Exception $e) {
  $ptime = 0;
}
$ctime = time();
if ($ctime - $ptime < 100) {
  exit("Error: Upload interval is too short. Try later.");
}

// データサイズによる制限
// 以下の例は 1000 Byte 未満
$data  = $_POST["data"];
$length = strlen($data);
if ($length > 1000) {
  exit("Error: Too big data.");
}

// ファイル名長さチェック
// 以下の例は 20 Byte 未満
$fname = $_POST["fname"];
$length = strlen($fname);
if ($length > 20) {
  exit("Error: Too long file name.");
}

// ファイル名チェック、上書きして良いファルだけ
// 以下の例は、パス区切り文字/(スラッシュ)を含めない。想定外のディレクトリに書き込まれないように。
if ( ! preg_match("/^[A-Za-z0-9_]+(\.[A-Za-z0-0_]+)*$/", $fname)) {
  exit("Error: Invalid file name.");
}

// その他のチェックを行う
// 大切なファイルを破壊されないように
// 以下の例は update_ok.txt というファイルだけ通す
# if ( ! preg_match("/^update_ok\.txt$/", $fname)) {
#   exit("Error: The file name is not allowd.");
# }

// 指定されたファイルにデータを追記
$fp = fopen("data/" . $fname, 'a');
fwrite($fp, $data);
fclose($fp);
file_put_contents('ptime.txt', $ctime);
print "OK.";
?>
