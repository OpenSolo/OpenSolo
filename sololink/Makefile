
SUBDIRS = flightcode wifi
SUBDIRS_BUILD = $(SUBDIRS:%=%_build)
SUBDIRS_CLEAN = $(SUBDIRS:%=%_clean)

# SUBDIRS2 should eventually be same as SUBDIRS when all are formatted

SUBDIRS2 = flightcode
SUBDIRS_FMT = $(SUBDIRS2:%=%_fmt)
SUBDIRS_FMT_DIFF = $(SUBDIRS2:%=%_fmt-diff)

all: $(SUBDIRS_BUILD)

build: $(SUBDIRS_BUILD)
$(SUBDIRS_BUILD):
	$(MAKE) -C $(@:%_build=%)

clean: $(SUBDIRS_CLEAN)
$(SUBDIRS_CLEAN):
	$(MAKE) -C $(@:%_clean=%) clean

fmt: $(SUBDIRS_FMT)
$(SUBDIRS_FMT):
	$(MAKE) -C $(@:%_fmt=%) fmt

fmt-diff: $(SUBDIRS_FMT_DIFF)
$(SUBDIRS_FMT_DIFF):
	$(MAKE) -C $(@:%_fmt-diff=%) fmt-diff

.PHONY: $(SUBDIRS) $(SUBDIRS_BUILD) $(SUBDIRS_CLEAN) $(SUBDIRS_FMT) $(SUBDIRS_FMT_DIFF)
