# Clip Pocket

Clip Pocket は、コピーしたテキストを一時的に残し、あとから貼り付けたい内容をもう一度選べる Windows 常駐アプリです。

現在のソースバージョン: v0.2.1

[English README](../README.md)

---

Clip Pocket は Windows クリップボードにコピーされたテキストを監視し、メモリ上の一時リストに保持します。前にコピーした内容を貼り付けたいときは、Clip Pocket を開き、その項目をダブルクリックしてから貼り付け先で `Ctrl+V` します。

## スクリーンショット

![Clip Pocket メインウィンドウ](assets/clip-pocket-main.png)

画像は黒の色設定を使った例です。初期値は白で、色と透過率は `Settings` / `設定` から変更できます。

## はじめ方

GitHub Releases から Windows 版 ZIP をダウンロードし、展開して次を実行します。

```powershell
ClipPocket.exe
```

アプリは通知領域に隠れて常駐します。画面を開く方法は次の通りです。

- `Ctrl` を二回押す
- 通知領域アイコンをクリックまたはダブルクリックする
- すでに起動している状態で `ClipPocket.exe` をもう一度実行する

右クリック三回で開く操作は実験機能です。初期値は OFF で、通知領域アイコンの設定メニューから有効化できます。

## 機能

- コピーされたテキストの常駐監視
- 1文字のテキストも保存対象。空文字は保存しません
- アプリ終了で消えるメモリ上の履歴
- 選んだ項目を現在のクリップボードへ戻す
- 自動貼り付けなし
- 同じ内容は重複追加せず、保存期限を更新
- `Delete` キー、削除ボタン、右クリックメニューで削除
- 自動で隠れるウィンドウ。必要なときは「ウィンドウを固定」で開いたままにできます
- 通知領域アイコンまたはメイン画面から設定
- 通知領域アイコンから監視の一時停止・再開
- 既定は英語UI、日本語UIへ切替可能
- 保存期間を変更可能。無制限も選択可能ですが、履歴はメモリ上だけなのでアプリ終了時に消えます。
- 保存件数を変更可能
- ウィンドウの色を白または黒から選択可能
- ウィンドウの透過率を変更可能

## インストール

通常利用では、最新リリースからビルド済み Windows ZIP をダウンロードしてください。

one-folder ビルドは `ClipPocket.exe` と実行時ファイルを同じフォルダに置く形式です。移動する場合はフォルダごと移動してください。

## 設定

通知領域アイコンを右クリックして `Settings` または `設定` を開きます。メイン画面の `Settings` / `設定` からも開けます。

設定は `Apply` / `適用` でまとめて反映されます。適用せずに閉じた場合、現在の設定は変更されません。

設定できる項目:

- Windowsログイン時に自動起動する
- Ctrl二回で開く
- 右クリック三回で開く（実験）
- 言語
- 色
- 透過率
- コピーの削除までの期間
- 保存するコピー数

通知領域メニューには `Pause monitoring` / `監視を一時停止` と `Resume monitoring` / `監視を再開` もあります。一時停止中のコピーは無視され、再開後にあとから追加されることもありません。

## ウィンドウの動き

Clip Pocket はカーソルの近くに開き、画面外にはみ出さない位置へ収めます。画面端でカーソルとウィンドウが少し離れた場合でも、カーソルを動かすまでは自動で隠れません。カーソルを動かしてウィンドウ外に出ている場合は、`ウィンドウを固定` が無効ならすぐに隠れます。

## セキュリティとプライバシー

- コピー内容そのものはメモリ上だけに保持します。
- クリップボード内容をディスクに保存しません。
- アプリ設定と診断ログは `%LOCALAPPDATA%\ClipPocket` に保存されます。
- アプリ自身はネットワークアクセスを行いません。
- 他アプリへ自動貼り付けしません。
- 巨大なコピー内容は保存せず、メモリ上の履歴にも総文字数上限を設けています。
- Ctrl二回の検知には低レベルキーボードフックを使います。
- 右クリック三回の検知には、有効化した場合のみ低レベルマウスフックを使います。

## 現在の制限

- 保存対象はテキストのみです。
- 画像、ファイル、リッチテキストの書式は保存しません。
- 履歴はアプリ終了時に消えます。
- Clip Pocket は起動中に発生したクリップボード変更を記録します。起動前からクリップボードに入っていた内容は自動追加されません。
- 他アプリへ自動貼り付けはしません。
- 管理者権限のアプリ、リモートデスクトップ、ゲーム、一部の保護された画面ではショートカットが効かない場合があります。
- 右クリック三回は実験機能で、通常の右クリックメニューと競合する場合があります。

## トラブルシューティング

### 起動したが画面が出ない

Clip Pocket は通知領域に隠れて起動します。通知領域アイコンをクリックするか、`Ctrl` を二回押すか、`ClipPocket.exe` をもう一度実行してください。

### Ctrl二回で画面が開かない

`設定` を開き、`Ctrl二回で開く` が有効になっているか確認してください。一部のアプリではグローバルキーボードフックがブロックまたは上書きされる場合があります。

### Windowsの警告が出る

署名されていない実行ファイルは Windows SmartScreen の警告が出る場合があります。公式リリースページから入手したビルドだけを実行するか、自分でソースからビルドしてください。

## アンインストール

Clip Pocket は展開したフォルダの外へアプリ本体をインストールしません。ただし、ローカル設定と診断ログを保存する場合があります。

1. 通知領域メニューから Clip Pocket を終了します。
2. 自動起動を有効にしている場合は、`設定` を開いて `Windowsログイン時に自動起動する` をOFFにします。
3. 展開した `ClipPocket` フォルダを削除します。
4. ローカル設定とログも削除する場合は、次を削除します。

```text
%LOCALAPPDATA%\ClipPocket
```

コピー履歴そのものはメモリ上だけに保持され、アプリ終了時に消えます。

## ソースからビルド

このプロジェクトは Python と uv を使います。

前提:

- Windows
- Python 3.11+
- PATH に通った uv

セットアップ:

```powershell
git clone https://github.com/sekihan02/Clip_Pocket.git
cd Clip_Pocket
uv sync
uv run clip-pocket
```

Python パッケージをビルド:

```powershell
uv build --out-dir dist\python
```

Windows 実行ファイルをビルド:

```powershell
uv sync --extra build
uv run --extra build python tools/build_exe.py --clean
```

出力先:

```text
dist\windows\ClipPocket\ClipPocket.exe
```

## 品質確認

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests
python -m py_compile src\clip_pocket\*.py tools\build_exe.py
```

Windows API を起動しない履歴・設定ロジックは、`PYTHONPATH=src` を設定すれば Windows 以外でもテストできます。

## アーキテクチャ

```text
src/clip_pocket/
├── app.py          # CLI entry point and single-instance startup
├── history.py      # Clipboard history rules
├── i18n.py         # English/Japanese UI strings
├── resources.py    # Asset lookup for source and bundled builds
├── settings.py     # Local JSON settings
├── startup.py      # Per-user Windows startup registration
├── ui.py           # Tkinter UI
└── win32_host.py   # Hidden Win32 window, clipboard listener, tray icon, hooks
```

Tkinter UI と Win32 統合は分離しています。Windows メッセージは隠し Win32 ウィンドウで受け取り、キューを通して UI スレッドへ渡します。

## プロジェクト状態

これは初期リリースです。機能を増やすより、小さく、読みやすく、挙動が控えめな常駐アプリであることを優先しています。

プロジェクト名は、法的または商標上の安全性を保証するものではありません。別名や別ブランドで再配布する場合は、各自で確認してください。

## ライセンス

MIT
