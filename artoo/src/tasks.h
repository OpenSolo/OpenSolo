#ifndef TASKS_H
#define TASKS_H

#include "machine.h"

/*
 * Tasks are potentially longer running operations
 * that can't happen in ISR context. They can be scheduled from
 * ISR context, and will run at the next available opportunity
 * on the main thread of execution.
 */

class Tasks
{
public:

    // Order defines task priority, higher priorities come first.
    enum TaskID {
        HostProtocol,
        FiftyHzHeartbeat,
        DisplayRender,
        ButtonHold,
        Haptic,
        Camera,
        Shutdown,
    };

    Tasks();    // do not implement

    static const unsigned HEARTBEAT_HZ = 50;

    // One-shot, execute a task once at the next opportunity
    static ALWAYS_INLINE void trigger(TaskID id) {
        Atomic::SetLZ(pendingMask, id);
    }

    static void cancel(TaskID id) {
        uint32_t mask = ~Intrinsic::LZ(id);
        Atomic::And(pendingMask, mask);
    }

    static bool work();
    static void heartbeat();

private:
    static uint32_t pendingMask;

    static ALWAYS_INLINE void invoke(unsigned id);
};

#endif // TASKS_H
