#!/bin/sh
set -e

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

# set an appropriate umask (if one isn't set already)
# - https://github.com/docker-library/redis/issues/305
# - https://github.com/redis/redis/blob/bb875603fb7ff3f9d19aad906bd45d7db98d9a39/utils/systemd-redis_server.service#L37
um="$(umask)"
if [ "$um" = '0022' ]; then
	umask 0077
fi

if [ "$1" = 'redis-server' ]; then
	echo "Starting Redis Server"
	modules_dir="/usr/local/lib/redis/modules/"
	
	if [ ! -d "$modules_dir" ]; then
		echo "Warning: Default Redis modules directory $modules_dir does not exist."
	elif [ -n "$(ls -A $modules_dir 2>/dev/null)" ]; then
		for module in "$modules_dir"/*.so; 
		do
			if [ ! -s "$module" ]; then
				echo "Skipping module $module: file has no size."
				continue
			fi
			
			if [ -d "$module" ]; then
				echo "Skipping module $module: is a directory."
				continue
			fi
			
			if [ ! -r "$module" ]; then
				echo "Skipping module $module: file is not readable."
				continue
			fi

			if [ ! -x "$module" ]; then
				echo "Warning: Module $module is not executable."
				continue
			fi
			
			set -- "$@" --loadmodule "$module"
		done
	fi
fi


exec "$@"