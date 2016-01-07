#!/bin/sh
set -e

if [ "$1" = 'redis-server' ]; then
	chown -R redis .
	exec su-exec redis "$@"
fi

exec "$@"
