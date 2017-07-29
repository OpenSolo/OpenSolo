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

VPATH = ../util ../mavlink/c_library/ardupilotmega

INCS = -I../util -I../mavlink/c_library/ardupilotmega

CFLAGS += -Wall -O2 $(INCS)
CXXFLAGS += -Wall -O2 $(INCS)

SRCS_CPP = mavpkt.cpp
SRCS_C = util.c

OBJS = $(SRCS_CPP:.cpp=.o) $(SRCS_C:.c=.o)

MAIN = mavpkt

all: $(MAIN)

$(MAIN): $(OBJS)
	$(LINK.cpp) -o $(MAIN) $(OBJS) $(LIBS)

clean:
	$(RM) *.o *~ $(MAIN)

.PHONY: clean
