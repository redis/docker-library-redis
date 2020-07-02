.NOTPARALLEL:

# 5.0.x|6.0.x|5|6
VERSION ?= 6.0.5
# LATEST=1
# MASTER=1

OS ?= debian:buster-slim

# OSNICK=buster|stretch|xenial|bionic|centos6|centos7|centos8|fedora30
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

#----------------------------------------------------------------------------------------------

OS.xenial=ubuntu:xenial
OS.bionic=ubuntu:bionic
OS.stretch=debian:stretch-slim
OS.buster=debian:buster-slim
OS.centos6=centos:6
OS.centos7=centos:7
OS.centos8=centos:8
OS.fedora=fedora:30
OS.fedora30=fedora:30
OS.rhel7.4=rhel:7.4
OS=$(OS.$(OSNICK))

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
	@$(DOCKER) pull $(OS)
	@$(DOCKER) build $(BUILD_OPT) -t $(STEM):$(VERSION)-x64-$(OSNICK) -f $(MAJOR)/Dockerfile \
		$(CACHE_ARG) \
		--build-arg ARCH=x64 \
		--build-arg OS=$(OS) \
		--build-arg OSNICK=$(OSNICK) \
		--build-arg UID=$(UID) \
		--build-arg REDIS_VER=$(VERSION) \
		.
		
	@$(DOCKER) tag $(STEM):$(VERSION)-x64-$(OSNICK) $(STEM):$(MAJOR)-latest-x64-$(OSNICK)

.PHONY: build_x64
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

define publish_x64
publish_x64:
	@$(DOCKER) push $(STEM):$(VERSION)-x64-$(OSNICK)
	@$(DOCKER) push $(STEM):$(MAJOR)-latest-x64-$(OSNICK)

.PHONY: publish_x64
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
commons  Build common versions (with DO="<operations>")

Arguments:
OSNICK           buster|stretch|xenial|bionic|centos6|centos7|centos8|fedora30
OS               (optional) OS Docker image name (e.g., debian:buster-slim)
VERSION          Redis version (e.g. $(VERSION))
MASTER=1         Build sources from master branch ("edge" version)
LATEST=1         Build the latest version of branch given by VERSION
TEST=1           Run tests after build
CACHE=0          Build without cache


endef

help:
	$(file >/tmp/help,$(HELP))
	@cat /tmp/help
	@rm -f /tmp/help

#----------------------------------------------------------------------------------------------

.PHONY: all build publish help
