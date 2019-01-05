#ifndef BUZZER_H
#define BUZZER_H

#include "stm32/hwtimer.h"

class Buzzer
{
public:

    static void init(unsigned hz);

    static void setFrequency(unsigned hz);
    static void play();
    static void stop();

private:

};

#endif // BUZZER_H
