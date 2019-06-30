.NOPARALLEL:

VERSION ?= 5.0.5
OSNICK ?= stretch
REPO=redisfab

BUILD_OPT=--rm --squash

define build_x64
docker build $(BUILD_OPT) -t $(REPO)/redis-x64-$(OSNICK)-xbuild:$(VERSION) -f 5.0/Dockerfile 5.0
docker tag $(REPO)/redis-x64-$(OSNICK)-xbuild:$(VERSION) $(REPO)/redis-x64-$(OSNICK)-xbuild:latest
endef

define build_arm # (1=arch)
docker build $(BUILD_OPT) -t $(REPO)/redis-$(1)-$(OSNICK)-xbuild:$(VERSION) -f 5.0/Dockerfile.arm 5.0
docker tag $(REPO)/redis-$(1)-$(OSNICK)-xbuild:$(VERSION) $(REPO)/redis-$(1)-$(OSNICK)-xbuild:latest
endef

define push
docker push $(REPO)/redis-$(1)-$(OSNICK)-xbuild:$(VERSION)
docker push $(REPO)/redis-$(1)-$(OSNICK)-xbuild:latest
endef

.PHONY: all build public

all: build

build:
	$(call build_x64)
	$(call build_arm,arm32v7)
	$(call build_arm,arm64v8)

publish:
	$(call push,x64)
	$(call push,arm32v7)
	$(call push,arm64v8)
