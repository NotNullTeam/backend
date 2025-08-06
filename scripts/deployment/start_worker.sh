#!/usr/bin/env bash
# 启动 RQ Worker
# 依赖环境变量：REDIS_URL (如 redis://redis:6379/0)
set -e

# 默认队列 default，可通过 QUEUES 覆盖
QUEUES=${QUEUES:-default}

echo "Starting RQ worker for queues: $QUEUES"

# shellcheck disable=SC2086
rq worker $QUEUES --url "$REDIS_URL"
