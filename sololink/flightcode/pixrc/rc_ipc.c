
#include <fcntl.h>
#include <semaphore.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/types.h>
#include "rc_pkt.h"
#include "rc_ipc.h"

/* these must start with slash then contain no more slashes */
#define RC_IPC_SHM_NAME "/rc_shm"
#define RC_IPC_SEM_NAME "/rc_sem"

/*
 * Information about an instance of the RC IPC. One of these is allocated and
 * returned from create or attach, and passed back to the other functions. An
 * application must eventually give it to detach/delete to free it.
 */
struct rc_ipc_info {
    uint32_t magic;
    struct rc_pkt *pkt;
    sem_t *sem;
};

#define RC_IPC_INFO_MAGIC 0x21436587

/* return rc_ipc_id pointer on success, NULL on error */
void *rc_ipc_attach(int verbosity)
{
    struct rc_ipc_info *info;
    int fd;

    info = (struct rc_ipc_info *)malloc(sizeof(struct rc_ipc_info));
    if (info == NULL) {
        if (verbosity > 0)
            perror("malloc");
        return NULL;
    }

    memset(info, 0, sizeof(struct rc_ipc_info));

    /* create or attach shared memory */

    fd = shm_open(RC_IPC_SHM_NAME, O_RDWR | O_CREAT, 0666);
    if (fd < 0) {
        if (verbosity > 0)
            perror("shm_open");
        free(info);
        return NULL;
    }

    if (ftruncate(fd, sizeof(struct rc_pkt)) != 0) {
        if (verbosity > 0)
            perror("ftruncate");
        close(fd); /* instead of shm_unlink() */
        free(info);
        return NULL;
    }

    info->pkt = mmap(NULL, sizeof(struct rc_pkt), PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    if (info->pkt == MAP_FAILED) {
        if (verbosity > 0)
            perror("mmap");
        close(fd);
        free(info);
        return NULL;
    }

    /* after mapping, the fd is no longer needed */
    close(fd);

    /* create semaphore */

    info->sem = sem_open(RC_IPC_SEM_NAME, O_CREAT, 0666, 1);
    if (info->sem == SEM_FAILED) {
        if (verbosity > 0)
            perror("sem_open");
        munmap(info->pkt, sizeof(struct rc_pkt));
        free(info);
        return NULL;
    }

    info->magic = RC_IPC_INFO_MAGIC;

    if (verbosity > 1)
        printf("%s: shared memory and semaphore created\n", __FUNCTION__);

    return (void *)info;

} /* rc_ipc_attach */

/* return 0 on success, nonzero on error */
int rc_ipc_put(void *rc_ipc_id, const struct rc_pkt *pkt, int verbosity)
{
    struct rc_ipc_info *info = (struct rc_ipc_info *)rc_ipc_id;

    /* sanity check */
    if (info->magic != RC_IPC_INFO_MAGIC) {
        printf("%s: ERROR: bad magic\n", __FUNCTION__);
        return -1;
    }

    /* lock */
    if (sem_wait(info->sem) != 0) {
        if (verbosity > 0)
            perror("sem_wait");
        return -1;
    }

    /* write packet */
    memcpy(info->pkt, pkt, sizeof(struct rc_pkt));

    /* unlock */
    if (sem_post(info->sem) != 0) {
        if (verbosity > 0)
            perror("sem_post");
        return -1;
    }

    if (verbosity > 1)
        printf("%s: packet written to shared memory\n", __FUNCTION__);

    return 0;

} /* rc_ipc_put */

/* return 0 on success, nonzero on error */
int rc_ipc_get(void *rc_ipc_id, struct rc_pkt *pkt, int verbosity)
{
    struct rc_ipc_info *info = (struct rc_ipc_info *)rc_ipc_id;

    /* sanity check */
    if (info->magic != RC_IPC_INFO_MAGIC) {
        printf("%s: ERROR: bad magic\n", __FUNCTION__);
        return -1;
    }

    /* lock */
    if (sem_wait(info->sem) != 0) {
        if (verbosity > 0)
            perror("sem_wait");
        return -1;
    }

    /* read packet */
    memcpy(pkt, info->pkt, sizeof(struct rc_pkt));

    /* unlock */
    if (sem_post(info->sem) != 0) {
        if (verbosity > 0)
            perror("sem_post");
        return -1;
    }

    if (verbosity > 1)
        printf("%s: packet read from shared memory\n", __FUNCTION__);

    return 0;

} /* rc_ipc_get */

/* return 0 on success, nonzero on error */
int rc_ipc_detach(void *rc_ipc_id, int verbosity)
{
    struct rc_ipc_info *info = (struct rc_ipc_info *)rc_ipc_id;
    int status = 0;

    /* sanity check */
    if (info->magic != RC_IPC_INFO_MAGIC) {
        printf("%s: ERROR: bad magic\n", __FUNCTION__);
        return -1;
    }

    info->magic = 0;

    if (munmap(info->pkt, sizeof(struct rc_pkt)) != 0) {
        perror("munmap");
        status = -1;
    }
    info->pkt = NULL;

    if (sem_close(info->sem) != 0) {
        perror("sem_close");
        status = -1;
    }
    info->sem = NULL;

    free(info);

    return status;

} /* rc_ipc_detach */
