#!/bin/bash
set -e

SETPRIV="/usr/bin/setpriv --reuid redis --regid redis --clear-groups"
IS_REDIS_SENTINEL=""
IS_REDIS_SERVER=""
CONFIG=""

SKIP_FIX_PERMS_NOTICE="Use SKIP_FIX_PERMS=1 to skip permission changes."

# functions
has_cap() {
	/usr/bin/setpriv -d | grep -q 'Capability bounding set:.*\b'"$1"'\b'
}

check_for_sentinel() {
	CMD="$1"
	shift
	if [ "$CMD" = '/usr/local/bin/redis-server' ]; then
		for arg in "$@"; do
			if [ "$arg" = "--sentinel" ]; then
				return 0
			fi
		done
	fi

	if [ "$CMD" = '/usr/local/bin/redis-sentinel' ]; then
		return 0
	fi

	return 1
}

# Note: Change permissions only in simple, default cases to avoid affecting
# unexpected or user-specific files.

fix_data_dir_perms() {
	# Expecting only *.rdb files and default appendonlydir; skip if others are found.
	unknown_file="$(find . -mindepth 1 -maxdepth 1 \
		-not \( -name \*.rdb -or \( -type d -and -name appendonlydir \) \) \
		-print -quit)"
	if [ -z "$unknown_file" ]; then
		find . -print0 | fix_perms_and_owner rw
	else
		echo "Notice: Unknown file '$unknown_file' found in data dir. Permissions will not be modified. $SKIP_FIX_PERMS_NOTICE"
	fi
}

fix_config_perms() {
	config="$1"
	mode="$2"

	if [ ! -f "$config" ]; then
		return 0
	fi

	confdir="$(dirname "$config")"
	if [ ! -d "$confdir" ]; then
		return 0
	fi

	# Expecting only the config file; skip if others are found.
	pattern=$(printf "%s" "$(basename "$config")" | sed 's/[][?*]/\\&/g')
	unknown_file=$(find "$confdir" -mindepth 1 -maxdepth 1 -not -name "$pattern" -print -quit)

	if [ -z "$unknown_file" ]; then
		printf '%s\0%s\0' "$confdir" "$config" | fix_perms_and_owner "$mode"
	else
		echo "Notice: Unknown file '$unknown_file' found in '$confdir'. Permissions will not be modified. $SKIP_FIX_PERMS_NOTICE"

	fi
}

fix_perms_and_owner() {
	mode="$1"

	# shellcheck disable=SC3045
	while IFS= read -r -d '' file; do
		if [ "$mode" = "rw" ] && $SETPRIV test -r "$file" -a -w "$file"; then
			continue
		elif [ "$mode" = "r" ] && $SETPRIV test -r "$file"; then
			continue
		fi
		new_mode=$mode
		if [ -d "$file" ]; then
			new_mode=${mode}x
		fi
		err=$(chown redis "$file" 2>&1) || echo "Warning: cannot change owner to 'redis' for '$file': $err. $SKIP_FIX_PERMS_NOTICE"
		err=$(chmod "u+$new_mode" "$file" 2>&1) || echo "Warning: cannot change mode to 'u+$new_mode' for '$file': $err. $SKIP_FIX_PERMS_NOTICE"
	done
}

requirepass_arg_present() {
	# TODO: maybe better to check that provided password is not empty?
	for arg in "$@"; do
		if [ "$arg" = "--requirepass" ]; then
			return 0
		fi
	done
	return 1
}

# Assume that requirepass, include or user directives means that we have
# security settings and there is no point to show empty password warning.
config_has_security_settings() {
	if [ ! -r "$1" ]; then
		return 1
	fi
	# TODO: skip user for sentinel as it always has one
	grep -q -e '^[[:space:]]*\(requirepass\|include\|user\)[[:space:]][[:space:]]*[^[:space:]]' "$1"
}

show_empty_password_warning() {
	local config="$1"
	shift
	local pw
	pw=$(get_provided_password)
	if [ -z "$SKIP_PASSWORD_WARNING" ] && [ -z "$pw" ] && ! requirepass_arg_present "$@" && ! config_has_security_settings "$config"; then
		cat >&2 <<-'EOF'
  ********************************************************************************
  ********************************************************************************
  **                                                                            **
  **                           ##### WARNING #####                              **
  **                                                                            **
  **                       NO PASSWORD HAS BEEN SET!                            **
  **                                                                            **
  **  Redis is starting WITHOUT authentication enabled.                         **
  **  Anyone with network access to this container can connect                  **
  **  to Redis without a password and execute commands.                         **
  **                                                                            **
  **  This is INSECURE and should only be used in development environments.     **
  **                                                                            **
  **  To secure your Redis instance, set a password using one of:               **
  **    - REDIS_PASSWORD or REDIS_PASSWORD_FILE environment variable            **
  **    - requirepass directive in redis.conf                                   **
  **    - --requirepass command line option                                     **
  **    - ACL users configuration                                               **
  **                                                                            **
  **  Use SKIP_PASSWORD_WARNING=1 to hide this warning.                         **
  **                                                                            **
  ********************************************************************************
  ********************************************************************************
EOF
	fi
}

enquote_config_value() {
	# TODO: properly escape and quote password for config
	echo "$1"
}

# Provide error handling
get_password_from_file() {
	if [ ! -r "$1" ]; then
		return 1
	fi
	# TODO: check for multiline, null bytes, etc
	head -1 "$1"
}

get_provided_password() {
	# TODO: Handle cases when both are set with priority or error
	if [ -n "$REDIS_PASSWORD" ]; then
		echo "$REDIS_PASSWORD"
		return 0
	fi
	# TODO: Make sure to fail if file is not readable and not optional
	if [ -n "$REDIS_PASSWORD_FILE" ]; then
		get_password_from_file "$REDIS_PASSWORD_FILE" || :
		return 0
	fi
}

create_password_arg() {
	# nameref to caller's variable
    local -n _out=$1
	local no_include_conf="$2"

	local pw
	pw=$(get_provided_password)
	if [ -z "$pw" ]; then
		_out=()
		return 0
	fi

	# Try to use config file for password, to avoid showing it in process list.
	if [ -z "$no_include_conf" ] && [ -w /tmp ] && touch /tmp/requirepass.conf && chmod 0600 /tmp/requirepass.conf; then
		echo "requirepass $(enquote_config_value "$pw")" > /tmp/requirepass.conf
		_out=(--include /tmp/requirepass.conf)
		return 0
	else
		# Fallback to --requirepass if /tmp is not writable.
		_out=(--requirepass "$pw")
	fi
}

create_module_args() {
	# nameref to caller's variable
	local -n _out=$1
	_out=()

	modules_dir="/usr/local/lib/redis/modules"
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

			_out+=("--loadmodule" "$module")
		done
	fi
}

# first arg is `-f` or `--some-option`
# or first arg is `something.conf`
if [ "${1#-}" != "$1" ] || [ "${1%.conf}" != "$1" ]; then
	set -- redis-server "$@"
fi
CMD=$(command -v "$1" 2>/dev/null || :)

if [ "$(readlink -f "$CMD")" = '/usr/local/bin/redis-server' ]; then
	IS_REDIS_SERVER=1
fi

if check_for_sentinel "$CMD" "$@"; then
	IS_REDIS_SENTINEL=1
fi

# if is server and its first arg is not an option then it's a config
if [ "$IS_REDIS_SERVER" ] || [ "$IS_REDIS_SENTINEL" ] && [ "${2#-}" = "$2" ]; then
	CONFIG="$2"
fi

# drop privileges only if
# we are starting either server or sentinel
# our uid is 0 (container started without explicit --user)
# and we have capabilities required to drop privs
if [ "$IS_REDIS_SERVER" ] && [ -z "$SKIP_DROP_PRIVS" ] && [ "$(id -u)" = '0' ] && has_cap setuid && has_cap setgid; then
	if [ -z "$SKIP_FIX_PERMS" ]; then
		# fix permissions
		if [ "$IS_REDIS_SENTINEL" ]; then
			fix_config_perms "$CONFIG" rw
		else
			fix_data_dir_perms
			fix_config_perms "$CONFIG" r
		fi
	fi

	CAPS_TO_KEEP=""
	if has_cap sys_resource; then
		# we have sys_resource capability, keep it available for redis
		# as redis may use it to increase open files limit
		CAPS_TO_KEEP=",+sys_resource"
	fi
	exec $SETPRIV \
		--nnp \
		--inh-caps=-all$CAPS_TO_KEEP \
		--ambient-caps=-all$CAPS_TO_KEEP \
		--bounding-set=-all$CAPS_TO_KEEP \
		"$0" "$@"
fi

# set an appropriate umask (if one isn't set already)
# - https://github.com/docker-library/redis/issues/305
# - https://github.com/redis/redis/blob/bb875603fb7ff3f9d19aad906bd45d7db98d9a39/utils/systemd-redis_server.service#L37
um="$(umask)"
if [ "$um" = '0022' ]; then
	umask 0077
fi

# inject generated arguments before user arguments to keep override ability
current_args=("$@")
head_args=("${current_args[@]}")
tail_args=()
if [ "$IS_REDIS_SERVER" ] || [ "$IS_REDIS_SENTINEL" ]; then
	# head_args: command and (optionally) config
	# tail_args: user supplied arguments
	if [ -n "$CONFIG" ]; then
		head_args=("${current_args[@]:0:2}")
		tail_args=("${current_args[@]:2}")
	else
		head_args=("${current_args[@]:0:1}")
		tail_args=("${current_args[@]:1}")
	fi

	pass_arg=()
	# sentinel doesn't support --include
	create_password_arg pass_arg $IS_REDIS_SENTINEL
	head_args+=("${pass_arg[@]}")

	show_empty_password_warning "$CONFIG" "$@"
fi

if [ "$IS_REDIS_SERVER" ] && ! [ "$IS_REDIS_SENTINEL" ]; then
	echo "Starting Redis Server"

	module_args=()
	create_module_args module_args

	head_args+=("${module_args[@]}")
fi

exec "${head_args[@]}" "${tail_args[@]}"
