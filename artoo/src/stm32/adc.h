
#ifndef ADC_H
#define ADC_H

#include <stddef.h>

#include "hw.h"
#include "common.h"

class Adc
{
public:
    typedef void (*AdcIsr_t)();

    enum SampleRate {
        SampleRate_1_5,     // 1.5 ADC cycles
        SampleRate_7_5,     // 7.5 ADC cycles
        SampleRate_13_5,    // 13.5 ADC cycles
        SampleRate_28_5,    // 28.5 ADC cycles
        SampleRate_41_5,    // 41.5 ADC cycles
        SampleRate_55_5,    // 55.5 ADC cycles
        SampleRate_71_5,    // 71.5 ADC cycles
        SampleRate_239_5    // 239.5 ADC cycles
    };

    enum TriggerSource {
        TrigTim1_CC1    = 0,
        TrigTim1_CC2    = 1,
        TrigTim1_CC3    = 2,
        TrigTim2_CC2    = 3,
        TrigTim3_TRGO   = 4,
        TrigTim4_CC4    = 5,
        TrigExti11      = 6,
        TrigSwStart     = 7
    };

    static const uint16_t RawRange = 1 << 12;

    Adc(volatile ADC_t *adc, AdcIsr_t cb) :
        hw(adc), dmaChan(NULL), completionCB(cb)
    {}

    void init(bool dma, TriggerSource = TrigSwStart);
    void setSampleRate(uint8_t ch, SampleRate rate);

    ALWAYS_INLINE void enableEocInterrupt() {
        hw->CR1 |= (1 << 5);
    }

    ALWAYS_INLINE void disableEocInterrupt() {
        hw->CR1 &= ~(1 << 5);
    }

    void setRegularSequence(uint8_t len, const uint8_t channels[]);

    void beginSequence(unsigned len, uint16_t *samplebuf);
    uint16_t sampleSync(uint8_t channel);

private:
    volatile ADC_t *hw;
    volatile DMAChannel_t *dmaChan;

    AdcIsr_t completionCB;
    static void dmaCallback(void *p, uint8_t flags);
};

#endif // ADC_H
