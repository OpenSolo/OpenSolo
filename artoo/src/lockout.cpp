#include "lockout.h"
#include "ui.h"

// default to unlocked
bool Lockout::lockedOut;

void Lockout::onHostProtoMsg(bool locked)
{
    if (lockedOut != locked) {
        lockedOut = locked;

        // workaround for https://3drsolo.atlassian.net/browse/AR-481
        // we update the lockout state, but don't update the ui if an update
        // is in progress, since we want to wait for the update complete/failed
        // event before proceeding
        Ui &ui = Ui::instance;
        if (!(ui.state() == Ui::Updater && ui.updater.updateInProgress())) {
            ui.pendEvent(Event::SystemLockoutStateChanged);
        }
    }
}
