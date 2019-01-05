#include "cameracontrol.h"
#include "hostprotocol.h"
#include "inputs.h"
#include "params.h"
#include "tasks.h"
#include "flightmanager.h"
#include "vehicleconnector.h"
#include "powermanager.h"
#include "buttonmanager.h"
#include "buttonfunction.h"
#include "lockout.h"
#include "selftest.h"
#include "factorytest.h"
#include "version.h"
#include "mavlink.h"
#include "board.h"
#include "ui.h"
#include "ui_events.h" // Debugging only

#include "stm32/gpio.h"
#include "stm32/sys.h"

HostProtocol HostProtocol::instance(Usart(&HOST_UART, onTxComplete));

void HostProtocol::init()
{
    rxbuf.init();
    rxPacket.reset();

    /*
     * we want to enable uart RX immediately, in case
     * the imx6 has already booted somehow, so we can
     * skip to our running state.
     */
    uart.init(HOST_UART_RX_GPIO, HOST_UART_TX_GPIO, 115200, true);

    /*
     * but, we want to leave TX disabled so we don't
     * inadvertently backpower the imx6 before we've
     * actually enabled the voltage rails.
     */
    disableTX();
}

void HostProtocol::enableTX()
{
    // reattach uart tx line to the uart peripheral
    GPIOPin tx = HOST_UART_TX_GPIO;
    tx.setControl(GPIOPin::OUT_ALT_50MHZ);

    NVIC.irqEnable(IVT.HOST_UART_DMA_TX_CH);
}

void HostProtocol::disableTX()
{
    /*
     * We want to continue listening for msgs from the host,
     * but if it's disabled, it's possible for the TX line
     * to back power it.
     *
     * Set TX line to hi-z, but leave RX line enabled.
     */

    NVIC.irqDisable(IVT.HOST_UART_DMA_TX_CH);

    GPIOPin tx = HOST_UART_TX_GPIO;
    tx.setControl(GPIOPin::OUT_OPEN_2MHZ);
    tx.setHigh();

    firstMsgRxed = false;

    rxPacket.reset();
    synced = false;
    lastRxByteWasEsc = false;
}

void HostProtocol::requestTransaction()
{
    /*
     * Ask for producePacket() to be called once.
     *
     * If a transaction is already in progress, producePacket()
     * gets called again when it's complete, so all sources
     * will eventually get served.
     */

    if (!uart.enabled()) {
        return;
    }

    // critical section
    NVIC.irqDisable(IVT.HOST_UART_DMA_TX_CH);

    if (!txPending) {
        producePacket();
    }

    // end critical section
    NVIC.irqEnable(IVT.HOST_UART_DMA_TX_CH);
}

void HostProtocol::producePacket()
{
    /*
     * Produce a packet to send to the host.
     *
     * Gets called again from the completion handler,
     * so we'll keep producing packets until none of
     * our sources has one to send.
     */

    txPacket.reset();

    if (dispatchProduce()) {
        txPending = true;
        uart.writeDma(txPacket.data(), txPacket.length());
        stats.txBytes += txPacket.length();
    } else {
        txPending = false;
    }
}

bool HostProtocol::dispatchProduce()
{
    /*
     * Helper for producePacket(), just concerned with
     * collecting a packet from one of our data sources.
     */

    if (produceHostProtocolPacket(txPacket)) {
        return true;
    }

    if (ButtonManager::producePacket(txPacket)) {
        return true;
    }

    if (Inputs::producePacket(txPacket)) {
        return true;
    }

    if (FlightManager::instance.producePacket(txPacket)) {
        return true;
    }

    if (VehicleConnector::instance.producePacket(txPacket)) {
        return true;
    }

    if (PowerManager::producePacket(txPacket)) {
        return true;
    }

    if (SelfTest::producePacket(txPacket)) {
        return true;
    }

    return false;
}

bool HostProtocol::produceHostProtocolPacket(Packet &p)
{
    /*
     * Produce a response to a request that we've
     * received from our host.
     */

    switch (hostRequest) {

    default:
        return false;

    case ParamStoredVals:
        p.delimitSlip();
        p.appendSlip(ParamStoredVals);
        p.appendItemSlip(Params::sys.storedValues);
        p.delimitSlip();
        break;

    case SysInfo:
        const uint16_t hwversion = BOARD;

        p.delimitSlip();
        p.appendSlip(SysInfo);
        p.appendSlip(Sys::UniqueId, Sys::UniqueIdLen);
        p.appendItemSlip(hwversion);
        p.appendSlip(Version::str(), strlen(Version::str()));
        p.delimitSlip();
        break;
    }

    hostRequest = Nop;
    return true;
}

void HostProtocol::onTxComplete()
{
    /*
     * DMA transmission has completed.
     * Try to produce another one if possible.
     */

    instance.producePacket();
}

IRQ_HANDLER ISR_USART1()
{
    HostProtocol::instance.isr();
}

void HostProtocol::isr()
{
    uint8_t b;
    uint16_t status = uart.isr(b);

    if (status & Usart::SR_OVERRUN) {
        synced = false;
        stats.overruns++;

    } else if (status & (Usart::SR_NOISE_ERR | Usart::SR_FRAMING_ERR)) {
        // NE and FE show up at the same time as RXNE,
        // so check those first, and only accept byte if they're clear
        synced = false;
        stats.lineErrors++;

    } else if (status & Usart::SR_RXED) {
        if (!rxbuf.full()) {
            rxbuf.enqueue(b);
            Tasks::trigger(Tasks::HostProtocol);
        } else {
            stats.dropped++;
        }
    }
}

void HostProtocol::task()
{
    /*
     * Process the packet that has just arrived.
     */

    while (!rxbuf.empty()) {

        uint8_t b = rxbuf.dequeue();
        stats.rxBytes++;

        if (!synced) {
            if (b == Slip::END) {
                rxPacket.reset();
                synced = true;
                lastRxByteWasEsc = false;
            }
            continue;
        }

        if (lastRxByteWasEsc) {
            if (b == Slip::ESC_END) {
                b = Slip::END;
            } else if (b == Slip::ESC_ESC) {
                b = Slip::ESC;
            } else {
                // if it's not an ESC_END or ESC_ESC, it's a malformed packet.
                // http://tools.ietf.org/html/rfc1055 says
                // just drop it in the packet anyway in this case.
                stats.malformedBytes++;
            }
            if (!rxPacket.isFull()) {
                rxPacket.append(b);
            }
            lastRxByteWasEsc = false;
            continue;
        }

        switch (b) {
        case Slip::END:
            if (!rxPacket.isEmpty()) {
                processPacket(rxPacket);
                rxPacket.reset();
            }
            break;

        case Slip::ESC:
            // we got an ESC character - we'll treat the next char specially
            lastRxByteWasEsc = true;
            break;

        default:
            if (!rxPacket.isFull()) {
                rxPacket.append(b);
            }
            break;
        }
    }
}

void HostProtocol::processPacket(const Packet &p)
{
    if (!firstMsgRxed) {
        firstMsgRxed = true;
    }

    const uint8_t * bytes = p.data();

    switch (bytes[0]) {

    case SysInfo:
    case ParamStoredVals:
        hostRequest = static_cast<MsgID>(bytes[0]);
        requestTransaction();
        break;

    case SetRawIo:
        // first byte treated as bool
        Inputs::setRawIoEnabled(bytes[1] != 0);
        break;

    case Calibrate:
        // don't apply stick calibration changes while armed
        if (!FlightManager::instance.armed()) {
            Params::StoredValues &sv = Params::sys.storedValues;
            if (p.payloadLen() >= sizeof(sv.sticks)) {
                memcpy(sv.sticks, &bytes[1], sizeof(sv.sticks));

                // dismiss any previous stick-related error alerts, load params
                Inputs::onCalibrationApplied();
                Params::sys.mark();
            }
        }
        break;

    case ConfigSweepTime:{
        Params::StoredValues &sv = Params::sys.storedValues;

        if (p.payloadLen() >= sizeof(sv.sweepConfig)){
            memcpy(&sv.sweepConfig, &bytes[1], sizeof(sv.sweepConfig));
            CameraControl::instance.setSweepConfig(sv.sweepConfig);
            Params::sys.mark();
        }

        break;}

    case ConfigStickAxes:
        // don't apply stick axis changes while armed
        if (!FlightManager::instance.armed()) {
            Params::StoredValues &sv = Params::sys.storedValues;
            if (p.payloadLen() >= sizeof(sv.rcSticks)) {
                memcpy(sv.rcSticks, &bytes[1], sizeof sv.rcSticks);
                Inputs::loadStickParams();
                Params::sys.mark();
            }
        }
        break;

    case ButtonFunctionCfg:
        if (p.payloadLen() >= ButtonFunction::Config::MIN_LEN && p.payloadLen() < sizeof(ButtonFunction::Config)) {
            const ButtonFunction::Config *pcfg = reinterpret_cast<const ButtonFunction::Config*>(&bytes[1]);
            Io::ButtonID id = static_cast<Io::ButtonID>(pcfg->buttonID);

            if (ButtonManager::setButtonFunction(id, pcfg)) {
                Params::sys.mark();
                Ui::instance.pendEvent(Event::ButtonFunctionUpdated);
            }
        }
        break;

    case Mavlink:
        Mavlink::onMavlinkData(&bytes[1], p.payloadLen());
        break;

    case PairRequest:
        VehicleConnector::instance.onPairingRequest(&bytes[1], p.payloadLen());
        break;

    case PairResult:
        VehicleConnector::instance.onPairingResult(&bytes[1], p.payloadLen());
        break;

    case OutputTest:
        FactoryTest::onOutputTest(&bytes[1], p.payloadLen());
        break;

    case SetShotInfo: {
        const char *si = reinterpret_cast<const char*>(&bytes[1]);
        Ui::instance.gimbal.onShotChanged(si);
        Ui::instance.topBar.onShotChanged(si);
    } break;

    case Updater:
        onUpdaterMsg(&bytes[1], p.payloadLen());
        break;

    case LockoutState:
        if (p.payloadLen() >= 1) {
            Lockout::onHostProtoMsg(bytes[1]);
        }
        break;

    case SelfTest:
        static const uint64_t SelfTestMagic = 0x73656c6674657374;
        if (p.payloadLen() >= sizeof(SelfTestMagic) &&
            memcmp(&bytes[1], &SelfTestMagic, sizeof SelfTestMagic) == 0)
        {
            SelfTest::checkForShorts();
        }
        break;

    case GpioTest:
        FactoryTest::onGpioTest(&bytes[1], p.payloadLen());
        break;

    case TestEvent:
        if (p.payloadLen() >= 1){
            if (Event::isValid(bytes[1])) {
                Event::ID event = static_cast<Event::ID>(bytes[1]);
                Ui::instance.pendEvent(event);
            } else {
                DBG(("[host_protocol.cpp] Received event is invalid.\n"));
            }
        }
        break;

    case SetTelemUnits:
        if (p.payloadLen() >= 1){
            Ui::instance.telem.onUnitsChanged(bytes[1]);
        }
        break;

    case SoloAppConnection: // TODO: If there's more of these iMX6->STM32 type alerts we chould think about combining them all together, leaving like this for now
        if (p.payloadLen() >= 1){
            Ui::instance.telem.onSoloAppConnChanged(bytes[1]);
        }
        break;
    }
}

void HostProtocol::onUpdaterMsg(const uint8_t *bytes, unsigned len)
{
    // XXX: find a better home for this some day

    if (len >= 1) {
        switch (bytes[0]) {
        case 0: // begin
        case 1: // success
        case 2: // fail
            Ui::instance.pendEvent(static_cast<Event::ID>(Event::SystemUpdateBegin + bytes[0]));
            break;
        }
    }
}
