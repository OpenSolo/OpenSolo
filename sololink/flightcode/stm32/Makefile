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

LIBS = -lpthread

SRCS_CPP = stm32.cpp
SRCS_CPP += PacketHandler.cpp
SRCS_CPP += PairReq.cpp
SRCS_CPP += RC.cpp
SRCS_CPP += SLIP.cpp
SRCS_CPP += SysInfo.cpp
SRCS_CPP += Telem.cpp
SRCS_CPP += ButtonEventMessage.cpp
SRCS_CPP += ButtonEventHandler.cpp
SRCS_CPP += InputReport.cpp
SRCS_CPP += ButtonFunctionCfg.cpp
SRCS_CPP += SetShotInfo.cpp
SRCS_CPP += TcpServer.cpp
SRCS_CPP += SoloMessage.cpp
SRCS_CPP += INIReader.cpp
SRCS_CPP += SerialLog.cpp
SRCS_CPP += CircularBuffer.cpp
SRCS_CPP += LockoutState.cpp
SRCS_CPP += ConfigStickAxes.cpp
SRCS_CPP += SetTelemUnits.cpp
SRCS_CPP += ConfigSweepTime.cpp
SRCS_C = ini.c
SRCS_C += util.c
SRCS_C += mutex.c
SRCS_C += syslog.c

OBJS = $(SRCS_CPP:.cpp=.o) $(SRCS_C:.c=.o)

MAIN = stm32

all: $(MAIN)

$(MAIN): $(OBJS)
	$(LINK.cpp) -o $(MAIN) $(OBJS) $(LIBS)

# This has run on a Linux host
CircularBufferTest: CircularBufferTest.o CircularBuffer.o
	$(LINK.cpp) -o CircularBufferTest CircularBufferTest.o CircularBuffer.o

# This has run on a Linux host
SerialLogTest: SerialLogTest.o SerialLog.o CircularBuffer.o util.o
	$(LINK.cpp) -o SerialLogTest SerialLogTest.o SerialLog.o CircularBuffer.o util.o

clean:
	$(RM) *.o *~ $(MAIN) *Test

BASE := ../..

fmt:
	@python $(BASE)/tools/build/clang-format-run.py --apply

fmt-diff:
	@python $(BASE)/tools/build/clang-format-run.py

.PHONY: all clean fmt fmt-diff
