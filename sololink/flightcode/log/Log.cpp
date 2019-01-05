#include <iostream>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <sstream>
#include <fstream>
#include "util.h"
#include "Log.h"

using namespace std;

/**********************************************************************
Function: Log()

Description: The log constructor.  Opens an fstream file based on
             the filename string.  Sets the maximum size of the log file
             and the maximum number of log files to be written.
***********************************************************************/
Log::Log(string filename, long int maxFileSize, int maxLogFiles)
    : _maxFileSize(maxFileSize), _maxLogFiles(maxLogFiles), _logFilename(filename)
{
    log_fd.precision(2);
    log_fd.setf(ios::fixed, ios::floatfield);

    // Open the log file
    log_fd.open(filename.c_str(), ios::out | std::ofstream::app);
    if (!log_fd) {
        cerr << "Could not open log file" << endl;
        return;
    }
}

/**********************************************************************
Function: Log()

Description: Overloaded log constructor with an option for creating a
             new log when the log starts up
***********************************************************************/
Log::Log(string filename, long int maxFileSize, int maxLogFiles, bool newLogOnBoot)
    : _maxFileSize(maxFileSize), _maxLogFiles(maxLogFiles), _logFilename(filename)
{
    log_fd.precision(2);
    log_fd.setf(ios::fixed, ios::floatfield);
    bool fileExists = doesFileExist(filename);

    // Open the log file
    log_fd.open(filename.c_str(), ios::out | std::ofstream::app);
    if (!log_fd) {
        cerr << "Could not open log file" << endl;
        return;
    }

    if (newLogOnBoot && fileExists)
        forceRoll();
}

/**********************************************************************
Function: getFilesize()

Description: Gets the filesize of a file named by filename
***********************************************************************/
long int Log::getFilesize(string filename)
{
    struct stat filestatus;

    stat(filename.c_str(), &filestatus);

    return filestatus.st_size;
}

/**********************************************************************
Function: doesFileExist()

Description: Returns a bool indicating if the file named filename
             exists.  filename must be an absolute path.
***********************************************************************/
bool Log::doesFileExist(string filename)
{
    struct stat filestatus;

    return (stat(filename.c_str(), &filestatus) == 0);
}

/***********************************************************************
Function: char* getTimeString(void)

Description: Gets the current time string.
 ***********************************************************************/
const char *Log::getTimeString(void)
{
    static char buffer[80];

    clock_gettime_str_r(CLOCK_REALTIME, buffer);

    return buffer;
}

/**********************************************************************
Function: checkSizeAndRoll()

Description:  Checks to see if the log file has grown too big and should
              be rolled over.  Rolls it and all previous logfiles
              if necessary.  The calling application should call this
              function periodically after writing to the logfile.
***********************************************************************/
void Log::checkSizeAndRoll(void)
{
    stringstream filename, newfilename;

    // Check the size of the file.  If its too big, roll the logfiles.
    if (getFilesize(_logFilename) > _maxFileSize) {
        // Roll the log files up to the max-1
        for (int i = 1; i < _maxLogFiles; ++i) {
            filename.str(string());
            filename << _logFilename.c_str() << "." << dec << (int)(_maxLogFiles - i);

            // See if the file exists
            if (doesFileExist(filename.str())) {
                newfilename.str(string());
                newfilename << _logFilename.c_str() << "." << dec << (int)(_maxLogFiles - i + 1);

                rename(filename.str().c_str(), newfilename.str().c_str());
            }
        }

        // Roll the current file
        log_fd.close();
        rename(_logFilename.c_str(), filename.str().c_str());
        log_fd.open(_logFilename.c_str(), ios::out | std::ofstream::app);
    }
}

/**********************************************************************
Function: forceRoll()

Description:  Forces a file roll
***********************************************************************/
void Log::forceRoll(void)
{
    stringstream filename, newfilename;

    // Roll the log files up to the max-1
    for (int i = 1; i < _maxLogFiles; ++i) {
        filename.str(string());
        filename << _logFilename.c_str() << "." << dec << (int)(_maxLogFiles - i);

        // See if the file exists
        if (doesFileExist(filename.str())) {
            newfilename.str(string());
            newfilename << _logFilename.c_str() << "." << dec << (int)(_maxLogFiles - i + 1);

            rename(filename.str().c_str(), newfilename.str().c_str());
        }
    }

    // Roll the current file
    log_fd.close();
    rename(_logFilename.c_str(), filename.str().c_str());
    log_fd.open(_logFilename.c_str(), ios::out | std::ofstream::app);
}
