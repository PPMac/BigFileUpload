#!/usr/bin/env python
# encoding: utf-8

# add current project to path
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import threading

from tornado.ioloop import IOLoop
from tornado.web import Application, StaticFileHandler

from bigfileupload.handler import BaseHandler, FileHandler, ChunkHandler


PROJECT_PATH = os.path.dirname(os.path.abspath(__file__))
STATIC_PATH = os.path.join(PROJECT_PATH, "static")

CHUNK_SIZE = 16 * 1024 * 1024  # 16M
CHUNKS_ROOT = "./chunks"


def initialize():
    """make sure `CHUNKS_ROOT` exists"""

    chunks_root = os.path.abspath(
        os.path.expandvars(os.path.expanduser(CHUNKS_ROOT)))

    if not os.path.exists(chunks_root):
        os.mkdir(chunks_root)


def make_app():
    return Application([
        (r"/", BaseHandler),
        (r"/file/?(\w{32})?", FileHandler),
        (r"/chunk/?(\w{32})?", ChunkHandler),
        (r"/static/(.*)", StaticFileHandler, {"path": STATIC_PATH})
    ], **{
        "lock": threading.Lock(),
        "CHUNK_SIZE": CHUNK_SIZE,
        "CHUNKS_ROOT": CHUNKS_ROOT,
        "debug": True
    })


if __name__ == "__main__":
    initialize()

    app = make_app()
    app.listen(8080)
    IOLoop.current().start()
