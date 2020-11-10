#!/bin/bash

mkdir -p /root/.ssh && cp /root/.ssh_original/* /root/.ssh && chmod 700 /root/.ssh &&

until alembic upgrade head 2>/dev/null; do
  echo "Database is unavailable - sleeping (10s)"
  sleep 10
done &&
echo "Done: alembic upgrade head" &&
python processor_server.py
