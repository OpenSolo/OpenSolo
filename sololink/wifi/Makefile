# To cross compile:
#
# Set up as usual for bitbake:
# $ . setup-environment build
#
# In the build directory:
# $ bitbake meta-ide-support
# $ . tmp/environment-setup-cortexa9hf-vfp-neon-poky-linux-gnueabi
#
# Now a make in this directory should work.

VPATH = ../flightcode/util

INCROOT = $(OECORE_TARGET_SYSROOT)/usr/include
CFLAGS += -Wall

BIN1 = wifistats
BIN2 = survey_dump

all: $(BIN1) $(BIN2)

wifistats: CFLAGS += -I../flightcode/util
wifistats: wifistats.o util.o
	$(LINK.c) -o wifistats wifistats.o util.o

survey_dump: CFLAGS += -I$(INCROOT)/libnl3
survey_dump: LDLIBS += -lnl-3 -lnl-genl-3

clean:
	$(RM) *.o *~ $(BIN1) $(BIN2)

.PHONY: all clean
