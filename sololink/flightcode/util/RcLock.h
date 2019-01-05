#ifndef RC_LOCK_H
#define RC_LOCK_H

namespace RcLock
{

extern bool locked(void);
extern void lock_version(void);
extern void unlock_version(void);
extern void unlock_override(void);

} // namespace RcLock

#endif // RC_LOCK_H
