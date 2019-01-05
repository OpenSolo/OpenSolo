
SUBDIRS =
SUBDIRS += arp_table
SUBDIRS += dflog
SUBDIRS += dataflash_logger
SUBDIRS += hostapd_ctrl
SUBDIRS += pixrc
SUBDIRS += proc_top
SUBDIRS += rssi
SUBDIRS += stm32
SUBDIRS += telem
SUBDIRS += telem_ctrl
SUBDIRS += tlog
SUBDIRS += video/vid
SUBDIRS += video/app
SUBDIRS += video/hdmi
SUBDIRS += unlock
SUBDIRS += wdog

SUBDIRS_BUILD = $(SUBDIRS:%=%_build)
SUBDIRS_CLEAN = $(SUBDIRS:%=%_clean)

# SUBDIRS2 is SUBDIRS, plus directories that can be formatted but not built
SUBDIRS2 = $(SUBDIRS)
SUBDIRS2 += ini
SUBDIRS2 += ini/cpp
SUBDIRS2 += log
SUBDIRS2 += util

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
