#!/usr/bin/env bash
# Start or stop the local Postgres and ClickHouse used by the integration tests.
#
#   scripts/dev-db.sh up      # start both (idempotent), wait until ready
#   scripts/dev-db.sh down    # stop and remove both
#
# Ports are deliberately non-default so they don't collide with a locally
# installed Postgres (5432) or ClickHouse (8123) or anything else squatting on 58123.
set -euo pipefail

PG_NAME=amino-pg
CH_NAME=amino-ch
PG_PORT=${AMINO_PG_PORT:-55432}
CH_PORT=${AMINO_CH_PORT:-18123}
PG_IMAGE=postgres:16-alpine
CH_IMAGE=clickhouse/clickhouse-server:24.8

up() {
  if ! docker ps -a --format '{{.Names}}' | grep -qx "$PG_NAME"; then
    docker run -d --name "$PG_NAME" \
      -e POSTGRES_USER=amino -e POSTGRES_PASSWORD=amino -e POSTGRES_DB=amino \
      -p "${PG_PORT}:5432" "$PG_IMAGE" >/dev/null
  else
    docker start "$PG_NAME" >/dev/null
  fi
  if ! docker ps -a --format '{{.Names}}' | grep -qx "$CH_NAME"; then
    docker run -d --name "$CH_NAME" \
      -e CLICKHOUSE_USER=amino -e CLICKHOUSE_PASSWORD=amino -e CLICKHOUSE_DB=amino \
      -p "${CH_PORT}:8123" "$CH_IMAGE" >/dev/null
  else
    docker start "$CH_NAME" >/dev/null
  fi

  echo -n "waiting for postgres on :$PG_PORT "
  for _ in $(seq 1 60); do
    if docker exec "$PG_NAME" pg_isready -U amino -d amino >/dev/null 2>&1; then echo ok; break; fi
    echo -n .; sleep 1
  done
  echo -n "waiting for clickhouse on :$CH_PORT "
  for _ in $(seq 1 60); do
    if curl -fs "http://localhost:${CH_PORT}/ping" >/dev/null 2>&1; then echo ok; break; fi
    echo -n .; sleep 1
  done
  echo "AMINO_PG_DSN=postgresql://amino:amino@localhost:${PG_PORT}/amino"
  echo "AMINO_CH_URL=http://amino:amino@localhost:${CH_PORT}/amino"
}

down() {
  docker rm -f "$PG_NAME" "$CH_NAME" >/dev/null 2>&1 || true
  echo "stopped"
}

case "${1:-}" in
  up) up ;;
  down) down ;;
  *) echo "usage: $0 up|down" >&2; exit 2 ;;
esac
