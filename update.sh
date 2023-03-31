#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$(readlink -f "$BASH_SOURCE")")"

versions=( "$@" )
if [ ${#versions[@]} -eq 0 ]; then
	versions=( */ )
fi
versions=( "${versions[@]%/}" )

packagesUrl='https://raw.githubusercontent.com/redis/redis-hashes/master/README'
packages="$(echo "$packagesUrl" | sed -r 's/[^a-zA-Z.-]+/-/g')"
trap "$(printf 'rm -f %q' "$packages")" EXIT
curl -fsSL "$packagesUrl" -o "$packages"

for version in "${versions[@]}"; do
	rcVersion="${version%-rc}"

	line="$(
		awk '
			{ gsub(/^redis-|[.]tar[.]gz$/, "", $2) }
			$1 == "hash" && $2 ~ /^'"$rcVersion"'([.]|$)/ { print }
		' "$packages" \
			| sort -rV \
			| head -1
	)"

	if [ -n "$line" ]; then
		fullVersion="$(cut -d' ' -f2 <<<"$line")"
		downloadUrl="$(cut -d' ' -f5 <<<"$line")"
		shaHash="$(cut -d' ' -f4 <<<"$line")"
		shaType="$(cut -d' ' -f3 <<<"$line")"
	elif [ "$version" != "$rcVersion" ] && fullVersion="$(
			git ls-remote --tags https://github.com/redis/redis.git "refs/tags/$rcVersion*" \
				| cut -d/ -f3 \
				| cut -d^ -f1 \
				| sort -urV \
				| head -1
	)" && [ -n "$fullVersion" ]; then
		downloadUrl="https://github.com/redis/redis/archive/$fullVersion.tar.gz"
		shaType='sha256'
		shaHash="$(curl -fsSL "$downloadUrl" | "${shaType}sum" | cut -d' ' -f1)"
	else
		echo >&2 "error: full version for $version cannot be determined"
		exit 1
	fi
	[ "$shaType" = 'sha256' ] || [ "$shaType" = 'sha1' ]

	echo "$version: $fullVersion"

	for variant in \
		alpine '' \
	; do
		dir="$version${variant:+/$variant}"
		[ -d "$dir" ] || continue
		template="Dockerfile${variant:+-$variant}.template"

		sed -r \
			-e 's/^(ENV REDIS_VERSION) .*/\1 '"$fullVersion"'/' \
			-e 's!^(ENV REDIS_DOWNLOAD_URL) .*!\1 '"$downloadUrl"'!' \
			-e 's/^(ENV REDIS_DOWNLOAD_SHA) .*/\1 '"$shaHash"'/' \
			-e 's!sha[0-9]+sum!'"$shaType"'sum!g' \
			"$template" > "$dir/Dockerfile"

		cp -a docker-entrypoint.sh "$dir/"
		if [ "$variant" = 'alpine' ]; then
			sed -i -e 's/gosu/su-exec/g' "$dir/docker-entrypoint.sh"
		fi
	done
done
