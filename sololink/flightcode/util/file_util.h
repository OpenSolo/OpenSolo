#ifndef FILE_UTIL_H
#define FILE_UTIL_H

#ifdef __cplusplus
extern "C" {
#endif

extern int file_exists(const char *filename);
extern int file_touch(const char *filename);

#ifdef __cplusplus
};
#endif

#endif /* FILE_UTIL_H */
