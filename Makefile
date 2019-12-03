.NOTPARALLEL:

VERSION ?= 5.0.7

OS ?= debian:buster-slim

# OSNICK=buster|stretch|xenial|bionic|centos6|centos7|centos8|fedora30
OSNICK ?= buster

#----------------------------------------------------------------------------------------------

OS.xenial=ubuntu:xenial # 16
OS.bionic=ubuntu:bionic # 18
OS.stretch=debian:stretch-slim # 9
OS.buster=debian:buster-slim # 10
OS.centos6=centos:centos6
OS.centos7=centos:centos7
OS.centos8=centos:centos8
OS.fedora=fedora:30
OS.fedora30=fedora:30
OS=$(OS.$(OSNICK))

UID.centos7=997
UID.centos8=997
UID.fedora=989
UID.fedora30=989
ifeq ($(UID.$(OSNICK)),)
UID=999
else
UID=$(UID.$(OSNICK))
endif

REPO=redisfab
STEM=$(REPO)/redis

BUILD_OPT=--rm
# --squash

ifeq ($(CACHE),0)
CACHE_ARG=--no-cache
endif

#----------------------------------------------------------------------------------------------

define targets # (1=OP, 2=op)
$(1)_TARGETS :=
$(1)_TARGETS += $(if $(findstring $(X64),1),$(2)_x64)
$(1)_TARGETS += $(if $(findstring $(ARM7),1),$(2)_arm32v7)
$(1)_TARGETS += $(if $(findstring $(ARM8),1),$(2)_arm64v8)

$(1)_TARGETS += $$(if $$(strip $$($(1)_TARGETS)),,$(2)_arm32v7 $(2)_arm64v8)
endef

$(eval $(call targets,BUILD,build))
$(eval $(call targets,PUBLISH,publish))

#----------------------------------------------------------------------------------------------

define build_x64
build_x64:
	@docker build $(BUILD_OPT) -t $(STEM):$(VERSION)-x64-$(OSNICK) -f 5.0/Dockerfile \
		$(CACHE_ARG) \
		--build-arg ARCH=x64 \
		--build-arg OS=$(OS) \
		--build-arg OSNICK=$(OSNICK) \
		--build-arg UID=$(UID) \
		--build-arg REDIS_VER=$(VERSION) \
		.
		
	@docker tag $(STEM):$(VERSION)-x64-$(OSNICK) $(STEM):latest-x64-$(OSNICK)

.PHONY: build_x64
endef

define build_arm # (1=arch)
build_$(1): 
	@docker build $(BUILD_OPT) -t $(STEM)-xbuild:$(VERSION)-$(1)-$(OSNICK) -f 5.0/Dockerfile.arm \
		--build-arg ARCH=$(1) \
		--build-arg OSNICK=$(OSNICK) \
		--build-arg UID=$(UID) \
		--build-arg REDIS_VER=$(VERSION) \
		.
	@docker tag $(STEM)-xbuild:$(VERSION)-$(1)-$(OSNICK) $(STEM)-xbuild:latest-$(1)-$(OSNICK)

.PHONY: build_$(1)
endef

#----------------------------------------------------------------------------------------------

define publish_x64
publish_x64:
	@docker push $(STEM):$(VERSION)-x64-$(OSNICK)
	@docker push $(STEM):latest-x64-$(OSNICK)

.PHONY: publish_x64
endef

define publish_arm # (1=arch)
publish_$(1):
	@docker push $(STEM)-xbuild:$(VERSION)-$(1)-$(OSNICK)
	@docker push $(STEM)-xbuild:latest-$(1)-$(OSNICK)

.PHONY: publish_$(1)
endef

#----------------------------------------------------------------------------------------------

all: build publish

build: $(BUILD_TARGETS)

$(eval $(call build_x64))
$(eval $(call build_arm,arm64v8))
$(eval $(call build_arm,arm32v7))

publish: $(PUBLISH_TARGETS)

$(eval $(call publish_x64))
$(eval $(call publish_arm,arm64v8))
$(eval $(call publish_arm,arm32v7))

#----------------------------------------------------------------------------------------------

define HELP
make [build|publish] [X64=1|ARM8=1|ARM7=1] [OSNICK=<nick> | OS=<os>] [VERSION=<ver>] [ARGS...]

build    Build image(s)
publish  Push image(s) to Docker Hub

Arguments:
OS       OS Docker image name (e.g., debian:buster-slim)
OSNICK   buster|stretch|xenial|bionic|centos6|centos7|centos8|fedora30
VERSION  Redis version (e.g. $(VERSION))
TEST=1   Run tests after build
CACHE=0  Build without cache


endef

help:
	$(file >/tmp/help,$(HELP))
	@cat /tmp/help
	@rm -f /tmp/help

#----------------------------------------------------------------------------------------------

.PHONY: all build publish help
