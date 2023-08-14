# BUILD redisfab/redis:${REDIS_VER}-${ARCH}-${OSNICK}

ARG REDIS_VER=5.0.12
ARG REDIS_MAJOR=5.0
ARG OS=debian:bullseye-slim
ARG OSNICK=bullseye

# ARCH=x64|arm64v8|arm32v7
ARG ARCH=x64

ARG UID=999

#----------------------------------------------------------------------------------------------
FROM ${OS} as builder

ARG REDIS_VER
ARG REDIS_MAJOR
ARG OS
ARG OSNICK
ARG ARCH

RUN echo "Building Redis v${REDIS_VER} on ${OSNICK} (${OS}) for ${ARCH}"
RUN uname -a; cat /etc/os-release

RUN if [ -f /root/.profile ]; then sed -ie 's/mesg n/tty -s \&\& mesg -n/g' /root/.profile; fi
SHELL ["/bin/bash", "-l", "-c"]

WORKDIR /build

ADD deps/ /build/deps/
ADD ${REDIS_MAJOR}/system-setup.py /build/

# ENV REDIS_DEPENDS "ca-certificates dirmngr gnupg wget gcc libc6-dev make"

RUN /build/deps/readies/bin/getbash
RUN /build/deps/readies/bin/getupdates
RUN /build/deps/readies/bin/getpy3
RUN	/build/system-setup.py

RUN gcc --version

ENV GOSU_VERSION 1.16
RUN set -ex ;\
	/build/deps/readies/bin/getgosu ;\
	gosu --version; \
	gosu nobody true

ENV REDIS_VERSION ${REDIS_VER}
ENV REDIS_DOWNLOAD_URL https://github.com/redis/redis/archive/${REDIS_VER}.tar.gz
# ENV REDIS_DOWNLOAD_URL http://download.redis.io/releases/redis-${REDIS_VER}.tar.gz
ENV REDIS_DOWNLOAD_SHA 2139009799d21d8ff94fc40b7f36ac46699b9e1254086299f8d3b223ca54a375

# for redis-sentinel see: http://redis.io/topics/sentinel
RUN set -ex; \
	wget -q -O redis.tar.gz "$REDIS_DOWNLOAD_URL"; \
	mkdir -p /usr/src/redis; \
	tar -xzf redis.tar.gz -C /usr/src/redis --strip-components=1

#	echo "$REDIS_DOWNLOAD_SHA *redis.tar.gz" | sha256sum -c -;

# Disable Redis protected mode [1] as it is unnecessary in context of Docker
# (ports are not automatically exposed when running inside Docker, but rather explicitly by specifying -p / -P)
# [1]: https://github.com/antirez/redis/commit/edd4d555df57dc84265fdfb4ef59a4678832f6da

ADD ${REDIS_MAJOR}/redis.patch /usr/src/redis/
RUN set -ex ;\
	cd /usr/src/redis ;\
	patch -p1 -i redis.patch

# For future reference, we modify this directly in the source instead of just supplying a default
# configuration flag because apparently "if you specify any argument to redis-server,
# [it assumes] you are going to specify everything".
# See also https://github.com/docker-library/redis/issues/4#issuecomment-50780840
# (more exactly, this makes sure the default behavior of "save on SIGTERM" stays functional by default)

# note: ARCH may break build if non-empty

RUN set -ex; \
	/build/deps/readies/bin/runn ARCH= make V=1 -C /usr/src/redis all; \
	/build/deps/readies/bin/runn make -C /usr/src/redis install

#----------------------------------------------------------------------------------------------
FROM ${OS}

ARG REDIS_VER
ARG REDIS_MAJOR
ARG ARCH
ARG OSNICK
ARG UID

RUN echo "Building redisfab/redis-${ARCH}-${OSNICK}:${REDIS_VER} UID=${UID}"

COPY platforms/setup.${OSNICK} /usr/local/bin/docker-setup
RUN chmod +x /usr/local/bin/docker-setup
RUN /usr/local/bin/docker-setup
RUN rm /usr/local/bin/docker-setup

# Add our user and group first to make sure their IDs get assigned consistently,
# regardless of whatever dependencies get added
RUN set -xe; \
    if [ -f /sbin/groupadd ] || [ -f /usr/sbin/groupadd ]; then \
        groupadd -r -g ${UID} redis && useradd -r -g redis -u ${UID} redis ;\
    else \
        addgroup --gid ${UID} redis && adduser --system --uid ${UID} redis ;\
    fi

COPY --from=builder /usr/local/ /usr/local/

RUN mkdir /data && chown redis:redis /data
VOLUME /data
WORKDIR /data

COPY ${REDIS_MAJOR}/docker-entrypoint.sh /usr/local/bin/
RUN chmod 755 /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]
EXPOSE 6379
CMD ["redis-server"]
