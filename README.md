# Morny Bot (MVP)

Discord で Google カレンダーの「今日の予定」と Open-Meteo の天気を表示し、毎朝自動通知する Bot のMVPです。

## 機能

- `/help` コマンド一覧表示
- `/setcalendar <calendar_id>` Google Calendar ID を保存（複数はカンマ区切り対応）
- `/setlocation <地名 or 緯度経度>` 天気取得地点を保存（Open-Meteo Geocoding 対応）
- `/today` 今日の予定 + 天気を表示（部分失敗に耐性あり）
- `/morning_on [time]` 毎朝通知 ON（デフォルト `07:30`）
- `/morning_off` 毎朝通知 OFF
- `/status` 現在の設定表示

## 技術スタック

- Python 3.11+
- `discord.py` 2.x (`app_commands` / Slash Command)
- SQLite
- APScheduler
- Google Calendar API (OAuth)
- Open-Meteo API

## ディレクトリ構成

```text
project-root/
├─ src/
│  ├─ main.py
│  ├─ bot.py
│  ├─ config.py
│  ├─ db.py
│  ├─ scheduler.py
│  ├─ commands/
│  ├─ services/
│  └─ utils/
├─ data/
│  └─ bot.db (自動生成)
├─ requirements.txt
├─ .env.example
└─ README.md
```

※ 共通の `/today` 生成ロジック用に `src/services/daily_summary_service.py` を追加しています。

## セットアップ

1. 依存関係をインストール

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. `.env` を作成

```bash
cp .env.example .env
```

3. Discord Bot を作成してトークンを設定

- `DISCORD_BOT_TOKEN` に Bot トークンを設定
- MVPでは `DISCORD_GUILD_ID` を指定してギルド同期を推奨

4. Google Calendar API の OAuth 設定

- Google Cloud で Calendar API を有効化
- OAuth クライアント（デスクトップアプリ）を作成
- `credentials.json` をプロジェクト直下（または `.env` の指定パス）に配置
- 初回のカレンダー取得時に OAuth 認証が走り、`token.json` が生成されます

## 起動

```bash
python -m src.main
```

## コマンド例

- `/setcalendar primary`
- `/setcalendar primary, xxxxx@group.calendar.google.com`
- `/setlocation つくば市`
- `/setlocation 36.08,140.11`
- `/today`
- `/morning_on 07:30`
- `/status`

## 動作メモ

- `/today` は応答遅延対策として `defer()` + `followup.send()` を使用
- 予定取得失敗時でも天気が取れれば天気のみ返します（逆も同様）
- 毎朝通知は APScheduler のポーリングで `HH:MM` 一致を確認し、メモリ上で日次重複送信を防止します
- `/setcalendar` は複数カレンダーIDをカンマ区切りで登録可能です（例: `primary, xxx@group.calendar.google.com`）

## 運用前提（重要）

このBotは以下を前提にしています。

- `discord.py` の Gateway 接続を維持する常駐プロセス
- APScheduler による定期実行（毎朝通知）
- ローカルファイル永続化（`data/bot.db`, `token.json`, `credentials.json`）

そのため、HTTPリクエスト時だけ動くサーバーレス環境（例: Vercel Functions）とは相性がよくありません。

## 常駐運用の選択肢（現状コードをほぼ変えない）

以下は「`python -m src.main` をそのまま常駐させる」前提での候補です。上ほど変更が少ないです。

### 1. ローカルPC/Macで常駐（最小変更）

用途: まず動かし続けたい / 個人利用

- 変更量: ほぼなし
- メリット: いまの構成をそのまま使える
- デメリット: PCスリープ/再起動で停止、外出中に止まりやすい

方法の例:

- `tmux` / `screen` で常駐
- macOS `launchd` でログイン時自動起動

### 2. Raspberry Pi / VPS（systemd常駐）

用途: 低コストで安定常駐したい / 現状コードを維持したい

- 変更量: ほぼなし（ファイル配置とサービス化のみ）
- メリット: 常時稼働しやすい、SQLiteのまま運用しやすい
- デメリット: サーバー管理（OS更新・ログ確認）が必要

運用ポイント:

- `python -m src.main` を `systemd` サービス化
- `data/`, `credentials.json`, `token.json`, `.env` をサーバーに配置
- 初回Google認証はローカルで `token.json` を作ってからサーバーへ転送すると楽

### 3. Render（Background Worker + Persistent Disk）

用途: PaaSを使いたいが、Bot常駐 + SQLite/トークンファイルも維持したい

- 変更量: 小（デプロイ設定追加、永続ディスクのマウントパスに `.env` を合わせる）
- メリット: 常駐ワーカー向け、管理が比較的楽
- デメリット: 永続ディスク前提のためデプロイ時に数秒の停止が発生しうる

推奨構成（現状コード維持）:

- Service type: Background Worker
- Start command: `python -m src.main`
- Persistent Disk をアタッチ（例: `/var/morny`）
- `.env` を以下のように変更

```env
DATABASE_PATH=/var/morny/bot.db
GOOGLE_TOKEN_FILE=/var/morny/token.json
GOOGLE_CLIENT_SECRET_FILE=/var/morny/credentials.json
```

### 4. Railway（Service + Volume）

用途: GitHub連携で手早く常駐運用したい

- 変更量: 小（ボリューム設定 + 環境変数）
- メリット: デプロイが簡単、VolumeでSQLite/トークンを維持できる
- デメリット: Volumeなしだとファイルは消える。Volume運用の理解が必要

推奨構成（現状コード維持）:

- Service の Start Command: `python -m src.main`
- Volume を `./data` に対応する場所へマウント（Railwayでは `/app/data` が扱いやすい）
- `token.json` / `credentials.json` も Volume 配下に置く（または別の永続パス）

```env
DATABASE_PATH=/app/data/bot.db
GOOGLE_TOKEN_FILE=/app/data/token.json
GOOGLE_CLIENT_SECRET_FILE=/app/data/credentials.json
```

### 5. Fly.io（Machine + Volume）

用途: 多少インフラ設定してもよい / 常駐VMっぽく運用したい

- 変更量: 中（`Dockerfile` / `fly.toml` を追加）
- メリット: 常駐プロセスと永続Volumeの相性がよい
- デメリット: 初回セットアップは他候補より少し重い

推奨構成（現状コード維持）:

- 単一Machineで `python -m src.main` を実行
- Volume をマウントして `DATABASE_PATH`, `GOOGLE_TOKEN_FILE`, `GOOGLE_CLIENT_SECRET_FILE` をそこに向ける

## どれを選ぶべきか（おすすめ順）

1. 個人用途ですぐ使う: `ローカル常駐（tmux / launchd）`
2. 安定運用したい・最小変更: `Raspberry Pi / VPS + systemd`
3. PaaSで楽したい（現状維持寄り）: `Render` または `Railway`（永続ディスク/Volume必須）
4. 少し構成追加してもよい: `Fly.io`

## Render デプロイ手順（現状コードほぼそのまま）

このリポジトリには `render.yaml`（Blueprint）を含めています。`discord.py` の常駐Botとして動かすため、Renderでは **Background Worker + Persistent Disk** を使います。

### 前提

- Renderアカウント作成済み
- GitHub にこのリポジトリをpush済み
- ローカルで一度 Google OAuth 認証を済ませて `token.json` を生成済み（推奨）

### 1. Render で Blueprint から作成

1. Render ダッシュボードで `New +` → `Blueprint`
2. このリポジトリを選択
3. `render.yaml` を読み込ませる
4. Worker Service（`morny-bot`）の作成内容を確認して作成

`render.yaml` の内容（概要）:

- `type: worker`
- `startCommand: python -m src.main`
- Persistent Disk を `/var/morny` にマウント
- `DATABASE_PATH`, `GOOGLE_*_FILE` を `/var/morny/...` に設定

### 2. 必須環境変数を設定（Render Dashboard）

最低限必要:

- `DISCORD_BOT_TOKEN`
- `DISCORD_GUILD_ID`（任意だがMVPでは推奨）

`render.yaml` で以下はデフォルト設定済みです（変更しなくてOK）:

- `DEFAULT_TIMEZONE=Asia/Tokyo`
- `DATABASE_PATH=/var/morny/bot.db`
- `GOOGLE_CLIENT_SECRET_FILE=/var/morny/credentials.json`
- `GOOGLE_TOKEN_FILE=/var/morny/token.json`

### 3. Google の `credentials.json` / `token.json` を Render に渡す（おすすめ方法）

この実装は、起動時に以下の環境変数があればファイルを自動生成できます（ファイル未存在時のみ）。

- `GOOGLE_CLIENT_SECRET_JSON_B64`
- `GOOGLE_TOKEN_JSON_B64`

ローカルで base64 文字列を作る例（macOS / Linux 共通で Python を使用）:

```bash
python - <<'PY'
import base64, pathlib
print(base64.b64encode(pathlib.Path('credentials.json').read_bytes()).decode())
PY
```

```bash
python - <<'PY'
import base64, pathlib
print(base64.b64encode(pathlib.Path('token.json').read_bytes()).decode())
PY
```

出力された1行文字列を Render の Secret env に設定:

- `GOOGLE_CLIENT_SECRET_JSON_B64=<credentials.json の base64>`
- `GOOGLE_TOKEN_JSON_B64=<token.json の base64>`

補足:

- 初回起動時に `/var/morny/credentials.json`, `/var/morny/token.json` が生成されます
- すでにファイルがある場合は上書きしません（トークン更新を壊さないため）

### 4. デプロイ後の確認

- Render Logs で以下が出ることを確認
  - `Synced ... commands to guild ...`
  - `Morning scheduler started`
  - `Logged in as ...`
- Discord で `/status`, `/today` を試す

### 5. 運用上の注意（Render）

- **1インスタンス運用**（SQLite + APScheduler のため）
- Persistent Disk を外すと `bot.db` / `token.json` が失われる
- `credentials.json`, `token.json`, `.env` は Git にコミットしない

### 6. トラブルシュート（Render）

- `予定の取得に失敗しました`
  - `GOOGLE_CLIENT_SECRET_JSON_B64` / `GOOGLE_TOKEN_JSON_B64` の設定漏れ
  - `credentials.json` / `token.json` のbase64文字列が壊れている
- `Missing Access`（起動時コマンド同期）
  - `DISCORD_GUILD_ID` と Bot招待先サーバーが不一致
- 起動はするが通知が来ない
  - `/morning_on` を実行したチャンネルに Bot の `Send Messages` 権限がない

## デプロイ時の注意（Google OAuth / ファイル配置）

- この実装は `credentials.json` / `token.json` をファイルとして読みます
- 起動時に `GOOGLE_CLIENT_SECRET_JSON(_B64)` / `GOOGLE_TOKEN_JSON(_B64)` が設定されていれば、ファイル未存在時に自動生成できます（Render向け補助）
- リモート環境で初回認証を直接行うのは手間がかかる場合があります
- 先にローカルで認証して `token.json` を作成し、デプロイ先の永続ストレージへ配置する方法が簡単です
- `token.json`, `credentials.json`, `.env` はGitにコミットしないでください

## 注意点（MVP）

- Google OAuth は単一の `token.json` を使用します（複数Googleアカウントの同時運用は未対応）
- Bot の通知先は `/morning_on` を実行したチャンネルに保存されます
# Morny
