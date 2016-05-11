#!/bin/sh
set -e

# first arg is `-f` or `--some-option`
# or first arg is `something.conf`
if [ "${1#-}" != "$1" ] || [ "${1%.conf}" != "$1" ]; then
	set -- redis-server "$@"
fi

# allow the container to be started with `--user`
if [ "$1" = 'redis-server' -a "$(id -u)" = '0' ]; then
	chown -R redis .
	exec su-exec redis "$0" "$@"
fi

if [ "$1" = 'redis-server' ]; then
	# Disable Redis protected mode [1] as it is unnecessary in context
	# of Docker. Ports are not automatically exposed when running inside
	# Docker, but rather explicitely by specifying -p / -P.
	# [1] https://github.com/antirez/redis/commit/edd4d555df57dc84265fdfb4ef59a4678832f6da
	doProtectedMode=1
	configFile=
	if [ -f "$2" ]; then
		configFile="$2"
		if grep -q '^protected-mode' "$configFile"; then
			# if a config file is supplied and explicitly specifies "protected-mode", let it win
			doProtectedMode=
		fi
	fi
	if [ "$doProtectedMode" ]; then
		shift # "redis-server"
		if [ "$configFile" ]; then
			shift
		fi
		set -- --protected-mode no "$@"
		if [ "$configFile" ]; then
			set -- "$configFile" "$@"
		fi
		set -- redis-server "$@" # redis-server [config file] --protected-mode no [other options]
		# if this is supplied again, the "latest" wins, so "--protected-mode no --protected-mode yes" will result in an enabled status
	fi
fi

exec "$@"
