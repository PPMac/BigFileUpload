#!/usr/bin/env python
# encoding: utf-8


import threading
import redis


lock = threading.Lock()


class Database(object):
    _instance = None

    @classmethod
    def instance(cls):
        """Redis singleton instance - thread safe."""

        if cls._instance is None:
            lock.acquire()
            if cls._instance is None:
                cls._instance = redis.StrictRedis()
            lock.release()
        return cls._instance
