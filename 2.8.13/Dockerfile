FROM debian:wheezy

# add our user and group first to make sure their IDs get assigned consistently, regardless of whatever dependencies get added
RUN groupadd -r redis && useradd -r -g redis redis

ENV REDIS_VERSION 2.8.13

RUN buildDeps='gcc libc6-dev make'; \
	set -x; \
	apt-get update && apt-get install -y $buildDeps curl --no-install-recommends \
	&& rm -rf /var/lib/apt/lists/* \
	&& mkdir -p /usr/src/redis \
	&& curl -sSL "http://download.redis.io/releases/redis-$REDIS_VERSION.tar.gz" \
		| tar -xzC /usr/src/redis --strip-components=1 \
	&& make -C /usr/src/redis \
	&& make -C /usr/src/redis install \
	&& rm -r /usr/src/redis \
	&& apt-get purge -y $buildDeps curl \
	&& apt-get autoremove -y

RUN mkdir /data && chown redis:redis /data
VOLUME /data
WORKDIR /data

USER redis
EXPOSE 6379
CMD [ "redis-server" ]
