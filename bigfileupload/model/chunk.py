#!/usr/bin/env python
# encoding: utf-8

import os
import hashlib

from bigfileupload import error
from bigfileupload.model.db import Database


class Chunk(object):
    KEY_CHUNK = "chunk:{id_}"

    def __init__(self, id_, size, path, checksum, is_good):
        self.id_ = id_
        self.size = int(size)
        self.path = path
        self.checksum = checksum
        self._is_good = (
            is_good if isinstance(is_good, bool) else is_good == "True")

    @classmethod
    def create(cls, id_, size, root_path, checksum):
        root_path = os.path.abspath(
            os.path.expandvars(os.path.expanduser(root_path)))

        if not (os.path.exists(root_path) and os.path.isdir(root_path)):
            raise error.PathError("invalid root_path")

        path = os.path.join(root_path, id_)
        if os.path.exists(path):
            raise error.PathExistError("path existed")

        try:
            open(path, "w").close()
        except Exception as e:
            raise error.PathError(str(e))

        chunk = cls(id_, size, path, checksum, False)

        Database.instance().hmset(cls.KEY_CHUNK.format(id_=chunk.id_), {
            "id_": chunk.id_,
            "size": chunk.size,
            "path": chunk.path,
            "checksum": chunk.checksum,
            "is_good": chunk.is_good
        })

        return chunk

    @classmethod
    def get(cls, id_):
        kwargs = Database.instance().hgetall(cls.KEY_CHUNK.format(id_=id_))
        return cls(**kwargs) if kwargs else None

    def check_status(self):
        try:
            with open(self.path, "r") as f:
                checksum = hashlib.md5(f.read()).hexdigest()
        except:
            return False

        return checksum == self.checksum

    @property
    def is_good(self):
        if self._is_good:
            return True

        self._is_good = self.check_status()
        Database.instance().hset(
            self.KEY_CHUNK.format(id_=self.id_), "is_good", self._is_good)

        return self._is_good

    @property
    def offset(self):
        if not os.path.exists(self.path):
            return -1

        return os.stat(self.path).st_size
