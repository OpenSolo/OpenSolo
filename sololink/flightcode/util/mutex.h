#ifndef MUTEX_H
#define MUTEX_H

#include <stdint.h>
#include <pthread.h>

#ifdef __cplusplus
extern "C" {
#endif

extern void mutex_attr_show(const pthread_mutexattr_t *attr);
extern int mutex_init(pthread_mutex_t *mutex);
extern int mutex_lock(pthread_mutex_t *mutex, uint64_t *max_blocked_us);
extern int mutex_unlock(pthread_mutex_t *mutex);

#ifdef __cplusplus
};
#endif

#endif /* MUTEX_H */
