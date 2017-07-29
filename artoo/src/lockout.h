#ifndef LOCKOUT_H
#define LOCKOUT_H

#include "tasks.h"
#include "hostprotocol.h"

class Lockout
{
public:
    Lockout();  // do not implement

    static inline bool isUnlocked() {
        return (lockedOut == false);
    }

private:
    static bool lockedOut;

    static void onHostProtoMsg(bool locked);
    friend class HostProtocol;
};

#endif // LOCKOUT_H
