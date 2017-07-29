
#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>
#include <fcntl.h>
#include "file_util.h"

/*
* file_exists - determine whether a file exists
*
* Return nonzero (true) if file exists, zero (false) if file does not exist.
*/
int file_exists(const char *filename)
{
    struct stat file_stat;
    return (stat(filename, &file_stat) == 0);
}

/*
* file_touch - create file if it does not exist
*
* Method of doing this (the mode flags) is per 'man touch'.
*/
int file_touch(const char *filename)
{
    int fd;
    mode_t mode;

    mode = S_IRUSR | S_IWUSR | S_IRGRP | S_IWGRP | S_IROTH | S_IWOTH;

    fd = creat(filename, mode);
    if (fd < 0) {
        return 0;
    } else {
        close(fd);
        return 1;
    }
}
