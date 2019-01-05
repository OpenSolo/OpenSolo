#ifndef UI_POWER_H
#define UI_POWER_H


class UiPower
{
public:
    UiPower();

    void initShutdown();
    bool updateShutdown();

    void drawBatteryCheck();
    void drawChargerConnected();
    void drawBatteryTooLowToStart();

private:
    // currently we hard code this, would be better to
    // timeout on a heartbeat from the imx6
    static const unsigned IMX6_SHUTDOWN_SECONDS = 17;

    void drawSpinner();
    void drawBattery();

    bool reportedLifeAfterDeath;
    unsigned spinnerFrame;
};

#endif // UI_POWER_H
