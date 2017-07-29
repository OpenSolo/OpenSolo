
#include <pthread.h>
#include <stdio.h>
#include <stdint.h>
#include "util.h"
#include "mutex.h"

/*
* mutex_type_str - return string name of mutex type attribute (debug)
*/
static const char *mutex_type_str(int type)
{
    switch (type) {
    case PTHREAD_MUTEX_NORMAL:
        return "PTHREAD_MUTEX_NORMAL";
    case PTHREAD_MUTEX_ERRORCHECK:
        return "PTHREAD_MUTEX_ERRORCHECK";
    case PTHREAD_MUTEX_RECURSIVE:
        return "PTHREAD_MUTEX_RECURSIVE";
    /* PTHREAD_MUTEX_DEFAULT = PTHREAD_MUTEX_NORMAL */
    default:
        return "UNKNOWN";
    }
}

/*
* mutex_protocol_str - return string name of mutex protocol attribute (debug)
*/
static const char *mutex_protocol_str(int protocol)
{
    switch (protocol) {
    case PTHREAD_PRIO_NONE:
        return "PTHREAD_PRIO_NONE";
    case PTHREAD_PRIO_INHERIT:
        return "PTHREAD_PRIO_INHERIT";
    case PTHREAD_PRIO_PROTECT:
        return "PTHREAD_PRIO_PROTECT";
    default:
        return "UNKNOWN";
    }
}

/*
* mutex_pshared_str - return string name of mutex pshared attribute (debug)
*/
static const char *mutex_pshared_str(int pshared)
{
    switch (pshared) {
    case PTHREAD_PROCESS_SHARED:
        return "PTHREAD_PROCESS_SHARED";
    case PTHREAD_PROCESS_PRIVATE:
        return "PTHREAD_PROCESS_PRIVATE";
    default:
        return "UNKNOWN";
    }
}

/*
* mutex_attr_show - print mutex attributes to stdout (debug)
*/
void mutex_attr_show(const pthread_mutexattr_t *attr)
{
    int rc;
    int val;

    printf("mutex attributes @ %10p:\n", attr);

    rc = pthread_mutexattr_gettype(attr, &val);
    if (rc != 0)
        printf("ERROR %d returned from pthread_mutexattr_gettype\n", rc);
    else
        printf("type=%s\n", mutex_type_str(val));

    rc = pthread_mutexattr_getprioceiling(attr, &val);
    if (rc != 0)
        printf("ERROR %d returned from pthread_mutexattr_getprioceiling\n", rc);
    else
        printf("prio_ceiling=%d\n", val);

    rc = pthread_mutexattr_getprotocol(attr, &val);
    if (rc != 0)
        printf("ERROR %d returned from pthread_mutexattr_getprotocol\n", rc);
    else
        printf("protocol=%s\n", mutex_protocol_str(val));

    rc = pthread_mutexattr_getpshared(attr, &val);
    if (rc != 0)
        printf("ERROR %d returned from pthread_mutexattr_getpshared\n", rc);
    else
        printf("pshared=%s\n", mutex_pshared_str(val));
}

/*
* mutex_init - initialize a mutex for use with realtime threads
*
* Default mutex attributes have a non-realtime priority ceiling, and do not
* have priority inversion enabled. This changes the defaults so the priority
* ceiling is the highest priority, priority inversion is enabled, and error
* checking it turned on.
*
* Attribute        Default                     Setting Here
* ---------------  --------------------------  --------------------------
* type             PTHREAD_MUTEX_NORMAL        PTHREAD_MUTEX_ERRORCHECK
* prio_ceiling     1                           99
* protocol         PTHREAD_PRIO_NONE           PTHREAD_PRIO_INHERIT
* pshared          PTHREAD_PROCESS_PRIVATE     PTHREAD_PROCESS_PRIVATE
*
* The priority specified for prio_ceiling is the SCHED_FIFO priority, i.e.
* 1 is lowest, 99 is highest.
*/
int mutex_init(pthread_mutex_t *mutex)
{
    pthread_mutexattr_t attr;
    int rc;

    /* set up attributes */

    rc = pthread_mutexattr_init(&attr);
    if (rc != 0)
        return rc;

    /* mutex_attr_show(&attr); */

    rc = pthread_mutexattr_settype(&attr, PTHREAD_MUTEX_ERRORCHECK);
    if (rc != 0)
        return rc;

    rc = pthread_mutexattr_setprioceiling(&attr, 99);
    if (rc != 0)
        return rc;

    rc = pthread_mutexattr_setprotocol(&attr, PTHREAD_PRIO_INHERIT);
    if (rc != 0)
        return rc;

    rc = pthread_mutexattr_setpshared(&attr, PTHREAD_PROCESS_PRIVATE);
    if (rc != 0)
        return rc;

    /* mutex_attr_show(&attr); */

    rc = pthread_mutex_init(mutex, &attr);
    if (rc != 0)
        return rc;

    return 0;

} /* mutex_init */

/*
* mutex_lock - lock mutex, keeping track of maximum block time
*
* If max_blocked_us is not NULL, measure how long it took to lock the
* mutex (how long we were blocked). Then, if the new blocked time was
* longer, update max_blocked_us; if the new blocked time was not
* longer, do not change max_blocked_us.
*
* To ignore how long the lock took, set max_blocked_us to NULL.
*
* To measure how long the lock took without regard to whether it is
* a new maximum, initialize *max_blocked_us to 0.
*/
int mutex_lock(pthread_mutex_t *mutex, uint64_t *max_blocked_us)
{
    int rc;
    uint64_t start_us;
    uint64_t blocked_us;

    if (max_blocked_us != NULL)
        start_us = clock_gettime_us(CLOCK_MONOTONIC);

    rc = pthread_mutex_lock(mutex);

    if (rc == 0 && max_blocked_us != NULL) {
        blocked_us = clock_gettime_us(CLOCK_MONOTONIC) - start_us;
        if (*max_blocked_us < blocked_us)
            *max_blocked_us = blocked_us;
    }

    return rc;

} /* mutex_lock */

/*
* mutex_unlock - unlock mutex
*
* Provided for symmetry with mutex_lock.
*/
int mutex_unlock(pthread_mutex_t *mutex)
{

    return pthread_mutex_unlock(mutex);

} /* mutex_unlock */
