#!/bin/bash
set -e
docker ps --format '{{.Names}}' 2>/dev/null || true
which psql 2>/dev/null || true
ss -lntp 2>/dev/null | grep 5432 || netstat -lntp 2>/dev/null | grep 5432 || true
