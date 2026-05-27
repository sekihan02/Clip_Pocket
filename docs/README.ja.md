# Clip Pocket

Clip Pocket は、コピーしたテキストを一時的に残し、あとから選んでクリップボードに戻せる Windows 常駐アプリです。

現在のソースバージョン: v0.1.0

[English README](../README.md)

---

Clip Pocket は Windows クリップボードにコピーされたテキストを監視し、メモリ上の一時リストに保持します。過去の項目を選ぶと、その内容を現在のクリップボードに戻せます。自動貼り付けはしません。戻したあと、貼り付け先で `Ctrl+V` してください。

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
- アプリ終了で消えるメモリ上の履歴
- 選んだ項目を現在のクリップボードへ戻す
- 自動貼り付けなし
- 同じ内容は重複追加せず、保存期限を更新
- `Delete` キー、削除ボタン、右クリックメニューで削除
- 固定できる自動非表示ウィンドウ
- 通知領域アイコンから設定
- 既定は英語UI、日本語UIへ切替可能
- 保存期間を変更可能。無制限も選択可能
- 保存件数を変更可能

## インストール

通常利用では、最新リリースからビルド済み Windows ZIP をダウンロードしてください。

one-folder ビルドは `ClipPocket.exe` と実行時ファイルを同じフォルダに置く形式です。移動する場合はフォルダごと移動してください。

## 設定

通知領域アイコンを右クリックして `Settings` または `設定` を開きます。

設定できる項目:

- Windowsログイン時に自動起動する
- Ctrl二回で開く
- 右クリック三回で開く（実験）
- 言語
- コピーの削除までの期間
- 保存するコピー数

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

## セキュリティとプライバシー

- 履歴はメモリ上だけに保存します。
- アプリ自身はネットワークアクセスを行いません。
- クリップボード内容をディスクに保存しません。
- 他アプリへ自動貼り付けしません。
- Ctrl二回の検知には低レベルキーボードフックを使います。
- 右クリック三回の検知には、有効化した場合のみ低レベルマウスフックを使います。

## プロジェクト状態

これは初期リリースです。機能を増やすより、小さく、読みやすく、挙動が控えめな常駐アプリであることを優先しています。

プロジェクト名は、法的または商標上の安全性を保証するものではありません。別名や別ブランドで再配布する場合は、各自で確認してください。

## ライセンス

MIT
