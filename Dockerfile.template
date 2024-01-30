{{ include ".template-helper-functions" -}}
{{ if env.variant == "alpine" then ( -}}
FROM alpine:{{ .alpine.version }}
{{ ) else ( -}}
FROM debian:{{ .debian.version }}-slim
{{ ) end -}}

# add our user and group first to make sure their IDs get assigned consistently, regardless of whatever dependencies get added
{{ if env.variant == "alpine" then ( -}}
RUN set -eux; \
# alpine already has a gid 999, so we'll use the next id
	addgroup -S -g 1000 redis; \
	adduser -S -G redis -u 999 redis
{{ ) else ( -}}
RUN set -eux; \
	groupadd -r -g 999 redis; \
	useradd -r -g redis -u 999 redis
{{ ) end -}}

# runtime dependencies
{{ if env.variant == "alpine" then ( -}}
RUN set -eux; \
	apk add --no-cache \
# add tzdata for https://github.com/docker-library/redis/issues/138
		tzdata \
	;
{{ ) else ( -}}
RUN set -eux; \
	apt-get update; \
	apt-get install -y --no-install-recommends \
# add tzdata explicitly for https://github.com/docker-library/redis/issues/138 (see also https://bugs.debian.org/837060 and related)
		tzdata \
	; \
	rm -rf /var/lib/apt/lists/*
{{ ) end -}}

# grab gosu for easy step-down from root
# https://github.com/tianon/gosu/releases
ENV GOSU_VERSION {{ .gosu.version }}
RUN set -eux; \
{{ if env.variant == "alpine" then ( -}}
	apk add --no-cache --virtual .gosu-fetch gnupg; \
	arch="$(apk --print-arch)"; \
{{ ) else ( -}}
	savedAptMark="$(apt-mark showmanual)"; \
	apt-get update; \
	apt-get install -y --no-install-recommends ca-certificates gnupg wget; \
	rm -rf /var/lib/apt/lists/*; \
	arch="$(dpkg --print-architecture | awk -F- '{ print $NF }')"; \
{{ ) end -}}
	case "$arch" in \
{{
	[
		.gosu.arches
		| to_entries[]
		| (
			if env.variant == "alpine" then
				{
					# https://dl-cdn.alpinelinux.org/alpine/edge/main/
					# https://dl-cdn.alpinelinux.org/alpine/latest-stable/main/
					amd64: "x86_64",
					arm32v6: "armhf",
					arm32v7: "armv7",
					arm64v8: "aarch64",
					i386: "x86",
					ppc64le: "ppc64le",
					riscv64: "riscv64",
					s390x: "s390x",
				}
			else
				{
					# https://salsa.debian.org/dpkg-team/dpkg/-/blob/main/data/cputable
					# https://wiki.debian.org/ArchitectureSpecificsMemo#Architecture_baselines
					# http://deb.debian.org/debian/dists/unstable/main/
					# http://deb.debian.org/debian/dists/stable/main/
					# https://deb.debian.org/debian-ports/dists/unstable/main/
					amd64: "amd64",
					arm32v5: "armel",
					arm32v7: "armhf",
					arm64v8: "arm64",
					i386: "i386",
					mips64le: "mips64el",
					ppc64le: "ppc64el",
					riscv64: "riscv64",
					s390x: "s390x",
				}
			end
		)[.key] as $arch
		| select($arch)
		| .value
		| (
-}}
		{{ $arch | @sh }}) url={{ .url | @sh }}; sha256={{ .sha256 | @sh }} ;; \
{{
		)
	] | add
-}}
		*) echo >&2 "error: unsupported gosu architecture: '$arch'"; exit 1 ;; \
	esac; \
	wget -O /usr/local/bin/gosu.asc "$url.asc"; \
	wget -O /usr/local/bin/gosu "$url"; \
	echo "$sha256 */usr/local/bin/gosu" | sha256sum -c -; \
	export GNUPGHOME="$(mktemp -d)"; \
	gpg --batch --keyserver hkps://keys.openpgp.org --recv-keys B42F6819007F00F88E364FD4036A9C25BF357DD4; \
	gpg --batch --verify /usr/local/bin/gosu.asc /usr/local/bin/gosu; \
	gpgconf --kill all; \
	rm -rf "$GNUPGHOME" /usr/local/bin/gosu.asc; \
{{ if env.variant == "alpine" then ( -}}
	apk del --no-network .gosu-fetch; \
{{ ) else ( -}}
	apt-mark auto '.*' > /dev/null; \
	[ -z "$savedAptMark" ] || apt-mark manual $savedAptMark > /dev/null; \
	apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false; \
{{ ) end -}}
	chmod +x /usr/local/bin/gosu; \
	gosu --version; \
	gosu nobody true

ENV REDIS_VERSION {{ .version }}
ENV REDIS_DOWNLOAD_URL {{ .url }}
ENV REDIS_DOWNLOAD_SHA {{ .sha256 // error("no sha256 for \(.version) (\(env.version))") }}

RUN set -eux; \
	\
{{ if env.variant == "alpine" then ( -}}
	apk add --no-cache --virtual .build-deps \
		coreutils \
		dpkg-dev dpkg \
		gcc \
		linux-headers \
		make \
		musl-dev \
		openssl-dev \
# install real "wget" to avoid:
#   + wget -O redis.tar.gz https://download.redis.io/releases/redis-6.0.6.tar.gz
#   Connecting to download.redis.io (45.60.121.1:80)
#   wget: bad header line:     XxhODalH: btu; path=/; Max-Age=900
		wget \
	; \
{{ ) else ( -}}
	savedAptMark="$(apt-mark showmanual)"; \
	apt-get update; \
	apt-get install -y --no-install-recommends \
		ca-certificates \
		wget \
		\
		dpkg-dev \
		gcc \
		libc6-dev \
		libssl-dev \
		make \
	; \
	rm -rf /var/lib/apt/lists/*; \
{{ ) end -}}
	\
	wget -O redis.tar.gz "$REDIS_DOWNLOAD_URL"; \
	echo "$REDIS_DOWNLOAD_SHA *redis.tar.gz" | sha256sum -c -; \
	mkdir -p /usr/src/redis; \
	tar -xzf redis.tar.gz -C /usr/src/redis --strip-components=1; \
	rm redis.tar.gz; \
	\
# disable Redis protected mode [1] as it is unnecessary in context of Docker
# (ports are not automatically exposed when running inside Docker, but rather explicitly by specifying -p / -P)
# [1]: https://github.com/redis/redis/commit/edd4d555df57dc84265fdfb4ef59a4678832f6da
	grep -E '^ *createBoolConfig[(]"protected-mode",.*, *1 *,.*[)],$' /usr/src/redis/src/config.c; \
	sed -ri 's!^( *createBoolConfig[(]"protected-mode",.*, *)1( *,.*[)],)$!\10\2!' /usr/src/redis/src/config.c; \
	grep -E '^ *createBoolConfig[(]"protected-mode",.*, *0 *,.*[)],$' /usr/src/redis/src/config.c; \
# for future reference, we modify this directly in the source instead of just supplying a default configuration flag because apparently "if you specify any argument to redis-server, [it assumes] you are going to specify everything"
# see also https://github.com/docker-library/redis/issues/4#issuecomment-50780840
# (more exactly, this makes sure the default behavior of "save on SIGTERM" stays functional by default)
	\
# https://github.com/jemalloc/jemalloc/issues/467 -- we need to patch the "./configure" for the bundled jemalloc to match how Debian compiles, for compatibility
# (also, we do cross-builds, so we need to embed the appropriate "--build=xxx" values to that "./configure" invocation)
	gnuArch="$(dpkg-architecture --query DEB_BUILD_GNU_TYPE)"; \
	extraJemallocConfigureFlags="--build=$gnuArch"; \
# https://salsa.debian.org/debian/jemalloc/-/blob/c0a88c37a551be7d12e4863435365c9a6a51525f/debian/rules#L8-23
	dpkgArch="$(dpkg --print-architecture)"; \
	case "${dpkgArch##*-}" in \
		amd64 | i386 | x32) extraJemallocConfigureFlags="$extraJemallocConfigureFlags --with-lg-page=12" ;; \
		*) extraJemallocConfigureFlags="$extraJemallocConfigureFlags --with-lg-page=16" ;; \
	esac; \
	extraJemallocConfigureFlags="$extraJemallocConfigureFlags --with-lg-hugepage=21"; \
	grep -F 'cd jemalloc && ./configure ' /usr/src/redis/deps/Makefile; \
	sed -ri 's!cd jemalloc && ./configure !&'"$extraJemallocConfigureFlags"' !' /usr/src/redis/deps/Makefile; \
	grep -F "cd jemalloc && ./configure $extraJemallocConfigureFlags " /usr/src/redis/deps/Makefile; \
	\
	export BUILD_TLS=yes; \
	make -C /usr/src/redis -j "$(nproc)" all; \
	make -C /usr/src/redis install; \
	\
# TODO https://github.com/redis/redis/pull/3494 (deduplicate "redis-server" copies)
	serverMd5="$(md5sum /usr/local/bin/redis-server | cut -d' ' -f1)"; export serverMd5; \
	find /usr/local/bin/redis* -maxdepth 0 \
		-type f -not -name redis-server \
		-exec sh -eux -c ' \
			md5="$(md5sum "$1" | cut -d" " -f1)"; \
			test "$md5" = "$serverMd5"; \
		' -- '{}' ';' \
		-exec ln -svfT 'redis-server' '{}' ';' \
	; \
	\
	rm -r /usr/src/redis; \
	\
{{ if env.variant == "alpine" then ( -}}
	runDeps="$( \
		scanelf --needed --nobanner --format '%n#p' --recursive /usr/local \
			| tr ',' '\n' \
			| sort -u \
			| awk 'system("[ -e /usr/local/lib/" $1 " ]") == 0 { next } { print "so:" $1 }' \
	)"; \
	apk add --no-network --virtual .redis-rundeps $runDeps; \
	apk del --no-network .build-deps; \
{{ ) else ( -}}
	apt-mark auto '.*' > /dev/null; \
	[ -z "$savedAptMark" ] || apt-mark manual $savedAptMark > /dev/null; \
	find /usr/local -type f -executable -exec ldd '{}' ';' \
		| awk '/=>/ { so = $(NF-1); if (index(so, "/usr/local/") == 1) { next }; gsub("^/(usr/)?", "", so); print so }' \
		| sort -u \
		| xargs -r dpkg-query --search \
		| cut -d: -f1 \
		| sort -u \
		| xargs -r apt-mark manual \
	; \
	apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false; \
{{ ) end -}}
	\
	redis-cli --version; \
	redis-server --version; \
	\
	echo {{
		{
			name: "redis-server",
			version: .version,
			params: (
				if env.variant == "alpine" then
					{
						os_name: "alpine",
						os_version: .alpine.version,
					}
				else
					{
						os_name: "debian",
						os_version: .debian.version,
					}
				end
			),
			licenses: [
				"BSD-3-Clause"
			]
		} | sbom | tostring | @sh
	}} > /usr/local/redis.spdx.json

RUN mkdir /data && chown redis:redis /data
VOLUME /data
WORKDIR /data

COPY docker-entrypoint.sh /usr/local/bin/
ENTRYPOINT ["docker-entrypoint.sh"]

EXPOSE 6379
CMD ["redis-server"]
