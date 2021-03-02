.NOTPARALLEL:

# 5.0.x|6.0.x|5|6
VERSION ?= 6.0.11
# LATEST=1
# MASTER=1

OS ?= debian:buster-slim

# OSNICK=buster|stretch|trusty|xenial|bionic|centos6|centos7|centos8|fedora30
OSNICK ?= buster

ifeq ($(patsubst 4%,4,$(VERSION)),4)
MAJOR=6.0
else ifeq ($(patsubst 5%,5,$(VERSION)),5)
MAJOR=5.0
else ifeq ($(patsubst 6%,6,$(VERSION)),6)
MAJOR=6.0
else
$(info Strange Redis version: $(VERSION))
endif

# latest version on 5.0
# curl -s "https://api.github.com/repos/antirez/redis/tags" | jq '.[].name'  |cut -d\" -f2|grep "^5\.0"|head -1

ARCH:=$(shell ./deps/readies/bin/platform --arch)

ifeq ($(ARCH),x64)
#
else ifeq ($(CROSS),1)
$(error Cannot cross-build on ARM)
endif

#----------------------------------------------------------------------------------------------

OS.trusty=ubuntu:trusty
OS.xenial=ubuntu:xenial
OS.bionic=ubuntu:bionic
OS.focal=ubuntu:focal
OS.stretch=debian:stretch-slim
OS.buster=debian:buster-slim
OS.centos6=centos:6
OS.centos7=centos:7
OS.centos8=centos:8
OS.fedora=fedora:30
OS.fedora30=fedora:30
OS.rhel7.4=rhel:7.4
OS=$(OS.$(OSNICK))

ifeq ($(OS),)
$(error Probably wrong OSNICK specified ($(OSNICK)))
endif

#----------------------------------------------------------------------------------------------

UID.centos7=997
UID.centos8=997
UID.fedora=989
UID.fedora30=989
UID.rhel7.4=800
ifeq ($(UID.$(OSNICK)),)
UID=999
else
UID=$(UID.$(OSNICK))
endif

#----------------------------------------------------------------------------------------------

REPO=redisfab
STEM=$(REPO)/redis

DOCKER ?= docker

BUILD_OPT=--rm
# --squash

ifeq ($(CACHE),0)
CACHE_ARG=--no-cache
endif

#----------------------------------------------------------------------------------------------

ifneq ($(CROSS),1)

define targets # (1=OP, 2=op)
$(1)_TARGETS :=
$(1)_TARGETS += $(2)_native
endef

else # cross

define targets # (1=OP, 2=op)
$(1)_TARGETS :=
$(1)_TARGETS += $(if $(findstring $(X64),1),$(2)_native)
$(1)_TARGETS += $(if $(findstring $(ARM7),1),$(2)_arm32v7)
$(1)_TARGETS += $(if $(findstring $(ARM8),1),$(2)_arm64v8)

$(1)_TARGETS += $$(if $$(strip $$($(1)_TARGETS)),,$(2)_arm32v7 $(2)_arm64v8)
endef

endif # cross

$(eval $(call targets,BUILD,build))
$(eval $(call targets,PUBLISH,publish))

#----------------------------------------------------------------------------------------------

define build_native
build_native:
	@$(DOCKER) pull $(OS)
	@$(DOCKER) build $(BUILD_OPT) -t $(STEM):$(VERSION)-$(ARCH)-$(OSNICK) -f $(MAJOR)/Dockerfile \
		$(CACHE_ARG) \
		--build-arg ARCH=$(ARCH) \
		--build-arg OS=$(OS) \
		--build-arg OSNICK=$(OSNICK) \
		--build-arg UID=$(UID) \
		--build-arg REDIS_VER=$(VERSION) \
		.
		
	@$(DOCKER) tag $(STEM):$(VERSION)-$(ARCH)-$(OSNICK) $(STEM):$(MAJOR)-latest-$(ARCH)-$(OSNICK)

.PHONY: build_native
endef

define build_arm # (1=arch)
build_$(1): 
	@$(DOCKER) build $(BUILD_OPT) -t $(STEM)-xbuild:$(VERSION)-$(1)-$(OSNICK) -f $(MAJOR)/Dockerfile.arm \
		--build-arg ARCH=$(1) \
		--build-arg OSNICK=$(OSNICK) \
		--build-arg UID=$(UID) \
		--build-arg REDIS_VER=$(VERSION) \
		.
	@$(DOCKER) tag $(STEM)-xbuild:$(VERSION)-$(1)-$(OSNICK) $(STEM)-xbuild:$(MAJOR)-latest-$(1)-$(OSNICK)

.PHONY: build_$(1)
endef

#----------------------------------------------------------------------------------------------

define publish_native
publish_native:
	@$(DOCKER) push $(STEM):$(VERSION)-$(ARCH)-$(OSNICK)
	@$(DOCKER) push $(STEM):$(MAJOR)-latest-$(ARCH)-$(OSNICK)

.PHONY: publish_native
endef

define publish_arm # (1=arch)
publish_$(1):
	@$(DOCKER) push $(STEM)-xbuild:$(VERSION)-$(1)-$(OSNICK)
	@$(DOCKER) push $(STEM)-xbuild:$(MAJOR)-latest-$(1)-$(OSNICK)

.PHONY: publish_$(1)
endef

#----------------------------------------------------------------------------------------------

all: build publish commons

commons:
	$(MAKE) $(DO) VERSION=5.0 LATEST=1
	$(MAKE) $(DO) VERSION=5.0 MASTER=1
	$(MAKE) $(DO) VERSION=6.0 LATEST=1
	$(MAKE) $(DO) VERSION=6.0 MASTER=1

build: $(BUILD_TARGETS)

$(eval $(call build_native))
ifeq ($(CROSS),1)
$(eval $(call build_arm,arm64v8))
$(eval $(call build_arm,arm32v7))
endif

publish: $(PUBLISH_TARGETS)

$(eval $(call publish_native))
ifeq ($(CROSS),1)
$(eval $(call publish_arm,arm64v8))
$(eval $(call publish_arm,arm32v7))
endif

#----------------------------------------------------------------------------------------------

define HELP
make [build|publish] [CROSS=1] [X64=1|ARM8=1|ARM7=1] [OSNICK=<nick> | OS=<os>] [VERSION=<ver>] [ARGS...]

build    Build image(s)
publish  Push image(s) to Docker Hub
commons  Build common versions (with DO="<operations>")

Arguments:
CROSS=1       Perform cross-platform builds (typically, ARM7/8 on x64)
OSNICK=nick   nick=buster|stretch|xenial|bionic|centos6|centos7|centos8|fedora30
OS=os         (optional) OS Docker image name (e.g., debian:buster-slim)
VERSION=ver   Redis version (e.g. $(VERSION))
MASTER=1      Build sources from master branch ("edge" version)
LATEST=1      Build the latest version of branch given by VERSION
TEST=1        Run tests after build
CACHE=0       Build without cache


endef

help:
	$(file >/tmp/help,$(HELP))
	@cat /tmp/help
	@rm -f /tmp/help

#----------------------------------------------------------------------------------------------

.PHONY: all build publish help
