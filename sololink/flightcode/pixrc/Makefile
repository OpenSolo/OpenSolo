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

VPATH = ../util ../command ../ini ../ini/cpp ../log

INCS = -I../util -I../command -I../ini -I../ini/cpp -I../log

CFLAGS += -Wall $(INCS)
CXXFLAGS += -Wall $(INCS)

LIBS = -lpthread -lrt

SRCS_CPP = pixrc.cpp
SRCS_CPP += Commander.cpp
SRCS_CPP += RcCommander.cpp
SRCS_CPP += RcLock.cpp
SRCS_CPP += INIReader.cpp Log.cpp
SRCS_C = util.c mutex.c ini.c rc_ipc.c net_stats.c
SRCS_C += file_util.c
SRCS_C += syslog.c

OBJS = $(SRCS_CPP:.cpp=.o) $(SRCS_C:.c=.o)

MAIN = pixrc

all: $(MAIN)

$(MAIN): $(OBJS)
	$(LINK.cpp) -o $(MAIN) $(OBJS) $(LIBS)

clean:
	$(RM) *.o *~ $(MAIN)
	$(RM) ../ini/*.o
	$(RM) ../ini/cpp/*.o
	$(RM) ../log/*.o

BASE := ../..

fmt:
	@python $(BASE)/tools/build/clang-format-run.py --apply

fmt-diff:
	@python $(BASE)/tools/build/clang-format-run.py

.PHONY: clean
