#ifndef BATTERY_H
#define BATTERY_H

#include "board.h"

#if (BOARD >= BOARD_BB03)

#include "stm32/common.h"
#include "stm32/gpio.h"
#include "movingavgfilter.h"

/*
 * Charger is responsible for charging & balancing our batteries.
 */

class Battery
{
public:
    Battery();

    static Battery instance;

    void init();
    void prepToSample();
    void onChgDetectChanged();
    void onCellSamples(uint16_t bottom, uint16_t top, uint16_t therm, uint16_t packID);

    bool isInitialized() const {
        return battLevel != -1U;
    }

    unsigned level() const {
        if (!batteryIsPresent()) {
            return 0;
        }
        return battLevel;
    }

    unsigned uiLevel() const {
        // clamp range to allow for a little padding to communicate
        // low battery before we actually die
        const unsigned clamped = clamp(level(), UI_BATT_LVL_OFFSET, 100U);
        return scale(clamped, UI_BATT_LVL_OFFSET, 100U, 0U, 100U);
    }

    bool ALWAYS_INLINE chargerIsPresent() const {
        return CHG_DETECT_GPIO.isHigh();
    }
    void ALWAYS_INLINE chgEnable() {
        CHG_ENABLE_GPIO.setHigh();
    }
    void ALWAYS_INLINE chgDisable() {
        CHG_ENABLE_GPIO.setLow();
    }

    bool batteryIsPresent() const {
        return thermal < DISCONN_THRESH && id < DISCONN_THRESH;
    }

    bool ALWAYS_INLINE samplesEnabled() const {
        return sampleCount >= COUNTER_SAMPLE_ENABLED;
    }

     static const unsigned UI_BATT_LVL_OFFSET = 10;

    // battery threshold percentages
    // critically low at 6, because increments are in 3.125 at the moment...
    static const unsigned FAILSAFE_PERCENT = 0+UI_BATT_LVL_OFFSET;
    static const unsigned CRITICALLY_LOW_PERCENT = 6+UI_BATT_LVL_OFFSET;
    static const unsigned DISMISS_TOO_LOW_TO_FLY = 20+UI_BATT_LVL_OFFSET;

private:
    static const unsigned NUM_CELLS = 2;
    // thermal and ID lines are pulled up, so expect high when disconnected
    static const unsigned DISCONN_THRESH = 4000;

    // measured empirically
    static const unsigned UVOLT_PER_ADC_UNIT = 3280;
    // start balancing if delta is greater than 20mV
    static const unsigned UVOLT_BALANCING_REQUIRED = 20 * 1000;

    // cell voltage limits
    static const unsigned UVOLT_OVER_VOLTAGE = 4100 * 1000;
    static const unsigned UVOLT_UNDER_VOLTAGE = 3200 * 1000;

    static const unsigned COUNTER_PREPARE_TO_SAMPLE = 45;
    static const unsigned COUNTER_SAMPLE_ENABLED = 50;

    /*
     * data sheet says that at 80C the min resistance would be 1591 ohms.
     * we have a 10k pullup and we are running at 3.3v,
     * so our formula looks like 1591 / (10000 + 1591) * 3.3 = .453volts.
     *
     * .453/3.3 * Adc::RawRange ~= 562.
     */
    static const unsigned THERMAL_CHG_LIMIT = 562;

    static constexpr uint16_t MillivoltsToAdc(unsigned mv) {
        return mv * 1000 / UVOLT_PER_ADC_UNIT;
    }

    void setChargerState();

    bool ALWAYS_INLINE chgIsEnabled() const {
        return CHG_ENABLE_GPIO.isOutputHigh();
    }

    void ALWAYS_INLINE measEnable() {
        CELL_MEAS_EN_GPIO.setHigh();
    }
    void ALWAYS_INLINE measDisable() {
        CELL_MEAS_EN_GPIO.setLow();
    }

    static bool balancingRequired(unsigned hi, unsigned lo) {
        return ((hi - lo) * UVOLT_PER_ADC_UNIT >= UVOLT_BALANCING_REQUIRED);
    }

    static bool ALWAYS_INLINE underVoltage(unsigned cell) {
        return (cell * UVOLT_PER_ADC_UNIT) <= UVOLT_UNDER_VOLTAGE;
    }

    static bool ALWAYS_INLINE overVoltage(unsigned cell) {
        return (cell * UVOLT_PER_ADC_UNIT) >= UVOLT_OVER_VOLTAGE;
    }

    enum PackID {
        Unknown         = 0x0,
        ThreeDR_2Cell   = 0x800,
        ThreeDR_4Cell   = 0x9d8,
    };

    static PackID packID(uint16_t sample);
    void updateBattLevel(unsigned lvl);
    void onLevelChanged(unsigned lvl);
    void doBalancing(uint16_t bottom, uint16_t top);
    void checkTherm();
    unsigned lookupLevel() const;

    uint16_t thermal;
    PackID id;

    unsigned cellSum;
    unsigned battLevel;
    MovingAvgFilter battLevelFilt;
    unsigned battLevelStableCount;

    unsigned sampleCount;
    bool chgPresentState;

    bool thermalChgLockout;

    static const PackID PackIdValues[];
    static const uint16_t GenericLiIonDischargeCurve[];

    static const uint16_t Artoo2CellDischargeCurve[];
    static const uint16_t Artoo2CellStm32OnlyDischargeCurve[];

    static const uint16_t Artoo4CellDischargeCurve[];
    static const uint16_t Artoo4CellStm32OnlyDischargeCurve[];
};

#endif // (BOARD >= BOARD_BB02_5)

#endif // BATTERY_H
