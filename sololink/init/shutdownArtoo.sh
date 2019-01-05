#!/bin/sh

IMX_POWER=21
BOARD_POWER=19
GPIODIR=/sys/class/gpio

#sync, shutdown hard drives
/sbin/halt -w -h

echo $BOARD_POWER >> $GPIODIR/export
echo out >> $GPIODIR/gpio$BOARD_POWER/direction
echo 0 >> $GPIODIR/gpio$BOARD_POWER/value

echo $IMX_POWER >> $GPIODIR/export
echo out >> $GPIODIR/gpio$IMX_POWER/direction
echo 0 >> $GPIODIR/gpio$IMX_POWER/value

#
# the stm32 is ready to shut down before we are,
# but we rely on it to wait for us, so that the entire
# system can agree that we're powered down.
#
# rough timeline:
#  - stm32 gets hold-pwr-button-to-shutdown gesture, sends please-shutdown msg
#  - imx6 starts shutting down, stm32 shows progress spinner & keeps power to imx6 enabled
#  - stm32 waits a hard coded duration for imx6 shutdown to complete. would prefer to timeout on a heartbeat, or similar.
#  - stm32 ensures power button has been released long enough for rc circuit to discharge
#  - stm32 disables power to the imx6 and either turns off if charger is not there, or goes to sleep
#