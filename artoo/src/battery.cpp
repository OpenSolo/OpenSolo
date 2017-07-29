#include "battery.h"

#if (BOARD >= BOARD_BB03)

#include "powermanager.h"
#include "tasks.h"
#include "ui.h"
#include "haptic.h"
#include "machine.h"
#include "stm32/gpio.h"
#include "stm32/adc.h"

Battery Battery::instance;

Battery::Battery() :
    thermal(0),
    id(Unknown),
    cellSum(0),
    battLevel(-1U),
    battLevelFilt(),
    battLevelStableCount(0),
    sampleCount(COUNTER_SAMPLE_ENABLED - 1),
    chgPresentState(false),
    thermalChgLockout(false)
{
}

void Battery::init()
{
    /*
     * Set up i/o related to charger balancing.
     *
     * Disable shunts to begin with.
     *
     * MEAS_EN is always on.
     */

    GPIOPin shuntBottom = CELL_SHUNT_BOT_GPIO;
    shuntBottom.setControl(GPIOPin::OUT_2MHZ);
    shuntBottom.setLow();

    GPIOPin shuntTop = CELL_SHUNT_TOP_GPIO;
    shuntTop.setControl(GPIOPin::OUT_2MHZ);
    shuntTop.setLow();

    GPIOPin chgDetect = CHG_DETECT_GPIO;
    chgDetect.setControl(GPIOPin::IN_PULL);

    CHG_ENABLE_GPIO.setControl(GPIOPin::OUT_2MHZ);
    chgDisable();

    GPIOPin cellMeasEnable = CELL_MEAS_EN_GPIO;
    cellMeasEnable.setControl(GPIOPin::OUT_2MHZ);
    measEnable();

    chgPresentState = chargerIsPresent();
}

void Battery::prepToSample()
{
    /*
     * Called from our 50Hz update loop,
     * prior to an ADC sample being kicked off.
     *
     * We disable the charger for 2 reasons:
     *  - when it's enabled, it adds an offset to the cells
     *  - when the charger is present, we don't get an edge when it disconnects
     *
     * Takes a little while for readings to stabilize after disabling
     * the charger, so only accept samples once counter has reached COUNTER_SAMPLE_ENABLED.
     *
     * Shunts must be disabled while sampling.
     */

    sampleCount++;

    if (sampleCount == COUNTER_PREPARE_TO_SAMPLE) {
        chgDisable();
    } else if (sampleCount == COUNTER_SAMPLE_ENABLED) {
        CELL_SHUNT_BOT_GPIO.setLow();
        CELL_SHUNT_TOP_GPIO.setLow();
    }
}


void Battery::onCellSamples(uint16_t bottom, uint16_t top, uint16_t therm, uint16_t cellId)
{
    /*
     * Called from ADC completion ISR.
     */

    ASSERT(samplesEnabled());

    sampleCount = 0;

    thermal = therm;
    checkTherm();

    PackID pid = packID(cellId);
    if (id != pid) {
        if (batteryIsPresent() && pid == Unknown) {
            Ui::instance.pendEvent(Event::UnknownBattery);
        }
        id = pid;
    }

    // remove the bottom component from the top cell measurement
    top -= bottom;

    unsigned newCellSum = bottom + top;
    if (cellSum != newCellSum) {
        cellSum = newCellSum;

        unsigned lvl = lookupLevel();
        if (!isInitialized()) {
            battLevel = lvl;
            battLevelFilt.update(battLevel, MovingAvgFilter::Alpha(1.0));
        } else {
            updateBattLevel(lvl);
        }
    }

    bool cp = chargerIsPresent();
    if (chgPresentState != cp) {
        Ui::instance.pendEvent(Event::ChargerConnChanged);
        if (cp) {
            Ui::instance.pendEvent(Event::ChargerConnected);
        }
        chgPresentState = cp;
    }

    if (overVoltage(top) || overVoltage(bottom)) {
        // charger is already disabled during sampling - just leave it that way

    } else {

        /*
         * we disable the charger during sampling - re-enable as appropriate.
         *
         * if the charger is connected, don't bother checking for undervoltage
         * since it will keep us alive anyway.
         */

        if (cp) {
            if (!thermalChgLockout) {
                chgEnable();
            }
        } else {
            // charger is not present - make sure we have enough juice to carry on
            if (underVoltage(top) || underVoltage(bottom)) {
                Tasks::trigger(Tasks::Shutdown);
            }

            // if we locked out the charger when it was plugged in,
            // we can try to re-enable
            thermalChgLockout = false;
        }
    }

    doBalancing(bottom, top);
}

void Battery::updateBattLevel(unsigned lvl)
{
    /*
     * process a new battery level sample.
     *
     * ensure the level is stable with a modified moving average
     * before we latch it as the new level.
     */

    const unsigned MMA_N = 10;                   // modified moving average window size
    const int MIN_LVL_DIFF_TO_UPDATE = 3;
    const unsigned MIN_STABLE_COUNT = MMA_N;     // prevents failsafe alert from coming up before critical alert when Artoo is booted up with critical battery

    // wait for battery level to stabilize after boot
    if (++battLevelStableCount < MIN_STABLE_COUNT) {
        return;
    }

    battLevelFilt.update(lvl, MovingAvgFilter::Alpha(1.0/MMA_N));
    unsigned movingAvgBattLevel = battLevelFilt.average();
    // propogate new battery level a single time after battery level has settled
    if (battLevelStableCount == MIN_STABLE_COUNT) {
        onLevelChanged(movingAvgBattLevel);
        battLevel = movingAvgBattLevel;
        return;
    }

    // update battery level when the moving average deviates by a significant amount from the previously latched battery level or if the new battery level reaches zero
    if (Intrinsic::abs(static_cast<int>(movingAvgBattLevel) - static_cast<int>(battLevel)) >= MIN_LVL_DIFF_TO_UPDATE || (!movingAvgBattLevel && battLevel)) {
        onLevelChanged(movingAvgBattLevel);
        battLevel = movingAvgBattLevel;
    }
}

void Battery::onLevelChanged(unsigned lvl)
{
    /*
     * Called in ISR context when our battery level has changed.
     *
     * Notify UI as appropriate.
     */

    Ui & ui = Ui::instance;
    ui.pendEvent(Event::ArtooBatteryChanged);

    // pend a lockout alert if controller battery reaches low and failsafe levels
    if (!chargerIsPresent()) {
        if (uiLevel() <= FAILSAFE_PERCENT) {
            const Telemetry & telemVals = FlightManager::instance.telemVals();
            if (telemVals.hasGpsFix()) {
                ui.pendEvent(Event::ControllerBatteryFailsafe);
            } else {
                ui.pendEvent(Event::ControllerBatteryFailsafeNoGps);
            }
            return;
        }

        if (uiLevel() <= CRITICALLY_LOW_PERCENT) {
            ui.pendEvent(Event::ControllerBatteryCritical);
            return;
        }
    }

    // dismiss controller battery alerts if new level is OK, failsafe battery alert should not be dismissed
    struct BattLevelAlert {
        Event::ID event;
        unsigned level;
    } const battLevelAlertDismissals[] = {
        { Event::ControllerBatteryTooLowForTakeoff, DISMISS_TOO_LOW_TO_FLY },
        { Event::ControllerBatteryCritical, CRITICALLY_LOW_PERCENT },
    };

    for (unsigned i = 0; i < arraysize(battLevelAlertDismissals); ++i) {
        const BattLevelAlert & bla = battLevelAlertDismissals[i];
        if (ui.alertManager.currentEvent() == bla.event) {
            if (chargerIsPresent() || lvl > bla.level) {
                ui.alertManager.dismiss();
                break;
            }
        }
    }
}

void Battery::doBalancing(uint16_t bottom, uint16_t top)
{
    if (chgIsEnabled()) {
        if (bottom > top) {
            if (balancingRequired(bottom, top)) {
                CELL_SHUNT_BOT_GPIO.setHigh();
            }
        } else {
            if (balancingRequired(top, bottom)) {
                CELL_SHUNT_TOP_GPIO.setHigh();
            }
        }
    }
}

void Battery::checkTherm()
{
    /*
     * If our battery has gotten too hot, flag it.
     * we'll disable the charger until it's unplugged and re-plugged.
     */

    if (!thermalChgLockout) {
        if (thermal < THERMAL_CHG_LIMIT) {
            thermalChgLockout = true;
            Ui::instance.pendEvent(Event::BatteryThermalLimitExceeded);
        }
    }
}

const Battery::PackID Battery::PackIdValues[] = {
    ThreeDR_2Cell,
    ThreeDR_4Cell,
};

Battery::PackID Battery::packID(uint16_t sample)
{
    // accept up to 1% slop in either direction
    static const int SLOP = Adc::RawRange / 100;

    for (unsigned i = 0; i < arraysize(PackIdValues); ++i) {
        if (Intrinsic::abs(PackIdValues[i] - sample) < SLOP) {
            return PackIdValues[i];
        }
    }

    return Unknown;
}

const uint16_t Battery::GenericLiIonDischargeCurve[] = {
    // XXX: need real curve numbers
    MillivoltsToAdc(4200 * NUM_CELLS),  // 100%
    MillivoltsToAdc(4100 * NUM_CELLS),
    MillivoltsToAdc(4000 * NUM_CELLS),
    MillivoltsToAdc(3850 * NUM_CELLS),
    MillivoltsToAdc(3650 * NUM_CELLS),
    MillivoltsToAdc(3600 * NUM_CELLS),  // 50%
    MillivoltsToAdc(3550 * NUM_CELLS),
    MillivoltsToAdc(3525 * NUM_CELLS),
    MillivoltsToAdc(3500 * NUM_CELLS),
    MillivoltsToAdc(3400 * NUM_CELLS),  // 10%
};

const uint16_t Battery::Artoo2CellDischargeCurve[] = {
    MillivoltsToAdc(8140),
    MillivoltsToAdc(7960),
    MillivoltsToAdc(7890),
    MillivoltsToAdc(7830),
    MillivoltsToAdc(7770),
    MillivoltsToAdc(7720),
    MillivoltsToAdc(7670),
    MillivoltsToAdc(7620),
    MillivoltsToAdc(7570),
    MillivoltsToAdc(7520),
    MillivoltsToAdc(7470),
    MillivoltsToAdc(7410),
    MillivoltsToAdc(7360),
    MillivoltsToAdc(7310),
    MillivoltsToAdc(7260),
    MillivoltsToAdc(7220),
    MillivoltsToAdc(7190),
    MillivoltsToAdc(7150),
    MillivoltsToAdc(7120),
    MillivoltsToAdc(7090),
    MillivoltsToAdc(7060),
    MillivoltsToAdc(7020),
    MillivoltsToAdc(6990),
    MillivoltsToAdc(6950),
    MillivoltsToAdc(6910),
    MillivoltsToAdc(6870),
    MillivoltsToAdc(6810),
    MillivoltsToAdc(6750),
    MillivoltsToAdc(6670),
    MillivoltsToAdc(6590),
    MillivoltsToAdc(6490),
    MillivoltsToAdc(6340),
};

const uint16_t Battery::Artoo2CellStm32OnlyDischargeCurve[] = {
    MillivoltsToAdc(8130),
    MillivoltsToAdc(8029),
    MillivoltsToAdc(7960),
    MillivoltsToAdc(7900),
    MillivoltsToAdc(7840),
    MillivoltsToAdc(7800),
    MillivoltsToAdc(7750),
    MillivoltsToAdc(7700),
    MillivoltsToAdc(7660),
    MillivoltsToAdc(7600),
    MillivoltsToAdc(7550),
    MillivoltsToAdc(7480),
    MillivoltsToAdc(7410),
    MillivoltsToAdc(7360),
    MillivoltsToAdc(7320),
    MillivoltsToAdc(7280),
    MillivoltsToAdc(7250),
    MillivoltsToAdc(7210),
    MillivoltsToAdc(7190),
    MillivoltsToAdc(7160),
    MillivoltsToAdc(7130),
    MillivoltsToAdc(7090),
    MillivoltsToAdc(7060),
    MillivoltsToAdc(7020),
    MillivoltsToAdc(6970),
    MillivoltsToAdc(6910),
    MillivoltsToAdc(6850),
    MillivoltsToAdc(6770),
    MillivoltsToAdc(6700),
    MillivoltsToAdc(6650),
    MillivoltsToAdc(6590),
    MillivoltsToAdc(6380),
};

const uint16_t Battery::Artoo4CellDischargeCurve[] = {
    MillivoltsToAdc(8090),
    MillivoltsToAdc(7880),
    MillivoltsToAdc(7810),
    MillivoltsToAdc(7740),
    MillivoltsToAdc(7690),
    MillivoltsToAdc(7630),
    MillivoltsToAdc(7570),
    MillivoltsToAdc(7520),
    MillivoltsToAdc(7470),
    MillivoltsToAdc(7420),
    MillivoltsToAdc(7380),
    MillivoltsToAdc(7330),
    MillivoltsToAdc(7290),
    MillivoltsToAdc(7240),
    MillivoltsToAdc(7200),
    MillivoltsToAdc(7170),
    MillivoltsToAdc(7150),
    MillivoltsToAdc(7120),
    MillivoltsToAdc(7110),
    MillivoltsToAdc(7090),
    MillivoltsToAdc(7070),
    MillivoltsToAdc(7050),
    MillivoltsToAdc(7040),
    MillivoltsToAdc(7020),
    MillivoltsToAdc(7000),
    MillivoltsToAdc(6970),
    MillivoltsToAdc(6940),
    MillivoltsToAdc(6910),
    MillivoltsToAdc(6850),
    MillivoltsToAdc(6780),
    MillivoltsToAdc(6710),
    MillivoltsToAdc(6620),
};

const uint16_t Battery::Artoo4CellStm32OnlyDischargeCurve[] = {
    MillivoltsToAdc(8200),
    MillivoltsToAdc(8080),
    MillivoltsToAdc(8010),
    MillivoltsToAdc(7940),
    MillivoltsToAdc(7870),
    MillivoltsToAdc(7800),
    MillivoltsToAdc(7740),
    MillivoltsToAdc(7680),
    MillivoltsToAdc(7630),
    MillivoltsToAdc(7570),
    MillivoltsToAdc(7530),
    MillivoltsToAdc(7480),
    MillivoltsToAdc(7440),
    MillivoltsToAdc(7380),
    MillivoltsToAdc(7330),
    MillivoltsToAdc(7300),
    MillivoltsToAdc(7270),
    MillivoltsToAdc(7250),
    MillivoltsToAdc(7230),
    MillivoltsToAdc(7220),
    MillivoltsToAdc(7200),
    MillivoltsToAdc(7190),
    MillivoltsToAdc(7170),
    MillivoltsToAdc(7140),
    MillivoltsToAdc(7110),
    MillivoltsToAdc(7080),
    MillivoltsToAdc(7040),
    MillivoltsToAdc(6980),
    MillivoltsToAdc(6900),
    MillivoltsToAdc(6870),
    MillivoltsToAdc(6820),
    MillivoltsToAdc(6670),
};

unsigned Battery::lookupLevel() const
{
    /*
     * Given the current cell sum and curve,
     * look up our battery voltage and return a 0 - 100 representation.
     *
     * curves must be in descending order.
     */

    const uint16_t *curve;
    unsigned len;

    switch (id) {
    case ThreeDR_2Cell:
        if (PowerManager::imx6Enabled()) {
            curve = Artoo2CellDischargeCurve;
            len = arraysize(Artoo2CellDischargeCurve);
        } else {
            curve = Artoo2CellStm32OnlyDischargeCurve;
            len = arraysize(Artoo2CellStm32OnlyDischargeCurve);
        }
        break;

    case ThreeDR_4Cell:
        if (PowerManager::imx6Enabled()) {
            curve = Artoo4CellDischargeCurve;
            len = arraysize(Artoo4CellDischargeCurve);
        } else {
            curve = Artoo4CellStm32OnlyDischargeCurve;
            len = arraysize(Artoo4CellStm32OnlyDischargeCurve);
        }
        break;

    default:
        curve = GenericLiIonDischargeCurve;
        len = arraysize(GenericLiIonDischargeCurve);
        break;
    }

    for (unsigned i = 0; i < len; ++i) {
        if (cellSum >= curve[i]) {
            return (len - i) * 100 / len;
        }
    }

    return 0;
}

#endif // BOARD >= BOARD_BB03
