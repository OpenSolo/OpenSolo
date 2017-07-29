#include "inputs.h"
#include "buttonmanager.h"
#include "dsm.h"
#include "params.h"
#include "board.h"
#include "ui.h"

#include "stm32/gpio.h"
#include "stm32/adc.h"

Adc Inputs::Adc1(&ADC1, Inputs::adcConversionComplete);

uint16_t Inputs::adcSamples[];
Inputs::InvalidStickValues Inputs::invalidStickVals;
SysTime::Ticks Inputs::alertStateEnterTimestamp;

bool Inputs::reportRequested;
bool Inputs::rawIoEnabled;
uint8_t Inputs::invalidStickInputMask;

// matches order of StickID
StickAxis Inputs::sticks[] = {
    StickAxis(Io::AdcStick0, StickAxis::Forward, StickAxis::RcChannelDeadZone),     // StickThro
    StickAxis(Io::AdcStick1, StickAxis::Forward, StickAxis::RcChannelDeadZone),     // StickRoll
    StickAxis(Io::AdcStick2, StickAxis::Forward, StickAxis::RcChannelDeadZone),     // StickPitch
    StickAxis(Io::AdcStick3, StickAxis::Reverse, StickAxis::RcChannelDeadZone),     // StickYaw
    StickAxis(Io::AdcGimbalY, StickAxis::Reverse, StickAxis::GimbalPitchDeadZone),  // StickGimbalY
    StickAxis(Io::AdcGimbalRate, StickAxis::Reverse, 0)                             // StickGimbalRate
};

void Inputs::init()
{
    Dsm::instance.init();
    initADC();
    beginAdcCapture();
    initStickValidState();
}

void Inputs::initADC()
{
    GPIOPin adcPins[] = {
        STICK_0_GPIO,
        STICK_1_GPIO,
        STICK_2_GPIO,
        STICK_3_GPIO,
        GIMBAL_RATE_GPIO,
        GIMBAL_Y_GPIO,
#if (BOARD >= BOARD_BB03)
        AMBIENT_LIGHT_GPIO,
        CELL_THERM_GPIO,
        CELL_ID_GPIO,
        CELL_MEAS_BOT_GPIO,
        CELL_MEAS_TOP_GPIO,
#endif
    };

    for (unsigned i = 0; i < arraysize(adcPins); ++i) {
        adcPins[i].setControl(GPIOPin::IN_ANALOG);
    }

    const uint8_t adcChannels[] = {
        STICK_0_ADC_CH,
        STICK_1_ADC_CH,
        STICK_2_ADC_CH,
        STICK_3_ADC_CH,
        GIMBAL_Y_ADC_CH,
        GIMBAL_RATE_ADC_CH,
#if (BOARD >= BOARD_BB03)
        AMBIENT_LIGHT_ADC_CH,
        CELL_THERM_ADC_CH,
        CELL_ID_ADC_CH,
        CELL_MEAS_BOT_ADC_CH,
        CELL_MEAS_TOP_ADC_CH,
#endif
    };

    Adc1.init(true);
    Adc1.setRegularSequence(arraysize(adcChannels), adcChannels);
    for (unsigned i = 0; i < arraysize(adcChannels); ++i) {
        Adc1.setSampleRate(adcChannels[i], Adc::SampleRate_239_5);
    }

    loadStickParams();
    beginAdcCapture();
}

void Inputs::loadStickParams()
{
    /*
     * Load the parameters for a given stick.
     * Note: params are stored with the raw ID for a stick input.
     */

    const Params::StoredValues &sv = Params::sys.storedValues;
    for (unsigned rawID = 0; rawID < arraysize(sticks); ++rawID) {
        unsigned mappedID = mappedStickID(rawID);
        sticks[mappedID].init(sv.sticks[rawID], sv.rcSticks[rawID]);
    }
}

void Inputs::adcConversionComplete()
{
    /*
     * Called in ISR context.
     */

    static const unsigned NUM_RC_STICKS = 4;

    for (unsigned rawID = 0; rawID < NUM_RC_STICKS; ++rawID) {
        unsigned mappedID = mappedStickID(rawID);
        sticks[mappedID].update(adcSamples[rawID]);
    }

    sticks[Io::StickGimbalY].update(adcSamples[Io::AdcGimbalY]);
    sticks[Io::StickGimbalRate].update(adcSamples[Io::AdcGimbalRate]);

#if (BOARD >= BOARD_BB03)
    if (Battery::instance.samplesEnabled()) {
        Battery::instance.onCellSamples(adcSamples[Io::AdcCellBottom], adcSamples[Io::AdcCellTop],
                                        adcSamples[Io::AdcCellTherm], adcSamples[Io::AdcCellID]);
    }
#endif

    Tasks::trigger(Tasks::Camera);

    beginAdcCapture();
}

bool Inputs::producePacket(HostProtocol::Packet &pkt)
{
    /*
     * Our opportunity to produce a packet to be sent to the host.
     */

    // always send an alert if out of range stick values are being received,
    // optionally followed by regularly scheduled input reports.

    bool appendedInvalidStickVals = invalidStickVals.producePacket(pkt);

    if (!reportRequested) {
        return appendedInvalidStickVals;
    }

    reportRequested = false;

    // RC channels to be forwarded to the vehicle, don't send any values (to trigger RCFailsafe) if getting any invalid values from flight sticks
    if (isFlightControlValid()) {
        Dsm::instance.producePacket(pkt);
    }

    // additional inputs that 3rd parties may be interested in
    uint16_t batt = Battery::instance.level();

    pkt.delimitSlip();
    pkt.appendSlip(HostProtocol::InputReport);
    pkt.appendItemSlip(sticks[Io::StickGimbalY].scaledAngularValue());
    pkt.appendItemSlip(sticks[Io::StickGimbalRate].scaledLinearValue());
    pkt.appendItemSlip(batt);
    pkt.delimitSlip();

    // usually only enabled for testing purposes
    if (rawIoEnabled) {
        pkt.delimitSlip();
        pkt.appendSlip(HostProtocol::RawIoReport);
        pkt.appendSlip(adcSamples, sizeof(adcSamples));
        uint16_t buttonMask = ButtonManager::pressMask();
        pkt.appendSlip(&buttonMask, sizeof(buttonMask));
        pkt.delimitSlip();
    }

    return true;
}

bool Inputs::InvalidStickValues::producePacket(HostProtocol::Packet &pkt)
{
    /*
     * If we have invalid values, write them to host,
     * and reset values once we've done so.
     *
     * We rely on the fact that we will continue to receive
     * invalid stick readings as long as they remain invalid.
     */

    if (!invalidStickVals.isSet) {
        return false;
    }

    pkt.delimitSlip();
    pkt.appendSlip(HostProtocol::InvalidStickInputs);
    pkt.appendItemSlip(rawID);
    pkt.appendItemSlip(inputVal);
    pkt.appendItemSlip(trimVal);
    pkt.appendItemSlip(minVal);
    pkt.appendItemSlip(maxVal);
    pkt.delimitSlip();

    reset();

    return true;
}

void Inputs::onInvalidStickInput(Io::AdcID rawID, uint16_t inputVal, uint16_t trim, uint16_t minVal, uint16_t maxVal)
{
    /*
     * A stick has received invalid input.
     *
     * Mark the stick as invalid, and hang onto the values
     * so we can report them.
     */

    invalidStickInputMask |= BIT(rawID);

    // if we're past the cooldown period (or timestamp hasn't been set) and another alert isn't being sent, we can send alerts
    if (SysTime::now() - alertStateEnterTimestamp > SysTime::msTicks(1000)) {
        invalidStickVals.latch(rawID, inputVal, trim, minVal, maxVal);
        pendInvalidStickAlert(rawID);
        alertStateEnterTimestamp = SysTime::now();
    }
}

void Inputs::InvalidStickValues::latch(Io::AdcID adcID, uint16_t v, uint16_t trim, uint16_t min, uint16_t max)
{
    if (!isSet) {
        isSet = true;
        rawID = adcID;
        mappedID = static_cast<uint8_t>(mappedStickID(adcID));
        inputVal = v;
        trimVal = trim;
        minVal = min;
        maxVal = max;
    }
}

void Inputs::InvalidStickValues::reset()
{
    /*
     * Clear out any previous invalid values.
     *
     * This is called every time an invalid stick error notification packet
     * is sent out, since we rely on the fact that we will continue
     * to receive invalid stick readings as long as they remain invalid.
     */

    rawID = Io::AdcStick0;
    mappedID = 255;
    inputVal = 0;
    trimVal = 0;
    minVal = 0;
    maxVal = 0;
    isSet = false;
}

unsigned Inputs::mappedStickID(unsigned rawID)
{
    /*
     * Retrieve the mapped id for the given raw ID.
     *
     * Raw IDs are in terms of hardware: sticks 0-3.
     * Mapped IDs are in terms of control axes: throttle, roll, pitch, yaw.
     */

    // defaults for EVT boards.
    static const unsigned EVTStickAxisMap[] = {
        Io::AdcStick3,      // StickThro
        Io::AdcStick2,      // StickRoll
        Io::AdcStick1,      // StickPitch
        Io::AdcStick0,      // StickYaw
        Io::AdcGimbalY,     // no change - direct mapping
        Io::AdcGimbalRate,  // no change - direct mapping
    };

    ASSERT(stickIdIsValid(rawID));

    uint8_t mappedId = Params::sys.storedValues.rcSticks[rawID].input;
    if (stickIdIsValid(mappedId)) {
        return mappedId;
    }

    // not valid, return default mapping
    return EVTStickAxisMap[rawID];
}

bool Inputs::isCameraControlValid() {
    const uint8_t mask = (BIT(Io::AdcGimbalY) | BIT(Io::AdcGimbalRate));
    return (invalidStickInputMask & mask) == 0;
}

bool Inputs::isFlightControlValid() {
    const uint8_t mask = (BIT(Io::AdcStick0) | BIT(Io::AdcStick1) | BIT(Io::AdcStick2) | BIT(Io::AdcStick3));
    return (invalidStickInputMask & mask) == 0;
}

bool Inputs::isCameraControl(Io::StickID id) {
    return (id == Io::StickGimbalY || id == Io::StickGimbalRate);
}

bool Inputs::isFlightControl(Io::StickID id) {
    return (id == Io::StickThro || id == Io::StickRoll|| id == Io::StickPitch || id == Io::StickYaw);
}

void Inputs::pendInvalidStickAlert(Io::AdcID id)
{
    Io::StickID mapped_id = static_cast<Io::StickID>(id);

    if (isFlightControl(mapped_id)) {
        if (!isFlightControlValid()) {
            Ui::instance.pendEvent(Event::ControllerValueOutOfRange);
        }
        return;
    }

    if (isCameraControl(mapped_id)) {
        if (!isCameraControlValid()) {
            Ui::instance.pendEvent(Event::CamControlValueOutOfRange);
        }
        return;
    }
}

void Inputs::initStickValidState()
{
    invalidStickVals.reset();
    invalidStickInputMask = 0;          // innocent until proven guilty
}

void Inputs::resetInvalidStickError()
{
    initStickValidState();
    Ui::instance.alertManager.dismissInvalidStickAlerts();
}

void Inputs::onCalibrationApplied()
{
    loadStickParams();
    resetInvalidStickError();
}
