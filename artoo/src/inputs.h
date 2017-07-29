#ifndef INPUTS_H
#define INPUTS_H

#include "io.h"
#include "stickaxis.h"
#include "hostprotocol.h"
#include "battery.h"
#include "board.h"

#include "stm32/adc.h"
#include "stm32/hwtimer.h"

class Inputs
{
public:
    static void init();
    static void loadStickParams();

    // only intended to be called by heartbeat task
    static ALWAYS_INLINE void fiftyHzWork() {
        reportRequested = true;
#if (BOARD >= BOARD_BB03)
        Battery::instance.prepToSample();
#endif
    }

    static bool producePacket(HostProtocol::Packet &pkt);
    static void onInvalidStickInput(Io::AdcID rawID, uint16_t inputVal, uint16_t trim, uint16_t minVal, uint16_t maxVal);

    static bool isCameraControlValid();
    static bool isFlightControlValid();
    static bool isCameraControl(Io::StickID id);
    static bool isFlightControl(Io::StickID id);
    static void pendInvalidStickAlert(Io::AdcID id);

    static bool stickIdIsValid(unsigned id) {
        return id <= Io::AdcGimbalRate;
    }

    static bool flightSticksValid();

    static unsigned mappedStickID(unsigned rawID);

    static StickAxis & stick(Io::StickID id) {
        return sticks[id];
    }

    static void setRawIoEnabled(bool enabled) {
        rawIoEnabled = enabled;
    }

    struct InvalidStickValues {
        Io::AdcID rawID;
        uint8_t mappedID;
        uint16_t inputVal;
        uint16_t trimVal;
        uint16_t minVal;
        uint16_t maxVal;
        bool isSet;

        void reset();
        void latch(Io::AdcID adcID, uint16_t v, uint16_t trim, uint16_t min, uint16_t max);
        bool producePacket(HostProtocol::Packet &pkt);
    };

    static bool stickValueInvalid(Io::AdcID i) {
        return (invalidStickInputMask >> i) & 1;
    }

    static void resetInvalidStickError();
    static void onCalibrationApplied();

private:
    static void initStickValidState();

    static ALWAYS_INLINE void beginAdcCapture() {
        Adc1.beginSequence(arraysize(adcSamples), adcSamples);
    }

    static Adc Adc1;
    static void adcConversionComplete();
    static uint16_t adcSamples[Io::AdcCount];

    static void initADC();

    static StickAxis sticks[];

    static bool reportRequested;
    static bool rawIoEnabled;
    static uint8_t invalidStickInputMask;
    static InvalidStickValues invalidStickVals;
    static SysTime::Ticks alertStateEnterTimestamp;

    static uint8_t ALWAYS_INLINE BIT(Io::AdcID x) {
        return (1 << x);
    }
};

#endif // INPUTS_H
