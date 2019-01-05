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

PKGCONFIG = `pkg-config gstreamer-0.10 --cflags --libs`

VPATH = ../../ini ../../ini/cpp

INCS = -I../../ini -I../../ini/cpp -I$(OECORE_TARGET_SYSROOT)/usr/include/libnl3

CFLAGS += -Wall $(INCS)
CXXFLAGS += -Wall $(INCS) $(PKGCONFIG)

LIBS = -lnl-3 -lnl-genl-3 

SRCS_CPP = INIReader.cpp
SRCS_CPP += vidlaunch.cpp
SRCS_CPP += 80211.cpp
SRCS_C += ini.c

OBJS = $(SRCS_CPP:.cpp=.o) $(SRCS_C:.c=.o)

MAIN = vidlaunch

all: $(MAIN)

$(MAIN): $(OBJS)
	  $(LINK.cpp) -o $(MAIN) $(OBJS) $(LIBS)

clean:
	  $(RM) *.o *~ $(MAIN) *Test

BASE := ../../..

fmt:
	@python $(BASE)/tools/build/clang-format-run.py --apply

fmt-diff:
	@python $(BASE)/tools/build/clang-format-run.py

.PHONY: all clean fmt fmt-diff
