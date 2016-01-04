#!/bin/bash
set -e

cd "$(dirname "$(readlink -f "$BASH_SOURCE")")"

versions=( "$@" )
if [ ${#versions[@]} -eq 0 ]; then
	versions=( */ )
fi
versions=( "${versions[@]%/}" )

packagesUrl='https://raw.githubusercontent.com/antirez/redis-hashes/master/README'
packages="$(echo "$packagesUrl" | sed -r 's/[^a-zA-Z.-]+/-/g')"
curl -fsSL "$packagesUrl" > "$packages"

travisEnv=
for version in "${versions[@]}"; do
	line="$(awk '/^hash redis-'"$version"\.'/' "$packages" | sort -rV | head -1)"
	fullVersion="$(echo "$line" | cut -d' ' -f2 | sed -r 's/^redis-|\.tar\..*$//g')"
	downloadUrl="$(echo "$line" | cut -d' ' -f5 | sed 's/[\/&]/\\&/g')"
	shaHash="$(echo "$line" | cut -d' ' -f4)"
	[ "$(echo "$line" | cut -d' ' -f3)" = 'sha1' ]
	
	(
		set -x
		sed -ri '
			s/^(ENV REDIS_VERSION) .*/\1 '"$fullVersion"'/;
			s/^(ENV REDIS_DOWNLOAD_URL) .*/\1 '"$downloadUrl"'/;
			s/^(ENV REDIS_DOWNLOAD_SHA1) .*/\1 '"$shaHash"'/
		' "$version"/{,*/}Dockerfile
	)
	for variant in alpine 32bit; do
		[ -d "$version/$variant" ] || continue
		travisEnv='\n  - VERSION='"$version VARIANT=$variant$travisEnv"
	done
	travisEnv='\n  - VERSION='"$version VARIANT=$travisEnv"
done

travis="$(awk -v 'RS=\n\n' '$1 == "env:" { $0 = "env:'"$travisEnv"'" } { printf "%s%s", $0, RS }' .travis.yml)"
echo "$travis" > .travis.yml

rm "$packages"
