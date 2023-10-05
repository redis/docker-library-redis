#!/usr/bin/env bash
set -Eeuo pipefail

# we will support at most two entries in each of these lists, and both should be in descending order
supportedDebianSuites=(
	bookworm
)
supportedAlpineVersions=(
	3.18
)
defaultDebianSuite="${supportedDebianSuites[0]}"
declare -A debianSuites=(
	#[7.2]='3.17'
)
defaultAlpineVersion="${supportedAlpineVersions[0]}"
declare -A alpineVersions=(
	#[14]='3.16'
)

gosuVersion='1.16'

cd "$(dirname "$(readlink -f "$BASH_SOURCE")")"

versions=( "$@" )
if [ ${#versions[@]} -eq 0 ]; then
	versions=( */ )
	json='{}'
else
	json="$(< versions.json)"
fi
versions=( "${versions[@]%/}" )

packagesBase='https://raw.githubusercontent.com/redis/redis-hashes/master/README'

declare -A packages=

fetch_package_list() {
	local -; set +x # make sure running with "set -x" doesn't spam the terminal with the raw package lists

	# normal (GA) releases end up in the "main" component of upstream's repository
	if [ -z "${packages}" ]; then
		packages="$(curl -fsSL "$packagesBase")"
	fi
}
get_version() {
	local version="$1"; shift

	rcVersion="${version%-rc}"

	line="$(
		awk '
			{ gsub(/^redis-|[.]tar[.]gz$/, "", $2) }
			$1 == "hash" && $2 ~ /^'"$rcVersion"'([.]|$)/ { print }
		' <<< "$packages" \
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
}

for version in "${versions[@]}"; do
	export version

	versionAlpineVersion="${alpineVersions[$version]:-$defaultAlpineVersion}"
	versionDebianSuite="${debianSuites[$version]:-$defaultDebianSuite}"
	export versionAlpineVersion versionDebianSuite

	doc="$(jq -nc '{
		alpine: env.versionAlpineVersion,
		debian: env.versionDebianSuite,
	}')"

	fetch_package_list
	get_version "$version"

	for suite in "${supportedDebianSuites[@]}"; do
		export suite
		doc="$(jq <<<"$doc" -c '
			.variants += [ env.suite ]
		')"
	done

	for alpineVersion in "${supportedAlpineVersions[@]}"; do
		doc="$(jq <<<"$doc" -c --arg v "$alpineVersion" '
			.variants += [ "alpine" + $v ]
		')"
	done

	echo "$version: $fullVersion"

	export fullVersion shaType shaHash downloadUrl gosuVersion
	json="$(jq <<<"$json" -c --argjson doc "$doc" '
		.[env.version] = ($doc + {
			version: env.fullVersion,
			downloadUrl: env.downloadUrl,
			(env.shaType): env.shaHash,
			"gosu": {
				version: env.gosuVersion
			}
		})
	')"
done

jq <<<"$json" -S . > versions.json
