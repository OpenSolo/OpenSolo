#ifndef _LOG_H
#define _LOG_H

#include <stdio.h>
#include <string.h>
#include <fstream>

using namespace std;

/**********************************************************************
Class: Log

Description: A simple logging class.  Opens a logfile specified by the
             calling function.  The log file can be rolled when its
             size gets large enough, out to maxLogFiles files.
***********************************************************************/
class Log
{
public:
    Log(string filename, long int maxFileSize, int maxLogFiles);
    Log(string filename, long int maxFileSize, int maxLogFiles, bool newLogOnBoot);
    void checkSizeAndRoll(void);
    void forceRoll(void);

    // Left as a public for use in logging macros
    const char *getTimeString(void);

    // Leave the file descriptor public so it can be written to
    // by the calling application.
    ofstream log_fd;

private:
    long int _maxFileSize;
    int _maxLogFiles;
    string _logFilename;

    bool doesFileExist(string filename);
    long int getFilesize(string filename);
};

#endif //_LOG_H
