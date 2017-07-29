
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <vector>

#include <arpa/inet.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/types.h>

#include <fcntl.h>
#include <poll.h>
#include <pthread.h>
#include <sched.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <syslog.h>
#include <termios.h>
#include <time.h>
#include <unistd.h>

#include "util.h"
#include "mutex.h"
#include "RC.h"
#include "Telem.h"
#include "SysInfo.h"
#include "PairReq.h"
#include "PairRes.h"
#include "ParamStoredVals.h"
#include "ConfigStickAxes.h"
#include "SetTelemUnits.h"
#include "ConfigSweepTime.h"
#include "ButtonEventHandler.h"
#include "InputReport.h"
#include "ButtonFunctionCfg.h"
#include "SetShotInfo.h"
#include "Updater.h"
#include "LockoutState.h"
#include "AppConnected.h"
#include "SLIP.h"
#include "packetTypes.h"
#include "INIReader.h"
#include "net_wmm.h"
#ifdef INCLUDE_SERIAL_LOG
#include "SerialLog.h"
#endif // INCLUDE_SERIAL_LOG

using namespace std;

/***********************************************************************
Timeouts
***********************************************************************/
#define LOG_DT_US 10000000 // 10s

/***********************************************************************
Serial port name
***********************************************************************/
string serialPortName;

/***********************************************************************
Serial port receive buffer
***********************************************************************/
#define SERIAL_BUFSIZE 4096
#define MAX_SERIAL_MESSAGE_LEN 1024

/***********************************************************************
Thread IDs
***********************************************************************/
pthread_t upstream_ctx;
pthread_t downstream_ctx;

/***********************************************************************
Thread priorities
***********************************************************************/
#define UPSTREAM_PRIORITY 60
#define DOWNSTREAM_PRIORITY 56

/***********************************************************************
File descriptors
***********************************************************************/
int serial_fd;

#ifdef INCLUDE_SERIAL_LOG
/***********************************************************************
Serial port log
***********************************************************************/
SerialLog *serialLog;
unsigned serialLogSize;
unsigned serialLogTimeout_us;
#endif // INCLUDE_SERIAL_LOG

/***********************************************************************
The amount of data sent/received every cycle
***********************************************************************/
unsigned upBytes = 0;
unsigned upMsgs[PKT_ID_MAX + 1];
pthread_mutex_t mutex_upBytes;

/***********************************************************************
Handler objects
***********************************************************************/
RC *rc;
Telem *telem;
SysInfo *sysInfo;
PairReq *pairReq;
PairRes *pairRes;
ParamStoredVals *paramStoredVals;
ConfigStickAxes *configStickAxes;
SetTelemUnits *setTelemUnits;
ConfigSweepTime *configSweepTime;
ButtonEventHandler *btnEvt;
InputReport *inputReport;
ButtonFunctionCfg *btnFuncCfg;
SetShotInfo *setShotInfo;
Updater *updater;
LockoutState *lockoutState;
AppConnected *appConn;

/***********************************************************************
Debug control
***********************************************************************/
static uint32_t dbg_downHandler = 0;

/***********************************************************************
Function: void lock_thread_mem(uint32_t memsize)

Description: Locks memory in the thread so that stack faults don't cause
             timing jitter.
 ***********************************************************************/
static void lock_thread_mem(uint32_t memsize)
{
    uint8_t stackmem[memsize];

    mlockall(MCL_CURRENT | MCL_FUTURE);

    memset(stackmem, 0, sizeof(stackmem));
}

/***********************************************************************
Function: int serial_setup(int baudrate)

Description: The serial port initialization function.  This function
             initializes the serial port over which data is sent and
             received from the STM32.  A return of 0 indicates an error.
***********************************************************************/
int serial_setup(int baudrate)
{
    struct termios options;

    serial_fd = open(serialPortName.c_str(), O_RDWR | O_NOCTTY); // Blocking read

    if (serial_fd < 0) {
        syslog(LOG_ERR, "unable to open serial port %s", serialPortName.c_str());
        return 0;
    }

    // Configure port for 8N1 transmission
    tcgetattr(serial_fd, &options); // Gets the current options for the port
    switch (baudrate) {
    case 57600:
        cfsetspeed(&options, B57600);
        break;
    case 115200:
        cfsetspeed(&options, B115200);
        break;
    case 1500000:
        cfsetspeed(&options, B1500000);
        break;
    default:
        syslog(LOG_ERR, "unsupported baudrate %d", baudrate);
        return 0;
    }
    options.c_iflag &= ~(IGNBRK | BRKINT | ICRNL | INLCR | PARMRK | INPCK | ISTRIP | IXON);
    options.c_oflag &= ~(OCRNL | ONLCR | ONLRET | ONOCR | OFILL | OPOST);
    options.c_lflag &= ~(ECHO | ECHONL | ICANON | IEXTEN | ISIG);
    options.c_cflag &= ~(CSIZE | PARENB);
    options.c_cflag |= CS8;
    options.c_cc[VMIN] = 1;
    options.c_cc[VTIME] = 0;

    tcsetattr(serial_fd, TCSANOW, &options); // Set the new options for the port "NOW"

    syslog(LOG_INFO, "opened serial port %s", serialPortName.c_str());

    return 1;
}

static string msgToString(const char *msg, int msgLen)
{
    stringstream s;

    // dealing with the unknown; cap the number of bytes to log
    int printLen = msgLen;
    if (printLen > 8)
        printLen = 8;

    while (printLen-- > 0) {
        s << setfill('0') << setw(2) << hex << unsigned(*msg);
        if (printLen > 0)
            s << " ";
        msg++;
    }

    s << setfill(' ') << setw(0) << dec;

    if (msgLen > 8)
        s << "... (" << msgLen << " bytes long)";

    return s.str();
}

/***********************************************************************
Function: void *upstream_task(void*)

Description: The upstream thread task.  Checks for data available on the
             serial and calls the relevant handler.
***********************************************************************/
const int POLLTIMEOUT_MS = 10000;
void *upstream_task(void *)
{
    char buf[SERIAL_BUFSIZE];
    char msg[MAX_SERIAL_MESSAGE_LEN];
    struct pollfd fds[1];
    int pollrc;
    int i;
    int msgLen = 0;
    int readlen;
    SLIPDecoder *slipDec = new SLIPDecoder(msg, sizeof(msg));
    uint64_t now_us;
    uint64_t unknown_us = 0;
    unsigned unknown_skip_cnt = 0;
    bool in_sync = false;
    bool invalid_stick_inputs_logged = false;

    fds[0].fd = serial_fd;
    fds[0].events = POLLIN;

    lock_thread_mem(32764);

    while (true) {
        // Wait for available data, block until we get some or timeout
        pollrc = poll(fds, 1, POLLTIMEOUT_MS);

        if (pollrc > 0 && fds[0].revents & POLLIN) {
            // Check for any new incoming data, send over udp
            readlen = read(serial_fd, buf, SERIAL_BUFSIZE);
            if (readlen > 0) {
                for (i = 0; i < readlen; ++i) {
                    // Decode slip packets. Returns:
                    //  0 : packet in progress
                    // -1 : error in bytes stream, e.g. invalid sync sequence
                    // >0 : packet received
                    msgLen = slipDec->addByte(&buf[i]);
                    if (msgLen <= 0) {
                        if (msgLen < 0) {
                            syslog(LOG_INFO, "slip error - discarding data");
                            in_sync = false;
                        }
                        continue;
                    }

                    if (!in_sync) {
                        // First packet after an error (or init) is no good,
                        // since we generally did not start after a previous
                        // packet's sync. But at this point, we *did* just
                        // receive a sync, so we drop the current packet and
                        // go get the next one.
                        syslog(LOG_INFO, "slip - initial sync");
                        in_sync = true;
                        continue;
                    }

// OK, got a message

#ifdef INCLUDE_SERIAL_LOG
                    serialLog->log_packet(msg, msgLen, SerialLog::PKTFLG_UP);
#endif // INCLUDE_SERIAL_LOG

                    // syslog(LOG_INFO, "packet %d: %d bytes", int(msg[0]), msgLen);

                    // Get the packet type from the first byte
                    // When passing the message, skip the first byte
                    // which is the packet type.
                    unsigned up = 0;
                    switch (msg[0]) {
                    case PKT_ID_DSM_CHANNELS:
                        up = rc->upHandler(&msg[1], msgLen - 1);
                        break;
                    case PKT_ID_CALIBRATE:
                        break;
                    case PKT_ID_SYS_INFO:
                        up = sysInfo->upHandler(&msg[1], msgLen - 1);
                        break;
                    case PKT_ID_MAVLINK:
                        up = telem->upHandler(&msg[1], msgLen - 1);
                        break;
                    case PKT_ID_PAIR_CONFIRM:
                        up = pairReq->upHandler(&msg[1], msgLen - 1);
                        break;
                    // PKT_ID_PAIR_RESULT is never upstream
                    case PKT_ID_PARAM_STORED_VALS:
                        up = paramStoredVals->upHandler(&msg[1], msgLen - 1);
                        break;
                    case PKT_ID_SHUTDOWN_REQUEST:
                        // Call the system shutdown command
                        syslog(LOG_INFO, "STM32 requested shutdown");
                        system("shutdown -h now");
                        sleep(30); // should get killed in here
                        exit(1);   // init may restart us if we get here
                        break;
                    case PKT_ID_BUTTON_EVENT:
                        up = btnEvt->upHandler(&msg[1], msgLen - 1);
                        break;
                    case PKT_ID_INPUT_REPORT:
                        up = inputReport->upHandler(&msg[1], msgLen - 1);
                        break;
                    case PKT_ID_INVALID_STICK_INPUTS:
                        // polluting log - print one then ignore
                        if (!invalid_stick_inputs_logged) {
                            string s = msgToString(msg, msgLen);
                            syslog(LOG_INFO, "received invalid stick inputs message: %s",
                                   s.c_str());
                            invalid_stick_inputs_logged = true;
                        }
                        break;
                    case PKT_ID_NOP:
                    default:
                        // Print unknown messages, but max one per second
                        // Rate limit so if the STM32 firmware gets ahead
                        // and emits a new message, we don't soak the log.
                        now_us = clock_gettime_us(CLOCK_MONOTONIC);
                        if (now_us >= unknown_us) {
                            // okay to print it
                            string s = msgToString(msg, msgLen);
                            syslog(LOG_ERR, "unknown packet: %s", s.c_str());
                            if (unknown_skip_cnt != 0) {
                                syslog(LOG_ERR, "(%u more not printed)", unknown_skip_cnt);
                                unknown_skip_cnt = 0;
                            }
                            // don't print another for 1,000,000 usec
                            unknown_us = now_us + 1000000;
                        } else {
                            // too soon after the previous one; don't print
                            unknown_skip_cnt++;
                        }
                        break;
                    }
                    unsigned id = msg[0];
                    if (id > PKT_ID_MAX)
                        id = PKT_ID_MAX;
                    pthread_mutex_lock(&mutex_upBytes);
                    upMsgs[id]++; // upMsgs is [PKT_ID_MAX + 1]
                    upBytes += up;
                    pthread_mutex_unlock(&mutex_upBytes);
                }
            }
        } else if (pollrc == 0) {
            // timeout
            syslog(LOG_INFO, "no data received from STM32 for %d msec", POLLTIMEOUT_MS);
        }

    } // while (true)

    pthread_exit(NULL);
}

/**********************************************************************
Function: int start_upstream_thread(void)

Description: Starts the upstream thread
***********************************************************************/
int start_upstream_thread(void)
{
    int ret = 0;
    struct sched_param param;

    // Start the upstream thread
    pthread_create(&upstream_ctx, NULL, upstream_task, NULL);

    pthread_setname_np(upstream_ctx, "stm32_up");

    // upstream priority and schedule
    param.sched_priority = UPSTREAM_PRIORITY;
    if ((ret = pthread_setschedparam(upstream_ctx, SCHED_FIFO, &param)))
        syslog(LOG_ERR, "error %d setting upstream thread priority", ret);

    return ret;
}

/**********************************************************************
Function: void *downstream_task(void*)

Description: The downstream thread task.  Selects() on the set of
             fds and calls the relevant handler
***********************************************************************/
void *downstream_task(void *)
{
    int nfds = 0;
    int res = 0;
    fd_set fds;
    int bytesAvailable;
    struct timeval timeout;
    uint64_t log_last_us;
    unsigned downBytes = 0;

    lock_thread_mem(32764);

    log_last_us = clock_gettime_us(CLOCK_MONOTONIC);

    // Select() on the list of UDP FDs.
    while (1) {
        // Block until we get one
        // Generate the list of fds
        FD_ZERO(&fds);
        FD_SET(telem->getfd(), &fds);
        nfds = telem->getfd() + 1;

        FD_SET(pairReq->getfd(), &fds);
        if (pairReq->getfd() >= nfds)
            nfds = pairReq->getfd() + 1;

        FD_SET(pairRes->getfd(), &fds);
        if (pairRes->getfd() >= nfds)
            nfds = pairRes->getfd() + 1;

        FD_SET(sysInfo->getfd(), &fds);
        if (sysInfo->getfd() >= nfds)
            nfds = sysInfo->getfd() + 1;

        FD_SET(paramStoredVals->getfd(), &fds);
        if (paramStoredVals->getfd() >= nfds)
            nfds = paramStoredVals->getfd() + 1;

        FD_SET(configStickAxes->getfd(), &fds);
        if (configStickAxes->getfd() >= nfds)
            nfds = configStickAxes->getfd() + 1;

        FD_SET(setTelemUnits->getfd(), &fds);
        if (setTelemUnits->getfd() >= nfds)
            nfds = setTelemUnits->getfd() + 1;

        FD_SET(configSweepTime->getfd(), &fds);
        if (configSweepTime->getfd() >= nfds)
            nfds = configSweepTime->getfd() + 1;

        FD_SET(btnFuncCfg->getfd(), &fds);
        if (btnFuncCfg->getfd() >= nfds)
            nfds = btnFuncCfg->getfd() + 1;

        FD_SET(setShotInfo->getfd(), &fds);
        if (setShotInfo->getfd() >= nfds)
            nfds = setShotInfo->getfd() + 1;

        FD_SET(updater->getfd(), &fds);
        if (updater->getfd() >= nfds)
            nfds = updater->getfd() + 1;

        FD_SET(lockoutState->getfd(), &fds);
        if (lockoutState->getfd() >= nfds)
            nfds = lockoutState->getfd() + 1;

        FD_SET(appConn->getfd(), &fds);
        if (appConn->getfd() >= nfds)
            nfds = appConn->getfd() + 1;

        // select timeout 0.1 sec
        // (note that select can update timeout)
        // need to time out, so if downlink stops we still see stats
        timeout.tv_sec = 0;
        timeout.tv_usec = 100000;

        res = select(nfds, &fds, NULL, NULL, &timeout);

        if (res > 0) {

            // Run the appropriate downstream handler
            if (FD_ISSET(telem->getfd(), &fds)) {
                // record the amount of data we download
                ioctl(telem->getfd(), FIONREAD, &bytesAvailable);

                // Run the handler
                telem->downHandler(serial_fd);

                // Record the amount of data we got down
                downBytes += bytesAvailable;
            }

            if (FD_ISSET(pairReq->getfd(), &fds)) {
                // Don't increment the amount of data we send here
                syslog(LOG_INFO, "pair request going down");
                pairReq->downHandler(serial_fd, dbg_downHandler);
            }

            if (FD_ISSET(pairRes->getfd(), &fds)) {
                // Don't increment the amount of data we send here
                syslog(LOG_INFO, "pair result going down");
                pairRes->downHandler(serial_fd, dbg_downHandler);
            }

            if (FD_ISSET(sysInfo->getfd(), &fds)) {
                // Don't increment the amount of data we send here
                sysInfo->downHandler(serial_fd, dbg_downHandler);
            }

            if (FD_ISSET(paramStoredVals->getfd(), &fds))
                paramStoredVals->downHandler(serial_fd, dbg_downHandler);

            if (FD_ISSET(configStickAxes->getfd(), &fds))
                configStickAxes->downHandler(serial_fd, dbg_downHandler);

            if (FD_ISSET(setTelemUnits->getfd(), &fds))
                setTelemUnits->downHandler(serial_fd, dbg_downHandler);

            if (FD_ISSET(configSweepTime->getfd(), &fds))
                configSweepTime->downHandler(serial_fd, dbg_downHandler);

            if (FD_ISSET(btnFuncCfg->getfd(), &fds))
                btnFuncCfg->downHandler(serial_fd, dbg_downHandler);

            if (FD_ISSET(setShotInfo->getfd(), &fds))
                setShotInfo->downHandler(serial_fd, dbg_downHandler);

            if (FD_ISSET(updater->getfd(), &fds)) {
                // Don't increment the amount of data we send here
                syslog(LOG_INFO, "updater message going down");
                updater->downHandler(serial_fd, dbg_downHandler);
            }

            if (FD_ISSET(lockoutState->getfd(), &fds)) {
                // Don't increment the amount of data we send here
                syslog(LOG_INFO, "lockout state message going down");
                lockoutState->downHandler(serial_fd, dbg_downHandler);
            }

            if (FD_ISSET(appConn->getfd(), &fds)) {
                // Don't increment the amount of data we send here
                syslog(LOG_INFO, "app connected message going down");
                appConn->downHandler(serial_fd, dbg_downHandler);
            }
        }

        // check for time to log status logging
        uint64_t now_us = clock_gettime_us(CLOCK_MONOTONIC);
        uint64_t delta = now_us - log_last_us;
        if (delta >= LOG_DT_US) {
            unsigned newUpBytes;
            unsigned newUpMsgs[PKT_ID_MAX + 1];
            pthread_mutex_lock(&mutex_upBytes);
            newUpBytes = upBytes;
            upBytes = 0;
            memcpy(newUpMsgs, upMsgs, sizeof(newUpMsgs));
            memset(upMsgs, 0, sizeof(upMsgs));
            pthread_mutex_unlock(&mutex_upBytes);

            log_last_us = now_us;

            // normally need about 20 chars tops
            char msg[200];
            int x = sizeof(msg) - 1;
            char *p = msg;
            memset(msg, 0, sizeof(msg));
            for (int i = 0; i <= PKT_ID_MAX; i++) {
                if (newUpMsgs[i] != 0) {
                    int k = snprintf(p, x, "%d:%u ", i, newUpMsgs[i]);
                    if (k >= x)
                        break;
                    x -= k;
                    p += k;
                }
            }

            syslog(LOG_INFO, "up %s%u B %0.2f KB/s dn %u B %0.2f KB/s", msg, newUpBytes,
                   newUpBytes / 1024.0 / (delta / 1e6), downBytes,
                   downBytes / 1024.0 / (delta / 1e6));

            downBytes = 0;
        }
    }

    pthread_exit(NULL);
}

/**********************************************************************
Function: int start_downstream_thread(void)

Description: Starts the downstream thread
***********************************************************************/
int start_downstream_thread(void)
{
    int ret = 0;
    struct sched_param param;

    // Start the downstream thread
    pthread_create(&downstream_ctx, NULL, downstream_task, NULL);

    pthread_setname_np(downstream_ctx, "stm32_down");

    // Set the priority and scheduler
    memset(&param, 0, sizeof(param));
    param.sched_priority = DOWNSTREAM_PRIORITY;
    if ((ret = pthread_setschedparam(downstream_ctx, SCHED_FIFO, &param)))
        syslog(LOG_ERR, "error %d setting downstream thread priority", ret);

    return ret;
}

/**********************************************************************
Function: bool readSoloIP(string filename, string *ip)

Description: Reads the Solo's IP address from the solo Address File
***********************************************************************/
bool readSoloIP(string filename, string *ip)
{
    ifstream fd;

    // Open the address file, return false if its not been created yet
    fd.open(filename.c_str(), ios::in);
    if (!fd)
        return false;

    ip->clear();
    fd >> *ip;
    fd.close();

    return true;
}

/**********************************************************************
Function: int main(void)

Description: The main function.  Initializes and runs the serial and
             UDP threads.
***********************************************************************/
int main(void)
{
    int rcDestPort;
    int rcUpTos;
    int mavDestPort;
    int sysDestPort;
    int pairReqDestPort;
    int pairResDestPort;
    int paramStoredValsDestPort;
    int configStickAxesDestPort;
    int setTelemUnitsDestPort;
    string setTelemUnitsSetting;
    int telemLogGap;
    int telemLogDelayMax;
    string telemLogDelayFile;
    int configSweepTimeDestPort;
    int btnEvtDestPort;
    int inputReportDestPort;
    int btnFuncCfgDestPort;
    int setShotInfoDestPort;
    int updaterDestPort;
    int lockoutStateDestPort;
    int appConnDestPort;
    int baudrate;
    string soloIPAddr;
    bool haveSoloIP = false;

    openlog("stm32", LOG_NDELAY, LOG_LOCAL0);

    syslog(LOG_INFO, "main: starting: built " __DATE__ " " __TIME__);

    /* Parse the sololink.conf file for serial port, source IPs and ports */
    INIReader reader("/etc/sololink.conf");

    if (reader.ParseError() < 0) {
        syslog(LOG_ERR, "main: can't load /etc/sololink.conf");
        return -1;
    }

    /* Get all parameter info */
    serialPortName = reader.Get("solo", "stm32Dev", "/dev/ttymxc1");
    rcDestPort = reader.GetInteger("solo", "rcDestPort", 5005);
    rcUpTos = reader.GetInteger("solo", "rcUpTos", 0xff);
    mavDestPort = reader.GetInteger("solo", "mavDestPort", 5015);
    sysDestPort = reader.GetInteger("solo", "sysDestPort", 5012);
    pairReqDestPort = reader.GetInteger("solo", "pairReqDestPort", 5013);
    pairResDestPort = reader.GetInteger("solo", "pairResDestPort", 5014);
    paramStoredValsDestPort = reader.GetInteger("solo", "paramStoredValsDestPort", 5011);
    configStickAxesDestPort = reader.GetInteger("solo", "configStickAxesDestPort", 5010);
    setTelemUnitsDestPort = reader.GetInteger("solo", "setTelemUnitsDestPort", 5024);
    setTelemUnitsSetting = reader.Get("solo", "uiUnits", "metric");
    telemLogGap = reader.GetInteger("solo", "telemLogGap", 1000000);
    syslog(LOG_INFO, "logging telemetry gaps >= %d msec", (telemLogGap + 500) / 1000);
    telemLogDelayMax =
        reader.GetInteger("solo", "telemLogDelayMax", 100000); // 100,000 is ~20 minutes, 6.4 MB
    telemLogDelayFile = reader.Get("solo", "telemLogDelayFile", "");
    if (telemLogDelayFile != "")
        syslog(LOG_INFO, "main: logging packet delays to %s (%d records per file)",
               telemLogDelayFile.c_str(), telemLogDelayMax);
    configSweepTimeDestPort = reader.GetInteger("solo", "configSweepTimeDestPort", 5022);
    btnEvtDestPort = reader.GetInteger("solo", "buttonEventDestPort", 5016);
    inputReportDestPort = reader.GetInteger("solo", "inputReportDestPort", 5021);
    btnFuncCfgDestPort = reader.GetInteger("solo", "buttonFunctionConfigDestPort", 5017);
    setShotInfoDestPort = reader.GetInteger("solo", "setShotInfoDestPort", 5018);
    updaterDestPort = reader.GetInteger("solo", "updaterDestPort", 5019);
    lockoutStateDestPort = reader.GetInteger("solo", "lockoutStateDestPort", 5020);
    appConnDestPort = reader.GetInteger("solo", "appConnDestPort", 5026);
    baudrate = reader.GetInteger("solo", "stm32Baud", 115200);
    dbg_downHandler = reader.GetInteger("solo", "dbg_downHandler", 0);
    if (dbg_downHandler != 0)
        syslog(LOG_INFO, "main: dbg_downHandler=0x%08x", dbg_downHandler);

#ifdef INCLUDE_SERIAL_LOG
    // serial log
    serialLogSize = reader.GetInteger("solo", "serialLogSize", 50000);
    serialLogTimeout_us = reader.GetInteger("solo", "serialLogTimeout_us", 1000000);

    serialLog = new SerialLog(serialLogSize, serialLogTimeout_us);
#endif // INCLUDE_SERIAL_LOG

    // shared variable mutex
    if (mutex_init(&mutex_upBytes) != 0) {
        syslog(LOG_ERR, "main: can't initialize mutex");
        return -1;
    }

    // initialize all the handler objects

    // The RC destination address gets updated by the Solo IP address file. We don't
    // send any data to the Solo until we've got that address
    rc = new RC("", rcDestPort, rcUpTos);
    telem = new Telem("127.0.0.1", mavDestPort, telemLogGap, telemLogDelayMax, telemLogDelayFile);
    sysInfo = new SysInfo("127.0.0.1", sysDestPort);
    pairReq = new PairReq("127.0.0.1", pairReqDestPort);
    pairRes = new PairRes("127.0.0.1", pairResDestPort);
    paramStoredVals = new ParamStoredVals(paramStoredValsDestPort);
    configStickAxes = new ConfigStickAxes(configStickAxesDestPort);
    setTelemUnits = new SetTelemUnits(setTelemUnitsDestPort);
    configSweepTime = new ConfigSweepTime(configSweepTimeDestPort);
    btnEvt = new ButtonEventHandler(btnEvtDestPort);
    inputReport = new InputReport(inputReportDestPort, 1);
    btnFuncCfg = new ButtonFunctionCfg(btnFuncCfgDestPort);
    setShotInfo = new SetShotInfo(setShotInfoDestPort);
    updater = new Updater("127.0.0.1", updaterDestPort);
    lockoutState = new LockoutState(lockoutStateDestPort);
    appConn = new AppConnected("127.0.0.1", appConnDestPort);

    /* Start the serial port */
    if (!serial_setup(baudrate)) {
        syslog(LOG_ERR, "main: unable to initialize serial port");
        return -1;
    }

    /* Start the upstream and downstream threads */
    start_downstream_thread();
    start_upstream_thread();

    // Send a ping to get the STM32 information in the log
    sysInfo->ping();

    // Set the telemetry display units
    setTelemUnits->set(setTelemUnitsSetting);

    // The main while() loop just becomes a thread monitor.  If any thread dies,
    // exit and let inittab restart us
    // We also check to see if the solo IP address has been written yet
    while (true) {
        if (pthread_kill(upstream_ctx, 0) != 0 || pthread_kill(downstream_ctx, 0) != 0) {
            syslog(LOG_ERR, "a thread is not running, exiting");
            exit(0);
        }

        // Check the Solo IP address file
        if (!haveSoloIP) {
            haveSoloIP = readSoloIP("/var/run/solo.ip", &soloIPAddr);
            if (haveSoloIP) {
                syslog(LOG_INFO, "got solo ip: %s", soloIPAddr.c_str());
                rc->setSoloIP(&soloIPAddr);
            }
        }

        // We also "ping" the STM32 occasionally to make sure its still talking to us.
        sysInfo->ping();

        // Long sleep
        sleep(1);
    }

    return -1;
}
