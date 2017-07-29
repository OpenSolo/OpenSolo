
#ifndef USART_H_
#define USART_H_

#include "hw.h"
#include "common.h"

class GPIOPin;

class Usart
{
public:
    enum SrBits {
        SR_PARITY_ERR   = (1 << 0),
        SR_FRAMING_ERR  = (1 << 1),
        SR_NOISE_ERR    = (1 << 2),
        SR_OVERRUN      = (1 << 3),
        SR_IDLE         = (1 << 4),
        SR_RXED         = (1 << 5),
        SR_TC           = (1 << 6),
        SR_TXED         = (1 << 7),
        SR_LINE_BREAK   = (1 << 8),
        SR_CTS          = (1 << 9),
    };

    enum StopBits {
        Stop1 = 0,
        Stop0_5 = 1,
        Stop2 = 2,
        Stop1_5 = 3
    };

    enum CrBits {
        Cr_UE       = (1 << 13),
        Cr_M        = (1 << 12),
        Cr_WAKE     = (1 << 11),
        Cr_PCE      = (1 << 10),
        Cr_PS       = (1 << 9),
        Cr_PEIE     = (1 << 8),
        Cr_TXEIE    = (1 << 7),
        Cr_TCIE     = (1 << 6),
        Cr_RXNEIE   = (1 << 5),
        Cr_IDLEIE   = (1 << 4),
        Cr_TE       = (1 << 3),
        Cr_RE       = (1 << 2),
        Cr_RWU      = (1 << 1),
        Cr_SBK      = (1 << 1),
    };

    typedef void (*CompletionCallback)();

    Usart(volatile USART_t *hw, CompletionCallback txCB = 0, CompletionCallback rxCB = 0)
        : uart(hw),
          dmaRxChan(NULL), dmaTxChan(NULL),
          txCompletionCB(txCB), rxCompletionCB(rxCB)
    {}

    void init(GPIOPin rx, GPIOPin tx, int rate, bool dma = false, StopBits bits = Stop1);
    void deinit();

    ALWAYS_INLINE bool enabled() const {
        return (uart->CR1 & EnableMask) == EnableMask;
    }

    void write(const uint8_t* buf, int size);
    void write(const char* buf);
    void writeHex(uint32_t value, unsigned numDigits = 8);
    void writeHexBytes(const void *data, int size);
    void read(uint8_t *buf, int size);

    void writeDma(const uint8_t *buf, unsigned len);
    void readDma(const uint8_t *buf, unsigned len);

    void put(char c);
    char get();

    uint16_t isr(uint8_t &byte);

private:
    static const uint16_t EnableMask = (Cr_UE | Cr_TE | Cr_RE);

    volatile USART_t *uart;
    volatile DMAChannel_t *dmaRxChan;
    volatile DMAChannel_t *dmaTxChan;

    const CompletionCallback txCompletionCB;
    const CompletionCallback rxCompletionCB;

    static void dmaTXCallback(void *p, uint8_t flags);
    static void dmaRXCallback(void *p, uint8_t flags);
};

#endif /* USART_H_ */
