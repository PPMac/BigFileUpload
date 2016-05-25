#!/usr/bin/env python
# encoding: utf-8

import os

from tornado import gen
from tornado.web import RequestHandler

from bigfileupload import error
from bigfileupload.model.file import File
from bigfileupload.model.chunk import Chunk


class BaseHandler(RequestHandler):
    def initialize(self):
        self.lock = self.application.settings["lock"]
        self.CHUNK_SIZE = self.application.settings["CHUNK_SIZE"]
        self.CHUNKS_ROOT = self.application.settings["CHUNKS_ROOT"]

    @gen.coroutine
    def options(self):
        """get settings of BigFileUpload"""

        self.set_status(200)
        self.set_header("Chunk-Size", self.CHUNK_SIZE)
        self.finish()

    @gen.coroutine
    def get(self):
        self.render("template/index.html")


class FileHandler(BaseHandler):
    @gen.coroutine
    def get(self, file_id):
        """download this file"""

        file_ = File.get(file_id)
        if not file_:
            self.set_status(404)
            self.finish()
            return

        # necessary?
        # if not file_.is_good:
        #     self.set_status(406, "file not completed")
        #     self.finish()
        #     return

        self.set_header("Content-Type", file_.content_type)
        self.set_header("Content-Length", file_.size)

        for chunk_id in file_.chunks:
            chunk = Chunk.get(chunk_id)

            try:
                with open(chunk.path, 'rb') as f:
                    buffer = f.read()

                    self.write(buffer)
                    self.flush()

            except Exception as e:
                self.set_status(500, str(e))
                self.finish()
                return

        self.set_status(206)
        self.finish()

    @gen.coroutine
    def post(self, *args):
        """create file"""

        file_name = self.request.headers.get("File-Name", None)
        size = int(self.request.headers.get("File-Size", -1))
        content_type = self.request.headers.get(
            "Content-Type", "application/octet-stream")

        if size <= 0 or not file_name:
            self.set_status(412, "headers required")
            self.finish()
            return

        file_ = File.create(file_name, size, self.CHUNK_SIZE, content_type)

        self.set_status(201)
        self.set_header("File-Id", file_.id_)
        self.set_header("File-Chunks", " ".join(file_.chunks))
        self.set_header("Content-Type", content_type)
        self.set_header(
            "Location",
            "{}://{}/file/{}".format(
                self.request.protocol, self.request.host, file_.id_)
        )
        self.finish()

    @gen.coroutine
    def head(self, file_id):
        """get information of this file"""

        file_ = File.get(file_id)
        if not file_:
            self.set_status(404)
            self.finish()
            return

        self.set_status(204)
        self.set_header("Chunk-Size", file_.chunk_size)
        self.set_header("File-Type", file_.content_type)
        self.set_header("File-Chunks", " ".join(file_.chunks))
        self.set_header(
            "Bad-Chunks", " ".join(
                map(lambda item: "{}:{}".format(*item), file_.get_chunks(0))))

        self.finish()


class ChunkHandler(BaseHandler):
    @gen.coroutine
    def post(self, *args):
        """create chunk"""

        file_id = self.request.headers.get('File-Id', None)
        index = int(self.request.headers.get("Chunk-Index", -1))
        checksum = self.request.headers.get("Chunk-Checksum", None)

        if not file_id or index < 0 or not checksum:
            self.set_status(412)
            self.finish()
            return

        file_ = File.get(file_id)

        try:
            chunk = file_.create_chunk(index, self.CHUNKS_ROOT, checksum)
        except error.PathError:
            self.set_status(500)
            self.finish()
            return
        except error.PathExistError:
            self.set_status(409, "path existed")
            self.finish()
            return

        self.set_status(201)
        self.set_header(
            "Location",
            "{}://{}/chunk/{}".format(
                self.request.protocol, self.request.host, chunk.id_)
        )
        self.finish()

    @gen.coroutine
    def head(self, chunk_id):
        """get information of this chunk"""

        chunk = Chunk.get(chunk_id)
        if not chunk:
            self.set_status(404)
            self.finish()
            return

        if not os.path.exists(chunk.path):
            self.set_status(403, "chunk not initialized")
            self.finish()
            return

        self.set_status(204)
        self.set_header("Chunk-Size", chunk.size)
        self.set_header("Chunk-Offset", os.stat(chunk.path).st_size)
        self.finish()

    @gen.coroutine
    def patch(self, chunk_id):
        """upload chunks, support resuming"""

        chunk = Chunk.get(chunk_id)
        if not chunk:
            self.set_status(404)
            self.finish()
            return

        offset = int(self.request.headers.get("Chunk-Offset", -1))
        if offset != chunk.offset:
            self.set_status(409, "offset conflicts")

        self.lock.acquire()
        try:
            with open(chunk.path, "a") as f:
                f.write(self.request.body)
        except:
            self.lock.release()

            self.set_status(500)
            self.finish()
            return
        self.lock.release()

        self.set_status(204)
        self.set_header("Chunk-Offset", os.stat(chunk.path).st_size)
        self.finish()
