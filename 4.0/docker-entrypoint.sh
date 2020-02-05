#!/bin/sh
set -e
if [ ! -z ${FORCE_DAEMON_UID+x} ];then
	usermod -u $FORCE_DAEMON_UID redis
	find / -user 999 -exec chown -h redis {} 2>/dev/null \; && true
fi
# first arg is `-f` or `--some-option`
# or first arg is `something.conf`
if [ "${1#-}" != "$1" ] || [ "${1%.conf}" != "$1" ]; then
	set -- redis-server "$@"
fi

# allow the container to be started with `--user`
if [ "$1" = 'redis-server' -a "$(id -u)" = '0' ]; then
	find . \! -user redis -exec chown redis '{}' +
	exec gosu redis "$0" "$@"
fi

exec "$@"
