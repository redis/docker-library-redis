#!/bin/sh
set -e

# first arg is `-f` or `--some-option`
# or first arg is `something.conf`
if [ "${1#-}" != "$1" ] || [ "${1%.conf}" != "$1" ]; then
	set -- redis-server "$@"
fi

# if secret REDIS_PASSWORD exists or REDIS_PASSWORD_FILE is set use content for requirepass
if [ "$1" = 'redis-server' -a -s "${REDIS_PASSWORD_FILE:=/run/secrets/REDIS_PASSWORD}" ]; then
	if ! printf '%s\n' "$@" | grep -Fqe "--requirepass"; then
		REDIS_PASSWORD=$(cat "${REDIS_PASSWORD_FILE}")
		set -- "$@" --requirepass "${REDIS_PASSWORD}"
	fi
fi

# allow the container to be started with `--user`
if [ "$1" = 'redis-server' -a "$(id -u)" = '0' ]; then
	find . \! -user redis -exec chown redis '{}' +
	exec gosu redis "$0" "$@"
fi

# set an appropriate umask (if one isn't set already)
# - https://github.com/docker-library/redis/issues/305
# - https://github.com/redis/redis/blob/bb875603fb7ff3f9d19aad906bd45d7db98d9a39/utils/systemd-redis_server.service#L37
um="$(umask)"
if [ "$um" = '0022' ]; then
	umask 0077
fi

exec "$@"
