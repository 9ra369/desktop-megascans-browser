"""Pythonサーバーの起動処理。

メインプロセスが ``userData`` のパスを引数に渡して起動する。``127.0.0.1`` の空き
ポートで待ち受け、ポートとトークンを標準出力の1行で返す。
"""

from __future__ import annotations

import argparse
import json
import logging
import socket
import sys
from pathlib import Path

import uvicorn

from ..core.db import Database
from .app import create_app
from .settings import ServerSettings

logger = logging.getLogger(__name__)

#: 標準出力の1行目に付ける目印。メインプロセスがこれを探す。
READY_PREFIX = "MEGASCANS_BROWSER_READY "

#: ``userData`` 内のDBファイル名とログファイル名。
DB_FILE_NAME = "megascans-browser.db"
LOG_FILE_NAME = "megascans-browser.log"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="megascans-browser-server")
    parser.add_argument(
        "--user-data",
        required=True,
        help="ElectronのuserDataのパス。DBとログをこの下に置く。",
    )
    parser.add_argument("--port", type=int, default=0, help="0ならOSが空きポートを選ぶ。")
    parser.add_argument("--log-level", default="info")
    return parser.parse_args(argv)


def bind_socket(host: str, port: int) -> socket.socket:
    """待ち受けソケットを先に作る。ポート番号を起動前に確定させるため。"""
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind((host, port))
    listener.listen(128)
    return listener


def ready_line(port: int, token: str) -> str:
    return READY_PREFIX + json.dumps({"port": port, "token": token})


def parse_ready_line(line: str) -> dict[str, object] | None:
    """``ready_line`` の逆。メインプロセス側と同じ形式をテストで固定するために置く。"""
    if not line.startswith(READY_PREFIX):
        return None
    return json.loads(line[len(READY_PREFIX) :])


def configure_logging(user_data: Path, level: str) -> None:
    user_data.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[
            logging.FileHandler(user_data / LOG_FILE_NAME, encoding="utf-8"),
            logging.StreamHandler(sys.stderr),
        ],
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    user_data = Path(args.user_data)
    configure_logging(user_data, args.log_level)

    settings = ServerSettings(port=args.port, db_path=user_data / DB_FILE_NAME)
    db = Database(settings.db_path)
    db.connect()
    listener = bind_socket(settings.host, settings.port)
    port = listener.getsockname()[1]

    # 画面とメインプロセスへ接続情報を渡す。これより前に標準出力へ書かない。
    print(ready_line(port, settings.token), flush=True)
    logger.info("待ち受け開始 %s:%s", settings.host, port)

    # Windowsでは fd 渡しが使えないので、ソケットそのものをuvicornへ渡す。
    config = uvicorn.Config(
        create_app(db, settings),
        log_level=args.log_level,
        access_log=False,
    )
    try:
        uvicorn.Server(config).run(sockets=[listener])
    finally:
        listener.close()
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
