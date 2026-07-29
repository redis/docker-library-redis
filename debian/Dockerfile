FROM debian:trixie-slim

# add our user and group first to make sure their IDs get assigned consistently, regardless of whatever dependencies get added
RUN set -eux; \
	groupadd -r -g 999 redis; \
	useradd -r -g redis -u 999 redis

# runtime dependencies
RUN set -eux; \
	apt-get update; \
	apt-get install -y --no-install-recommends \
# add tzdata explicitly for https://github.com/docker-library/redis/issues/138 (see also https://bugs.debian.org/837060 and related)
		tzdata \
	; \
	rm -rf /var/lib/apt/lists/*

ENV REDIS_VERSION=8.10.0
ARG REDIS_DOWNLOAD_URL=https://github.com/redis/redis/releases/download/8.10.0/redis-full.tar.gz
ARG REDIS_DOWNLOAD_SHA=021973d690498682372505c8c0da934e010eb5ae7db9438dcf5a6d78a9e6a5b8

RUN set -eux; \
	\
	savedAptMark="$(apt-mark showmanual)"; \
	apt-get update; \
	apt-get install -y --no-install-recommends \
		ca-certificates \
		wget \
		dpkg-dev \
		gcc \
		g++ \
		libc6-dev \
		libssl-dev \
		libsystemd-dev \
		pkg-config \
		make; \
	\
	arch="$(dpkg --print-architecture | awk -F- '{ print $NF }')"; \
	case "$arch" in \
		'amd64' | 'arm64') BUILD_WITH_MODULES=yes ;; \
		*) echo >&2 "Modules are NOT supported! unsupported architecture: '$arch'"; BUILD_WITH_MODULES=no ;; \
	esac; \
	if [ "$BUILD_WITH_MODULES" = "yes" ]; then \
		echo 'deb http://deb.debian.org/debian trixie-backports main' > /etc/apt/sources.list.d/backports.list; \
		apt-get update; \
		apt-get install -y --no-install-recommends \
			git \
			cmake \
			python3 \
			python3-pip \
			python3-venv \
			python3-dev \
			unzip \
			rsync \
			automake \
			autoconf \
			libtool \
			g++; \
		apt-get install -y --no-install-recommends clang-21 lld-21 llvm-21; \
		export PATH="/usr/lib/llvm-21/bin:$PATH"; \
	fi; \
	\
	rm -f /etc/apt/sources.list.d/backports.list; \
	rm -rf /var/lib/apt/lists/*; \
	\
	wget -O redis.tar.gz "$REDIS_DOWNLOAD_URL"; \
	echo "$REDIS_DOWNLOAD_SHA *redis.tar.gz" | sha256sum -c -; \
	mkdir -p /usr/src/redis; \
	tar -xzf redis.tar.gz -C /usr/src/redis --strip-components=1; \
	rm redis.tar.gz; \
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
	case "${arch##*-}" in \
		amd64 | i386 | x32) extraJemallocConfigureFlags="$extraJemallocConfigureFlags --with-lg-page=12" ;; \
		*) extraJemallocConfigureFlags="$extraJemallocConfigureFlags --with-lg-page=16" ;; \
	esac; \
	extraJemallocConfigureFlags="$extraJemallocConfigureFlags --with-lg-hugepage=21"; \
	grep -F 'cd jemalloc && ./configure ' /usr/src/redis/deps/Makefile; \
	sed -ri 's!cd jemalloc && ./configure !&'"$extraJemallocConfigureFlags"' !' /usr/src/redis/deps/Makefile; \
	grep -F "cd jemalloc && ./configure $extraJemallocConfigureFlags " /usr/src/redis/deps/Makefile; \
	\
	export BUILD_TLS=yes; \
	if [ "$BUILD_WITH_MODULES" = "yes" ]; then \
		export LTO=1; \
# make deploy/build.sh bypass modules/Makefile, so install the pinned Rust toolchain here
		make -C /usr/src/redis/modules install-rust INSTALL_RUST_TOOLCHAIN=yes; \
		make -C /usr/src/redis -j "$(nproc)" deploy; \
# remove the toolchain from /usr/local so it neither bloats the image nor pollutes runtime-dep detection
		make -C /usr/src/redis/modules uninstall-rust INSTALL_RUST_TOOLCHAIN=yes; \
	else \
		make -C /usr/src/redis -j "$(nproc)" deploy redis; \
	fi; \
	rm -r /usr/src/redis; \
	\
	apt-mark auto '.*' > /dev/null; \
	[ -z "$savedAptMark" ] || apt-mark manual $savedAptMark > /dev/null; \
	find /usr/local -type f -executable -exec ldd '{}' ';' \
		| awk '/=>/ { so = $(NF-1); if (index(so, "/usr/local/") == 1) { next }; gsub("^/(usr/)?", "", so); printf "*%s\n", so }' \
		| sort -u \
		| xargs -r dpkg-query --search \
		| cut -d: -f1 \
		| sort -u \
		| xargs -r apt-mark manual \
	; \
	apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false; \
	rm -rf /var/cache/debconf/*; \
	\
	redis-cli --version; \
	redis-server --version

RUN mkdir /data && chown redis:redis /data
WORKDIR /data

COPY docker-entrypoint.sh /usr/local/bin/
ENTRYPOINT ["docker-entrypoint.sh"]

EXPOSE 6379
CMD ["redis-server"]