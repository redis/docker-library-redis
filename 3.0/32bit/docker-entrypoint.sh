#!/bin/bash
set -e

# If there is a not null environment variable REDIS_PASSWORD
# use it as an argument in `redis-server` command
if [ ${REDIS_PASSWORD:+x} ];
then
	arg="--requirepass $REDIS_PASSWORD"
else
	arg=""
fi

if [ "$1" = 'redis-server' ]; then
	chown -R redis .
	exec gosu redis "$@" $arg
fi

exec "$@" $arg