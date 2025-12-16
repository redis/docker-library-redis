#!/bin/bash

##
#
# These tests are designed to verify the correctness of the entrypoint behavior
# under different preconditions and arguments. As such, in some tests, it is
# expected that the Redis process may fail with errors.
#
# To run specific test use:
#
# REDIS_IMG=image ./test.sh -- specific_test_name
#
# To get verbose output use TEST_VERBOSE=1:
#
# TEST_VERBOSE=1 REDIS_IMG=image ./test.sh
#
# Uses shunit2: https://github.com/kward/shunit2
#
# Requires sudo
#
##

# Container initialization wait time in seconds
CONTAINER_INIT_WAIT=3

if [ -z "$REDIS_IMG" ]; then
	echo "REDIS_IMG may not be empty"
	exit 1
fi
# By default create files owned by root to avoid intersecting with container user
HOST_UID=0
HOST_GID=0
if docker info 2>/dev/null | grep -qi rootless; then
	# For rootless docker we have to use current user
	HOST_UID=$(id -u)
	HOST_GID=$(id -g)
fi
HOST_OWNER=$HOST_UID:$HOST_GID

get_container_user_uid_gid_on_the_host() {
	container_user="$1"
	dir=$(mktemp -d -p .)
	docker run --rm -v "$(pwd)/$dir":/w -w /w --entrypoint=/bin/sh "$REDIS_IMG" -c "chown $container_user ."
	stat -c "%u %g" "$dir"
	sudo rm -rf "$dir"
}

# Detect how redis user and group from the container are mapped to the host ones
read -r REDIS_UID _ <<< "$(get_container_user_uid_gid_on_the_host redis:redis)"

if [ "$REDIS_UID" == "$HOST_UID" ]; then
	echo "Cannot test ownership as redis user uid is the same as current user"
	exit 1
fi

# Helper functions #

# Wait for Redis server or sentiel to be ready in a container by pinging it
# Arguments:
#   $1 - container name/id
# Returns:
#   0 if Redis responds with PONG within timeout
#   1 if timeout CONTAINER_INIT_WAIT occurs
wait_for_redis_server_in_container() {
	local container="$1"
	local timeout="${CONTAINER_INIT_WAIT:-3}"
	local elapsed=0
	local sleep_interval=0.1

	if [ -z "$container" ]; then
		return 1
	fi

	while [[ "$elapsed" < "$timeout" ]]; do
		# Try to ping Redis server
		if response=$(docker exec "$container" redis-cli ping 2>/dev/null) && [ "$response" = "PONG" ]; then
			return 0
		fi

		if response=$(docker exec "$container" redis-cli -p 26379 ping 2>/dev/null) && [ "$response" = "PONG" ]; then
			return 0
		fi

		# Sleep and increment elapsed time
		sleep "$sleep_interval"
		elapsed=$(awk "BEGIN {print $elapsed + $sleep_interval}")
	done

	echo "Timeout: Redis server did not respond within ${timeout}s"
	docker stop "$container" >/dev/null
	return 1
}

# creates one entry of directory structure
# used in combination with iterate_dir_structure_with
create_entry() {
	dir="$1"
	if [ "$type" = dir ]; then
		sudo mkdir -p "$dir/$entry"
	elif [ "$type" = file ]; then
		sudo touch "$dir/$entry"
	else
		echo "Unknown type '$type' for entry '$entry'"
		return 1
	fi
	sudo chmod "$initial_mode" "$dir/$entry"
	sudo chown "$initial_owner" "$dir/$entry"
}

# asserts ownership and permissions for one entry from directory structure
# used in combination with iterate_dir_structure_with
assert_entry() {
	dir="$1"
	msg="$2"
	actual_uid=$(sudo stat -c %u "$dir/$entry")
	actual_mode=0$(sudo stat -c '%a' "$dir/$entry")
	actual_mask=$(printf "0%03o" $(( actual_mode & expected_mode_mask )))
	assertEquals "$msg: Owner for $type '$entry'" "$expected_owner" "$actual_uid"
	assertEquals "$msg: Mode mask for $type '$entry'"  "$expected_mode_mask" "$actual_mask"
}

# Iterates over directory structure assigning variables and executing command
# from the arguments for each entry.
#
# Directory structure is the following form:
#   entry               type initial owner -> expected uid initial mode -> expected mode mask
#		.                   dir  $HOST_OWNER   -> $REDIS_UID   0555         -> 0700
#		appendonlydir       dir  $HOST_OWNER   -> $REDIS_UID   0333         -> 0600
#		dump.rdb            file $HOST_OWNER   -> $REDIS_UID   0333         -> 0600
iterate_dir_structure_with() {
	awk 'NF {print $1,$2,$3,$5,$6,$8}' \
		| while read -r \
				entry \
				type \
				initial_owner \
				expected_owner \
				initial_mode \
				expected_mode_mask; \
			do
		"$@"
	done
}

# Ownership and permissions test helper.
#
# This function tests the entrypoint.
#
# The idea is to test data and config files ownerhsip and permissions before and after container has started.
#
# The function creates temporary directory and uses --dir-structure (see iterate_dir_structure_with and create_entry)
# to create files and directories in this temporary dir.
#
# The temporary dir is mounted into the --mount-target inside the container.
#
# Container is started using REDIS_IMG and the function arguments as CMD.
#
# After container exits, all file permissions and ownership are checked using expected values from --dir-structure (see assert_entry)
#
# Additionally --extra-assert function is invoked if present.
#
# Arguments:
# < --mount-target DIR >
# [ --dir-structure STRING ]
# [ --extra-assert FUNCTION ]
# [ --docker-flags FLAGS ]
#
# Positional arguments:
# $docker_cmd
run_docker_and_test_ownership() {
	docker_flags=
	extra_assert=
	dir_structure=
	while [[ $# -gt 0 ]]; do
		case "$1" in
			--dir-structure)
			dir_structure="$2"
			shift 2
		;;
			--mount-target)
			mount_target="$2"
			shift 2
		;;
			--docker-flags)
			docker_flags="$2"
			shift 2
		;;
			--extra-assert)
			extra_assert="$2"
			shift 2
		;;
			--*)
			break
		;;
			*)
			break
		;;
		esac
	done
	docker_cmd="$*"

	if [ -z "$mount_target" ]; then
		fail "Mount target is empty"
		return 1
	fi

	dir=$(mktemp -d -p .)

	iterate_dir_structure_with create_entry "$dir" <<<"$dir_structure"

	docker_run="docker run --rm -v "$(pwd)/$dir":$mount_target $docker_flags $REDIS_IMG $docker_cmd"
	if [ "$TEST_VERBOSE" ]; then
		echo -e "\n#### ownership test: $docker_cmd"
		echo "running $docker_run"
		echo "Before:"
		sudo find "$dir" -exec ls -ald {} \+
	fi

	docker_output=$($docker_run 2>&1)

	if [ "$TEST_VERBOSE" ]; then
		echo "After:"
		sudo find "$dir" -exec ls -ald {} \+
		echo "Docker output:"
		echo "$docker_output"
	fi

	iterate_dir_structure_with assert_entry "$dir" "$docker_cmd" <<<"$dir_structure"

	if [ "$extra_assert" ]; then
		$extra_assert
	fi

	sudo rm -rf "$dir"
}

# running redis-server using different forms
# -v option will make redis-server to either return version or fail (if config has been provided)
# either one is OK for us
run_docker_and_test_ownership_with_common_flags_for_server() {
	run_docker_and_test_ownership "${common_flags[@]}" "$@" -v
	run_docker_and_test_ownership "${common_flags[@]}" redis-server "$@" -v
	run_docker_and_test_ownership "${common_flags[@]}" /usr/local/bin/redis-server "$@" -v
}

# running redis-sentinel using different forms and --dumb-option
# expecting sentinel to fail, it's ok as we are only interested in entrypoint testing here
run_docker_and_test_ownership_with_common_flags_for_sentinel() {
	run_docker_and_test_ownership "${common_flags[@]}" "$@" --sentinel --dumb-option
	run_docker_and_test_ownership "${common_flags[@]}" redis-sentinel "$@" --dumb-option
	run_docker_and_test_ownership "${common_flags[@]}" /usr/local/bin/redis-sentinel "$@" --dumb-option
	run_docker_and_test_ownership "${common_flags[@]}" redis-server "$@" --sentinel --dumb-option
	run_docker_and_test_ownership "${common_flags[@]}" /usr/local/bin/redis-server "$@" --sentinel --dumb-option
}

# start redis server or sentinel and check process uid and gid
run_redis_docker_and_check_uid_gid() {
	docker_flags=
	expected_cmd="redis-server"
	user=redis
	group=redis
	file_owner=

	while [[ $# -gt 0 ]]; do
		case "$1" in
			--user)
			user="$2"
			shift 2
		;;
			--group)
			group="$2"
			shift 2
		;;
			--expected-cmd)
			expected_cmd="$2"
			shift 2
		;;
			--docker-flags)
			docker_flags=$2
			shift 2
		;;
			--file-owner)
			file_owner="$2"
			shift 2
		;;
			--*)
			fail "Unknown flag $1"
			return 1
		;;
			*)
			break
		;;
		esac
	done

	if echo "$expected_cmd" | grep -q "sentinel"; then
		dir="$(readlink -f "$(mktemp -d -p .)")"
		touch "$dir/sentinel.conf"
		if [ "$file_owner" ]; then
			sudo chown -R "$file_owner" "$dir"
		fi
		docker_flags="-v $dir:/etc/sentinel $docker_flags"
	fi

	docker_cmd="$*"
	# shellcheck disable=SC2086
	container=$(docker run $docker_flags -d "$REDIS_IMG" $docker_cmd)
	ret=$?
	assertTrue "Container '$docker_flags $REDIS_IMG $docker_cmd' created" "[ $ret -eq 0 ]"
	wait_for_redis_server_in_container "$container" || return 1

	cmdline=$(docker exec "$container" cat /proc/1/cmdline|tr -d \\0)
	assertContains "$docker_flags $docker_cmd, cmdline: $cmdline" "$cmdline" "$expected_cmd"

	redis_user_uid=$(docker exec "$container" id -u "$user")
	redis_user_gid=$(docker exec "$container" id -g "$group")

	status=$(docker exec "$container" cat /proc/1/status)
	process_uid=$(echo "$status" | grep Uid | cut -f2)
	process_gid=$(echo "$status" | grep Gid | cut -f2)

	assertEquals "redis cmd '$docker_cmd', process uid" "$redis_user_uid" "$process_uid"
	assertEquals "redis cmd '$docker_cmd', process gid" "$redis_user_gid" "$process_gid"

	docker stop "$container" >/dev/null
	if [ "$dir" ]; then
		sudo rm -rf "$dir"
	fi
}

run_redis_docker_and_check_modules() {
	docker_cmd="$1"
	# shellcheck disable=SC2086
	container=$(docker run --rm -d "$REDIS_IMG" $docker_cmd)
	ret=$?
	assertTrue "Container '$docker_flags $REDIS_IMG $docker_cmd' created" "[ $ret -eq 0 ]"
	wait_for_redis_server_in_container "$container" || return 1

	info=$(docker exec "$container" redis-cli info)

	[ "$PLATFORM" ] && [ "$PLATFORM" != "amd64" ] && startSkipping
	assertContains "$info" "module:name=timeseries"
	assertContains "$info" "module:name=search"
	assertContains "$info" "module:name=bf"
	assertContains "$info" "module:name=vectorset"
	assertContains "$info" "module:name=ReJSON"

	docker stop "$container" >/dev/null
}

# helper assert function to check redis output
assert_redis_output_has_no_config_perm_error() {
	s="can't open config file"
	assertNotContains "cmd: $docker_cmd, docker output contains '$s': " "$docker_output" "$s"
}

assert_redis_v8() {
	# Accept both v=8 (normal) and v=255 (dev)
	if echo "$1" | grep -q "Redis server v=8"; then
		return 0
	elif echo "$1" | grep -q "Redis server v=255"; then
		return 0
	else
		assertContains "$1" "Redis server v=8/v255"
	fi
}

# Tests #

test_redis_version() {
	ret=$(docker run --rm "$REDIS_IMG" -v|tail -n 1)
	assert_redis_v8 "$ret"
}

test_data_dir_owner_and_perms_changed_by_server_when_data_is_RO() {
	dir_structure="
		.             dir  $HOST_OWNER -> $REDIS_UID 0555 -> 0700
		appendonlydir dir  $HOST_OWNER -> $REDIS_UID 0333 -> 0600
		dump.rdb      file $HOST_OWNER -> $REDIS_UID 0333 -> 0600
	"
	common_flags=(--dir-structure "$dir_structure" --mount-target /data)
	run_docker_and_test_ownership_with_common_flags_for_server
}

test_data_dir_owner_and_perms_changed_by_server_when_appendonlydir_contains_files() {
	dir_structure="
		.                     dir  $HOST_OWNER -> $REDIS_UID 0555 -> 0700
		appendonlydir         dir  $HOST_OWNER -> $REDIS_UID 0333 -> 0600
		appendonlydir/foo.aof dir  $HOST_OWNER -> $REDIS_UID 0333 -> 0600
		dump.rdb              file $HOST_OWNER -> $REDIS_UID 0333 -> 0600
	"
	common_flags=(--dir-structure "$dir_structure" --mount-target /data)
	run_docker_and_test_ownership_with_common_flags_for_server
}

test_data_dir_owner_and_perms_changed_by_server_when_data_is_empty_and_RO() {
	dir_structure="
		. dir  $HOST_OWNER -> $REDIS_UID 0555 -> 0700
	"
	common_flags=(--dir-structure "$dir_structure" --mount-target /data)
	run_docker_and_test_ownership_with_common_flags_for_server
}

test_data_dir_owner_and_perms_not_changed_by_server_when_data_is_RW() {
	dir_structure="
		.             dir  $HOST_OWNER -> $HOST_UID 0777 -> 0777
		appendonlydir dir  $HOST_OWNER -> $HOST_UID 0666 -> 0666
		dump.rdb      file $HOST_OWNER -> $HOST_UID 0666 -> 0666
	"
	common_flags=(--dir-structure "$dir_structure" --mount-target /data)
	run_docker_and_test_ownership_with_common_flags_for_server
}

test_data_dir_owner_and_perms_not_changed_by_server_when_data_contains_unknown_file() {
	dir_structure="
		.             dir  $HOST_OWNER -> $HOST_UID 0555 -> 0555
		appendonlydir dir  $HOST_OWNER -> $HOST_UID 0444 -> 0444
		dump.rdb      file $HOST_OWNER -> $HOST_UID 0444 -> 0444
		garbage.file  file $HOST_OWNER -> $HOST_UID 0444 -> 0444
	"
	common_flags=(--dir-structure "$dir_structure" --mount-target /data)
	run_docker_and_test_ownership_with_common_flags_for_server
}

test_data_dir_owner_and_perms_not_changed_by_server_when_data_contains_unknown_subdir() {
	dir_structure="
		.        dir  $HOST_OWNER -> $HOST_UID 0555 -> 0555
		somedir  dir  $HOST_OWNER -> $HOST_UID 0444 -> 0444
		dump.rdb file $HOST_OWNER -> $HOST_UID 0444 -> 0444
	"
	common_flags=(--dir-structure "$dir_structure" --mount-target /data)
	run_docker_and_test_ownership_with_common_flags_for_server
}

test_data_dir_owner_not_changed_when_sentinel() {
	dir_structure="
		.             dir  $HOST_OWNER -> $HOST_UID 0555 -> 0555
		appendonlydir dir  $HOST_OWNER -> $HOST_UID 0333 -> 0333
		dump.rdb      file $HOST_OWNER -> $HOST_UID 0333 -> 0333
	"
	common_flags=(--dir-structure "$dir_structure" --mount-target /data)
	run_docker_and_test_ownership_with_common_flags_for_sentinel
}


test_config_owner_not_changed_by_server_when_config_is_readable() {
	dir_structure="
		.          dir  $HOST_OWNER -> $HOST_UID 0555 -> 0555
		redis.conf file $HOST_OWNER -> $HOST_UID 0444 -> 0444
	"
	common_flags=(--dir-structure "$dir_structure" --mount-target /etc/redis)
	run_docker_and_test_ownership_with_common_flags_for_server /etc/redis/redis.conf
}

test_only_config_file_owner_and_perms_changed_by_server_when_only_config_is_not_readable() {
	dir_structure="
		.          dir  $HOST_OWNER -> $HOST_UID 0555 -> 0555
		redis.conf file $HOST_OWNER -> $REDIS_UID 0000 -> 0400
	"
	common_flags=(--dir-structure "$dir_structure" --mount-target /etc/redis)
	run_docker_and_test_ownership_with_common_flags_for_server /etc/redis/redis.conf
}

test_config_file_and_dir_owner_and_perms_changed_by_server_when_not_readable() {
	dir_structure="
		.          dir  $HOST_OWNER -> $REDIS_UID 0000 -> 0400
		redis.conf file $HOST_OWNER -> $REDIS_UID 0000 -> 0400
	"
	common_flags=(--dir-structure "$dir_structure" --mount-target /etc/redis)
	run_docker_and_test_ownership_with_common_flags_for_server /etc/redis/redis.conf
}

test_config_owner_and_perms_not_changed_when_unknown_file_exists() {
	dir_structure="
		.            dir  $HOST_OWNER -> $HOST_UID 0000 -> 0000
		redis.conf   file $HOST_OWNER -> $HOST_UID 0000 -> 0000
		garbage.file file $HOST_OWNER -> $HOST_UID 0000 -> 0000
	"

	common_flags=(--dir-structure "$dir_structure" --mount-target /etc/redis)
	run_docker_and_test_ownership_with_common_flags_for_server /etc/redis/redis.conf
	run_docker_and_test_ownership_with_common_flags_for_sentinel /etc/redis/redis.conf
}

test_config_owner_and_perms_not_changed_when_unknown_subdir_exists() {
	dir_structure="
		.          dir  $HOST_OWNER -> $HOST_UID 0000 -> 0000
		redis.conf file $HOST_OWNER -> $HOST_UID 0000 -> 0000
		some       dir  $HOST_OWNER -> $HOST_UID 0000 -> 0000
	"

	common_flags=(--dir-structure "$dir_structure" --mount-target /etc/redis)
	run_docker_and_test_ownership_with_common_flags_for_server /etc/redis/redis.conf
	run_docker_and_test_ownership_with_common_flags_for_sentinel /etc/redis/redis.conf
}

test_config_owner_and_perms_not_changed_by_sentinel_when_config_is_RW() {
	dir_structure="
		.             dir  $HOST_OWNER -> $HOST_UID 0777 -> 0777
		sentinel.conf file $HOST_OWNER -> $HOST_UID 0666 -> 0666
	"
	common_flags=(--dir-structure "$dir_structure" --mount-target /etc/redis/sentinel)
	run_docker_and_test_ownership_with_common_flags_for_sentinel /etc/redis/sentinel/sentinel.conf
}

test_config_file_and_dir_owner_and_perms_changed_by_sentinel_when_RO() {
	dir_structure="
		.             dir  $HOST_OWNER -> $REDIS_UID 0555 -> 0700
		sentinel.conf file $HOST_OWNER -> $REDIS_UID 0400 -> 0600
	"
	common_flags=(--dir-structure "$dir_structure" --mount-target /etc/redis/sentinel)
	run_docker_and_test_ownership_with_common_flags_for_sentinel /etc/redis/sentinel/sentinel.conf
}

test_config_dir_owner_and_perms_changed_by_sentinel_when_only_dir_is_RO() {
	dir_structure="
		.             dir  $HOST_OWNER -> $REDIS_UID 0555 -> 0700
		sentinel.conf file $HOST_OWNER -> $HOST_UID 0666 -> 0666
	"
	common_flags=(--dir-structure "$dir_structure" --mount-target /etc/redis/sentinel)
	run_docker_and_test_ownership_with_common_flags_for_sentinel /etc/redis/sentinel/sentinel.conf
}

test_config_owner_and_perms_changed_by_sentinel_when_config_is_WO() {
	dir_structure="
		.             dir  $HOST_OWNER -> $REDIS_UID 0333 -> 0700
		sentinel.conf file $HOST_OWNER -> $REDIS_UID 0222 -> 0600
	"
	common_flags=(--dir-structure "$dir_structure" --mount-target /etc/redis/sentinel)
	run_docker_and_test_ownership_with_common_flags_for_sentinel /etc/redis/sentinel/sentinel.conf
}

# test that entrypoint tries to start redis even when config is non existent dir
test_redis_start_reached_when_config_dir_does_not_exist() {
	assert_has_config_error() {
		# shellcheck disable=SC2317
		assertContains "$docker_output" "Fatal error, can't open config file"
		# shellcheck disable=SC2317
		assertContains "$docker_output" "No such file or directory"
	}
	common_flags=(--mount-target /etc/somewhere --extra-assert assert_has_config_error)
	run_docker_and_test_ownership_with_common_flags_for_server /etc/nowhere/redis.conf
}

test_redis_start_reached_when_chown_on_data_dir_is_denied() {
	assert_internal() {
		# shellcheck disable=SC2317
		assert_redis_v8 "$docker_output"
	}
	dir_structure="
		.        dir  $HOST_OWNER -> $HOST_UID 0333 -> 0700
		dump.rdb file root:root   -> 0      0222 -> 0222
	"
	common_flags=(--mount-target /data
		--dir-structure "$dir_structure"
		--extra-assert assert_internal
		--docker-flags "--cap-drop=chown"
	)
	run_docker_and_test_ownership_with_common_flags_for_server
}

test_data_dir_owner_and_perms_not_changed_by_server_when_data_is_RO_and_SKIP_FIX_PERMS_is_used() {
	dir_structure="
		.         dir  $HOST_OWNER -> $HOST_UID 0555 -> 0555
		datum.rdb file $HOST_OWNER -> $HOST_UID 0444 -> 0444
	"
	common_flags=(--mount-target /data
		--dir-structure "$dir_structure"
		--docker-flags "-e SKIP_FIX_PERMS=1"
	)
	run_docker_and_test_ownership_with_common_flags_for_server
}

test_config_owner_and_perms_not_changed_by_sentinel_when_config_is_RO_and_SKIP_FIX_PERMS_is_used() {
	dir_structure="
		.             dir  $HOST_OWNER -> $HOST_UID 0555 -> 0555
		sentinel.conf file $HOST_OWNER -> $HOST_UID 0444 -> 0444
	"
	common_flags=(--mount-target /etc/redis/sentinel
		--dir-structure "$dir_structure"
		--docker-flags "-e SKIP_FIX_PERMS=1"
	)
	run_docker_and_test_ownership_with_common_flags_for_sentinel /etc/redis/sentinel/sentinel.conf
}



test_redis_server_persistence_with_bind_mount() {
	dir=$(mktemp -d -p .)

	# make data directory non writable
	chmod 0444 "$dir"

	container=$(docker run --rm -d -v "$(pwd)/$dir":/data "$REDIS_IMG" --appendonly yes)
	ret=$?
	assertTrue "Container '$docker_flags $REDIS_IMG $docker_cmd' created" "[ $ret -eq 0 ]"
	wait_for_redis_server_in_container "$container" || return 1

	result=$(echo save | docker exec -i "$container" redis-cli)
	assertEquals "OK" "$result"

	# save container hash as a value
	result=$(echo "SET FOO $container" | docker exec -i "$container" redis-cli)
	assertEquals "OK" "$result"

	docker stop "$container" >/dev/null

	# change the owner
	sudo chown -R "$HOST_OWNER" "$dir"

	container2=$(docker run --rm -d -v "$(pwd)/$dir":/data "$REDIS_IMG")
	ret=$?
	assertTrue "Container '$docker_flags $REDIS_IMG $docker_cmd' created" "[ $ret -eq 0 ]"
	wait_for_redis_server_in_container "$container2" || return 1

	value=$(echo "GET FOO" | docker exec -i "$container2" redis-cli)
	assertEquals "$container" "$value"

	docker stop "$container2" >/dev/null

	sudo rm -rf "$dir"
}

test_redis_server_persistence_with_volume() {
	docker volume rm test_redis >/dev/null 2>&1 || :

	docker volume create test_redis >/dev/null

	# change owner of the data volume
	docker run --rm -v test_redis:/data --entrypoint=/bin/sh "$REDIS_IMG" -c 'chown -R 0:0 /data'

	container=$(docker run --rm -d -v test_redis:/data "$REDIS_IMG" --appendonly yes)
	ret=$?
	assertTrue "Container '$docker_flags $REDIS_IMG $docker_cmd' created" "[ $ret -eq 0 ]"
	wait_for_redis_server_in_container "$container" || return 1

	result=$(echo save | docker exec -i "$container" redis-cli)
	assertEquals "OK" "$result"

	# save container hash as a value
	result=$(echo "SET FOO $container" | docker exec -i "$container" redis-cli)
	assertEquals "OK" "$result"

	docker stop "$container" >/dev/null

	# change owner and permissions of files in data volume
	docker run --rm -v test_redis:/data --entrypoint=/bin/sh "$REDIS_IMG" -c 'chown -R 0:0 /data && chmod 0000 -R /data'

	container2=$(docker run --rm -d -v test_redis:/data "$REDIS_IMG")
	ret=$?
	assertTrue "Container '$docker_flags $REDIS_IMG $docker_cmd' created" "[ $ret -eq 0 ]"
	wait_for_redis_server_in_container "$container2" || return 1

	value=$(echo "GET FOO" | docker exec -i "$container2" redis-cli)
	assertEquals "$container" "$value"

	docker stop "$container2" >/dev/null

	docker volume rm test_redis >/dev/null || :
}

test_redis_process_uid_and_gid_are_redis() {
	run_redis_docker_and_check_uid_gid ""
	run_redis_docker_and_check_uid_gid redis-server
	run_redis_docker_and_check_uid_gid /usr/local/bin/redis-server

	run_redis_docker_and_check_uid_gid --expected-cmd redis-sentinel redis-sentinel /etc/sentinel/sentinel.conf
	run_redis_docker_and_check_uid_gid --expected-cmd redis-sentinel /usr/local/bin/redis-sentinel /etc/sentinel/sentinel.conf
	run_redis_docker_and_check_uid_gid --expected-cmd "[sentinel]" /etc/sentinel/sentinel.conf --sentinel
	run_redis_docker_and_check_uid_gid --expected-cmd "[sentinel]" redis-server /etc/sentinel/sentinel.conf --sentinel
	run_redis_docker_and_check_uid_gid --expected-cmd "[sentinel]" /usr/local/bin/redis-server /etc/sentinel/sentinel.conf --sentinel
}

test_redis_process_uid_and_gid_respects_docker_user_arg() {
	read -r daemon_user_uid _ <<< "$(get_container_user_uid_gid_on_the_host daemon:daemon)"

	# disable persistence as directory data dir would not be writable
	common_flags=(--user daemon --group daemon --docker-flags "--user daemon")
	run_redis_docker_and_check_uid_gid "${common_flags[@]}" "" --save ""
	run_redis_docker_and_check_uid_gid "${common_flags[@]}" redis-server --save ""
	run_redis_docker_and_check_uid_gid "${common_flags[@]}" /usr/local/bin/redis-server --save ""

	run_redis_docker_and_check_uid_gid "${common_flags[@]}" --file-owner "$daemon_user_uid" --expected-cmd redis-sentinel redis-sentinel /etc/sentinel/sentinel.conf
	run_redis_docker_and_check_uid_gid "${common_flags[@]}" --file-owner "$daemon_user_uid" --expected-cmd redis-sentinel /usr/local/bin/redis-sentinel /etc/sentinel/sentinel.conf
	run_redis_docker_and_check_uid_gid "${common_flags[@]}" --file-owner "$daemon_user_uid" --expected-cmd "[sentinel]" /etc/sentinel/sentinel.conf --sentinel
	run_redis_docker_and_check_uid_gid "${common_flags[@]}" --file-owner "$daemon_user_uid" --expected-cmd "[sentinel]" redis-server /etc/sentinel/sentinel.conf --sentinel
	run_redis_docker_and_check_uid_gid "${common_flags[@]}" --file-owner "$daemon_user_uid" --expected-cmd "[sentinel]" /usr/local/bin/redis-server /etc/sentinel/sentinel.conf --sentinel
}

test_redis_process_uid_and_gid_are_root_when_SKIP_DROP_PRIVS_is_used() {
	common_flags=(--user root --group root --docker-flags "-e SKIP_DROP_PRIVS=1")
	run_redis_docker_and_check_uid_gid "${common_flags[@]}" "" --save ""
	run_redis_docker_and_check_uid_gid "${common_flags[@]}" redis-server --save ""
	run_redis_docker_and_check_uid_gid "${common_flags[@]}" /usr/local/bin/redis-server --save ""

	run_redis_docker_and_check_uid_gid "${common_flags[@]}" --expected-cmd redis-sentinel redis-sentinel /etc/sentinel/sentinel.conf
	run_redis_docker_and_check_uid_gid "${common_flags[@]}" --expected-cmd redis-sentinel /usr/local/bin/redis-sentinel /etc/sentinel/sentinel.conf
	run_redis_docker_and_check_uid_gid "${common_flags[@]}" --expected-cmd "[sentinel]" /etc/sentinel/sentinel.conf --sentinel
	run_redis_docker_and_check_uid_gid "${common_flags[@]}" --expected-cmd "[sentinel]" redis-server /etc/sentinel/sentinel.conf --sentinel
	run_redis_docker_and_check_uid_gid "${common_flags[@]}" --expected-cmd "[sentinel]" /usr/local/bin/redis-server /etc/sentinel/sentinel.conf --sentinel
}

test_redis_server_modules_are_loaded() {
	run_redis_docker_and_check_modules
	run_redis_docker_and_check_modules redis-server
	run_redis_docker_and_check_modules /usr/local/bin/redis-server
}

# shellcheck disable=SC1091
. ./shunit2
