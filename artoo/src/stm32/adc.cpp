
#include "adc.h"
#include "dma.h"

#include "gpio.h"

void Adc::init(bool dma, TriggerSource trig)
{
    // enable peripheral clock
    if (hw == &ADC1) {
        RCC.APB2RSTR |= (1 << 9);
        RCC.APB2RSTR &= ~(1 << 9);
        RCC.APB2ENR |= (1 << 9);

        if (dma) {
            dmaChan = &DMA1.channels[0];    // DMA1, channel 1
            Dma::initChannel(&DMA1, 0, dmaCallback, this);
        }
    }
    else if (hw == &ADC2) {
        RCC.APB2ENR |= (1 << 10);

        // "Only ADC1 and ADC3 have this DMA capability.
        // ADC2-converted data can be transferred in dual ADC mode
        // using DMA thanks to master ADC1."
    }
    else if (hw == &ADC3) {
        RCC.APB2ENR |= (1 << 15);

        if (dma) {
            dmaChan = &DMA2.channels[4];  // DMA2, channel 5
            Dma::initChannel(&DMA2, 4, dmaCallback, this);
        }
    }

    /*
     * Set our external event selection, default channel selection
     * to none, and enable the periph.
     */

    hw->CR1 = (1 << 8);     // enable scan mode
    hw->CR2 = (trig << 17); // trigger selection
    hw->SQR1 = 0;
    hw->SQR2 = 0;
    hw->SQR3 = 0;
    hw->SMPR1 = 0;
    hw->SMPR2 = 0;

    if (dma) {
        dmaChan->CPAR = (uint32_t)&hw->DR;
        hw->CR2 |= (1 << 8);    // enable dma
    }

    hw->CR2 |= 0x1;
    (void)hw->DR;

    // reset calibration & wait for it to complete
    const uint32_t resetCalibration = (1 << 3);
    hw->CR2 |= resetCalibration;
    while (hw->CR2 & resetCalibration)
        ;

    // perform calibration & wait for it to complete
    const uint32_t calibrate = (1 << 2);
    hw->CR2 |= calibrate;
    while (hw->CR2 & calibrate)
        ;
}

void Adc::setSampleRate(uint8_t channel, SampleRate rate)
{
    if (channel < 10) {
        hw->SMPR2 |= rate << (channel * 3);
    } else {
        hw->SMPR1 |= rate << ((channel - 10) * 3);
    }
}

void Adc::setRegularSequence(uint8_t len, const uint8_t channels[])
{
    /*
     * We can perform up to 16 conversions in a sequence.
     *
     * The sequence is specified as an array of channel numbers
     * in 'channels' - conversions are performed in that order.
     *
     * The recommended strategy for converting multiple channels
     * is via DMA - otherwise, we're getting woken up for each
     * EOC interrupt with no good way to track which channel it
     * corresponds to.
     */

    hw->SQR1 = 0;
    hw->SQR2 = 0;
    hw->SQR3 = 0;

    if (len == 0 || len > 16) {
        return;
    }

    for (unsigned i = 0; i < len && i < 6; ++i) {
        hw->SQR3 |= (channels[i] << (i * 5));
    }

    for (unsigned i = 6; i < len && i < 12; ++i) {
        hw->SQR2 |= (channels[i] << ((i - 6) * 5));
    }

    for (unsigned i = 12; i < len && i < 16; ++i) {
        hw->SQR1 |= (channels[i] << ((i - 12) * 5));
    }

    hw->SQR1 |= ((len - 1) << 20);
}

void Adc::beginSequence(unsigned len, uint16_t *samplebuf)
{
    /*
     * Kick off a new sequence via DMA.
     * Must have been init'd with DMA enabled.
     */

    dmaChan->CNDTR = len;
    dmaChan->CMAR = (uint32_t)samplebuf;
    dmaChan->CCR =  (1 << 10) | // MSIZE - half-word
                    (1 << 8) |  // PSIZE - half-word
                    (1 << 7) |  // MINC - memory pointer increment
                    (0 << 4) |  // DIR - direction, 0 == read from peripheral
                    (1 << 3) |  // TEIE - transfer error ISR enable
                    (0 << 2) |  // HTIE - half complete ISR enable
                    (1 << 1);   // TCIE - transfer complete ISR enable
    dmaChan->CCR |= (1 << 0); // enable

    hw->CR2 |= ((1 << 22) | (1 << 20)); // SWSTART the conversion
}

uint16_t Adc::sampleSync(uint8_t channel)
{
    /*
     * Inefficient but simple synchronous sample.
     */

    hw->SQR3 = channel;

    hw->CR2 |= (1 << 22);           // SWSTART the conversion
    while (!(hw->SR & (1 << 1)))    // wait for EOC
        ;
    return hw->DR;
}

void Adc::dmaCallback(void *p, uint8_t flags)
{
    /*
     * static dispatcher for all ADC DMA callbacks.
     */

    Adc *adc = static_cast<Adc*>(p);

    // clear STRT - does not auto-clear
    adc->hw->SR &= ~(1 << 4);

    // disable dma channel
    adc->dmaChan->CCR = 0;

    if (flags) {
        // handle errors
    }

    if (adc->completionCB) {
        adc->completionCB();
    }
}
