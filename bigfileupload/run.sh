#!/bin/bash

echo "starting redis-server..."
nohup redis-server &

echo "starting web server..."
python server.py

