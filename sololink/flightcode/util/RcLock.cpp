
#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>
#include "file_util.h"
#include "RcLock.h"

namespace RcLock
{

// must match rc_lock.py
static const char *ro_lockfile = "/mnt/rootfs.ro/etc/.rc_lock";
static const char *tmp_lockfile = "/tmp/.rc_lock";
static const char *tmp_unlockfile = "/tmp/.rc_unlock";

// locked - see if RC is locked
//
// Returns true if RC is locked, false if not locked.
bool locked(void)
{

    if (file_exists(tmp_unlockfile))
        return false;
    else if (file_exists(tmp_lockfile) || file_exists(ro_lockfile))
        return true;
    else
        return false;
}

// lock_version - lock RC due to version mismatch
void lock_version(void)
{
    file_touch(tmp_lockfile);
}

// unlock_version - unlock RC (versions match)
void unlock_version(void)
{
    unlink(tmp_lockfile);
}

// unlock_override - unlock RC
void unlock_override(void)
{
    file_touch(tmp_unlockfile);
}

} // namespace RcLock
