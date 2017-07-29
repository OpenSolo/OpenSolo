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

VPATH = ../util ../ini ../ini/cpp

INCS = -I../util -I../ini -I../ini/cpp

CFLAGS += -Wall $(INCS)
CXXFLAGS += -Wall $(INCS)

LIBS = -lpthread -lrt

SRCS_CPP = telem_ctrl.cpp
SRCS_CPP += INIReader.cpp
SRCS_CPP += telem_dest.cpp
SRCS_C = arp_table.c hostapd_ctrl.c util.c ini.c
SRCS_C += mutex.c
SRCS_C += syslog.c

OBJS = $(SRCS_CPP:.cpp=.o) $(SRCS_C:.c=.o)

MAIN = telem_ctrl

all: $(MAIN)

$(MAIN): $(OBJS)
	$(LINK.cpp) -o $(MAIN) $(OBJS) $(LIBS)

clean:
	$(RM) *.o *~ $(MAIN)

BASE := ../..

fmt:
	@python $(BASE)/tools/build/clang-format-run.py --apply

fmt-diff:
	@python $(BASE)/tools/build/clang-format-run.py

.PHONY: all clean fmt fmt-diff
