
#ifndef _STM32_SPI_H
#define _STM32_SPI_H

#include <stdint.h>
#include <stddef.h>

#include "hw.h"
#include "gpio.h"
#include "dma.h"


class SPIMaster {
 public:

    enum Flags {
        // Clock divisors
        fPCLK_2     = (0 << 3),
        fPCLK_4     = (1 << 3),
        fPCLK_8     = (2 << 3),
        fPCLK_16    = (3 << 3),
        fPCLK_32    = (4 << 3),
        fPCLK_64    = (5 << 3),
        fPCLK_128   = (6 << 3),
        fPCLK_256   = (7 << 3),

        // SPI clocking mode
        fCPHA       = (1 << 0),
        fCPOL       = (1 << 1),

        // Bit order
        fLSBFIRST   = (1 << 7)
    };

    struct Config {
        Dma::Priority dmaRxPrio;
        unsigned flags;
        // others if we need them
    };

    typedef void (*CompletionCallback)();

    struct CallbackCtxt {
        CompletionCallback cb;
        void* param;
    };

    SPIMaster(volatile SPI_t *_hw,
              GPIOPin _sck,
              GPIOPin _miso,
              GPIOPin _mosi,
              CompletionCallback cb = 0)
        : hw(_hw), dmaRxChan(NULL), dmaTxChan(NULL),
          sck(_sck), miso(_miso), mosi(_mosi),
          dmaRxPriorityBits(0), completionCB(cb) {}

    void init(const Config & config);

    uint8_t transfer(uint8_t b);
    void transfer(const uint8_t *txbuf, uint8_t *rxbuf, unsigned len);

    void transferDma(const uint8_t *txbuf, uint8_t *rxbuf, unsigned len);
    void txDma(const uint8_t *txbuf, unsigned len);

 private:
    volatile SPI_t *hw;
    volatile DMAChannel_t *dmaRxChan;
    volatile DMAChannel_t *dmaTxChan;
    GPIOPin sck;
    GPIOPin miso;
    GPIOPin mosi;
    uint32_t dmaRxPriorityBits;

    CompletionCallback completionCB;
    static void dmaCallback(void *p, uint8_t flags);
};

#endif
