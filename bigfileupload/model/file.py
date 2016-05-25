#!/usr/bin/env python
# encoding: utf-8

from __future__ import division

import uuid
import math
from datetime import datetime

from bigfileupload.model.db import Database
from bigfileupload.model.chunk import Chunk


class File(object):
    KEY_FILE = "file:{id_}"
    KEY_CHUNKS = KEY_FILE + ":chunks"

    def __init__(self, id_, file_name, size, chunk_size, create_time,
                 content_type, chunks, is_good):
        self.id_ = id_
        self.file_name = file_name
        self.size = int(size)
        self.chunk_size = int(chunk_size)
        self.create_time = datetime.strptime(create_time, "%Y-%m-%d %H:%M:%S")
        self.content_type = content_type
        self.chunks = chunks
        self._is_good = (
            is_good if isinstance(is_good, bool) else is_good == "True")

    @classmethod
    def create(cls, file_name, size, chunk_size, content_type):
        id_ = uuid.uuid1().hex
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        chunks = [
            uuid.uuid1().hex
            for _ in xrange(int(math.ceil(size / chunk_size)))
        ]

        file_ = cls(id_, file_name, size, chunk_size, now,
                    content_type, chunks, False)

        key_file = cls.KEY_FILE.format(id_=file_.id_)
        key_chunks = cls.KEY_CHUNKS.format(id_=file_.id_)

        db = Database.instance()
        db.hmset(key_file, {
            "id_": file_.id_,
            "file_name": file_.file_name,
            "size": file_.size,
            "chunk_size": file_.chunk_size,
            "create_time": file_.create_time,
            "content_type": file_.content_type,
            "is_good": file_.is_good
        })
        db.rpush(key_chunks, *file_.chunks)

        return file_

    def create_chunk(self, chunk_index, root_path, checksum):
        if chunk_index >= len(self.chunks):
            raise IndexError("chunk_index out of range")

        size = self.chunk_size
        if chunk_index == len(self.chunks) - 1:
            size = self.size - self.chunk_size * chunk_index

        return Chunk.create(
            self.chunks[chunk_index], size, root_path, checksum)

    @classmethod
    def get(cls, id_):
        db = Database.instance()
        key_file = cls.KEY_FILE.format(id_=id_)
        key_chunks = cls.KEY_CHUNKS.format(id_=id_)

        kwargs = db.hgetall(key_file)
        if not kwargs:
            return

        kwargs['chunks'] = db.lrange(key_chunks, 0, -1)

        return cls(**kwargs)

    def get_chunks(self, status=None):
        """Get chunks by status

        status:
          - None: get all chunks
          - 0: get bad chunks
          - 1: get good chunks
        """

        if status is None:
            return self.chunks

        chunks = enumerate([Chunk.get(chunk_id) for chunk_id in self.chunks])

        f = lambda chunk: not (chunk[1] and chunk[1].is_good)
        if status:
            f = lambda chunk: chunk[1] and chunk[1].is_good

        return map(
            lambda item: (item[0], self.chunks[item[0]]), filter(f, chunks))

    def check_status(self):
        chunks = [Chunk.get(chunk_id) for chunk_id in self.chunks]
        return all(chunk and chunk.is_good for chunk in chunks)

    @property
    def is_good(self):
        if self._is_good:
            return True

        self._is_good = self.check_status()
        Database.instance().hset(
            self.KEY_FILE.format(id_=self.id_), "is_good", self._is_good)

        return self._is_good
