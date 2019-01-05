#ifndef HOSTPROTOCOL_H
#define HOSTPROTOCOL_H

#include <string.h>

#include "packetbuffer.h"
#include "ringbuffer.h"
#include "stm32/usart.h"
#include "stm32/vectors.h"

#include "mavlink/c_library/ardupilotmega/mavlink.h"

class HostProtocol
{
public:
    HostProtocol(Usart u) :
        uart(u),
        txPending(false),
        txPacket(), rxPacket(),
        rxbuf(),
        stats(),
        lastRxByteWasEsc(false),
        synced(false),
        firstMsgRxed(false),
        hostRequest(Nop)
    {}

    enum MsgID {
        Nop,                // Empty packet
        DsmChannels,        // DSM channels to be sent to vehicle
        Calibrate,          // Calibration data - store in nonvolatile mem
        SysInfo,            // HW ID & version info
        Mavlink,            // Mavlink data
        SetRawIo,           // control whether RawIoReports should be sent
        RawIoReport,        // io measurements, for assembly testing
        PairRequest,        // vehicle pair button has been pushed
        PairConfirm,        // artoo user has confirmed pair request
        PairResult,         // pairing process completed
        ShutdownRequest,    // system has received a shutdown request from the user
        ParamStoredVals,    // request/report a Params::StoredValues structure (see params.h)
        OutputTest,         // read/write the LEDs, buzzer, vibe motor
        ButtonEvent,        // push button event
        InputReport,        // 16-bit inputs not included in DSM reports
        ConfigStickAxes,    // specify which sticks to use for which control axes
        ButtonFunctionCfg,  // specify the function of A/B/Loiter buttons
        SetShotInfo,        // set the current shot
        Updater,            // screens for update flow
        LockoutState,       // update the lockout state of the system
        SelfTest,           // request/response for factory self test
        ConfigSweepTime,    // specify bounds of camera sweep time
        GpioTest,           // used during factory test to enable/disable some gpio lines
        TestEvent,          // debug only for testing event behaviours
        SetTelemUnits,      // set telemetry units to metric/imperial
        InvalidStickInputs, // out of range stick values received
        SoloAppConnection,  // solo app connection status (connected/disconnected)
    };

    // mavlink packets set the upper bound of our size here
    // this means we're a little bit heavy, but we're not RAM starved yet...
    typedef PacketBuffer<MAVLINK_MAX_PACKET_LEN> Packet;

    static HostProtocol instance;

    void init();
    void enableTX();
    void disableTX();
    void requestTransaction();

    bool connected() const {
        return firstMsgRxed;
    }
    void onHostDisconnected() {
        firstMsgRxed = false;
    }

    void task();

private:
    void producePacket();
    bool dispatchProduce();
    bool produceHostProtocolPacket(Packet &p);
    void processPacket(const Packet &p);
    void processMavlinkData(const uint8_t *bytes, unsigned len);

    void onUpdaterMsg(const uint8_t *bytes, unsigned len);

    void isr();
    friend void ISR_USART1();

    static void onTxComplete();

    Usart uart;
    volatile bool txPending;

    Packet txPacket, rxPacket;
    RingBuffer<2048> rxbuf; // again, huge but we're not strapped for RAM yet

    struct Stats {
        uint32_t txBytes;
        uint32_t rxBytes;
        uint32_t malformedBytes;
        uint32_t overruns;
        uint32_t dropped;
        uint32_t lineErrors;
    } stats;

    bool lastRxByteWasEsc;
    bool synced;

    bool firstMsgRxed;

    MsgID hostRequest;
};

#endif // HOSTPROTOCOL_H
