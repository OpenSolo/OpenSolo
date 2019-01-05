#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <iostream>
#include <iomanip>
#include <stdint.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/time.h>
#include <netdb.h>
#include <time.h>
#include <termios.h>
#include <sys/errno.h>
#include <sys/ioctl.h>
#include <list>
#include <sys/mman.h>
#include <fstream>
#include <poll.h>
#include "util.h"
#include "../mavlink/c_library/ardupilotmega/mavlink.h"
#include "../mavlink/c_library/common/mavlink.h"
#include <sstream>
#include <signal.h>
#include <pthread.h>
#include <semaphore.h>
#include <dirent.h>

using namespace std;

/***********************************************************************
Serial port name
***********************************************************************/
string serialPortName;

/***********************************************************************
File descriptors
***********************************************************************/
int serial_fd;

/***********************************************************************
Threading variables
***********************************************************************/
pthread_mutex_t mutex_msg;
pthread_mutex_t mutex_msgtype;
mavlink_message_t latest_msg;
sem_t sem_msg;
int msg_type = 0;

/***********************************************************************
Log file variables
***********************************************************************/
int log_size;
ofstream logfile;
int log_num = 0;

/***********************************************************************
User input variables
***********************************************************************/
bool get_latest = false;

/***********************************************************************
Serial tx/rx buffer size
***********************************************************************/
#define BUFSIZE 256

/***********************************************************************
Pointer to log buffer.  Allocate a really big buffer later
that is the size of the log file.  This is probably not the best way
to go about this, but it works in a pinch.
***********************************************************************/
char *logbuf;

/***********************************************************************
Function: int serial_setup(int baud)

Description: The serial port initialization function.  This function
             initializes the serial port over which DSM data is sent to
             the pixhawk.  A return of 0 indicates an error.
***********************************************************************/
int serial_setup(int baud)
{
    struct termios options;

    serial_fd = open(serialPortName.c_str(), O_RDWR | O_NOCTTY);

    if (serial_fd < 0) {
        cerr << "Unable to open serial port " << serialPortName.c_str() << endl;
        return 0;
    }

    tcflush(serial_fd, TCIOFLUSH);

    // Configure port for 8N1 transmission
    tcgetattr(serial_fd, &options); // Gets the current options for the port
    // Set the output baud rate
    switch (baud) {
    case 57600:
        cfsetspeed(&options, B57600);
        break;
    case 115200:
        cfsetspeed(&options, B115200);
        break;
    case 1500000:
        cfsetspeed(&options, B1500000);
        break;
    default:
        cerr << "Unsupported baud rate" << endl;
        return 0;
    }
    options.c_iflag &= ~(IGNBRK | BRKINT | ICRNL | INLCR | PARMRK | INPCK | ISTRIP | IXON);
    options.c_oflag &= ~(OCRNL | ONLCR | ONLRET | ONOCR | OFILL | OPOST);
    options.c_lflag &= ~(ECHO | ECHONL | ICANON | IEXTEN | ISIG);
    options.c_cflag &= ~(CSIZE | PARENB);
    options.c_cflag |= CS8;
    options.c_cflag |= CRTSCTS;
    options.c_cc[VMIN] = 17;
    options.c_cc[VTIME] = 0;

    tcsetattr(serial_fd, TCSANOW, &options); // Set the new options for the port "NOW"

    sleep(1);
    tcflush(serial_fd, TCIOFLUSH);

    cout << "Opened serial port " << serialPortName.c_str() << endl;

    return 1;
}

/***********************************************************************
Function: int print_pct()

Description: Prints a pct bar on the console and displays the
             current download speed.
***********************************************************************/
void print_pct(float pct, float speed)
{
    int maxWidth = 50;
    int pos;
    int i;

    cout << "[";
    pos = maxWidth * pct;
    for (i = 0; i < maxWidth; ++i) {
        if (i < pos)
            cout << "=";
        else if (i == pos)
            cout << ">";
        else
            cout << " ";
    }
    cout << "] " << int(pct * 100.0) << "%";
    cout << " " << speed << " kB/s  \r";
    cout << flush;
}

/***********************************************************************
Function: int handle_log_data()

Description: Take log data and dump it into a log file
***********************************************************************/
int handle_log_data(mavlink_message_t *msg)
{
    int ofs, cnt, id;
    uint64_t now_us;
    float speed = 0.0;
    char logdat[128];

    static int fileofs = 0;
    static int disc_cnt = 0;
    static uint64_t last_us = 0;
    static int bytes_received = 0;
    static int last_bytes_received = 0;
    static char *buf_ptr = logbuf;

    id = mavlink_msg_log_data_get_id(msg);

    if (id != log_num) {
        cout << "Got data from a different log, ignoring" << endl;
        return 0;
    }

    ofs = mavlink_msg_log_data_get_ofs(msg);
    cnt = mavlink_msg_log_data_get_count(msg);
    mavlink_msg_log_data_get_data(msg, (uint8_t *)logdat);

    // I don't think this ever happens, but if we get a zero
    // count then we're done
    if (cnt == 0) {
        cout << endl;
        cout << "Log download complete" << endl;
        return 1;
    }

    // Write data directly to the (really big) buffer
    memcpy(buf_ptr, logdat, cnt);
    buf_ptr += cnt;

    if (fileofs != ofs)
        disc_cnt++;

    now_us = clock_gettime_us(CLOCK_MONOTONIC);

    bytes_received += cnt;

    // Output
    if ((now_us - last_us) > 1e6) {
        speed =
            float(bytes_received - last_bytes_received) / 1024. / float((now_us - last_us) / 1e6);

        print_pct(float(bytes_received) / float(log_size), speed);

        last_us = now_us;
        last_bytes_received = bytes_received;
    }

    // Update the file position
    fileofs = ofs + cnt;

    // Are we done yet?
    if (fileofs == log_size) {
        print_pct(1, speed);
        cout << endl;
        cout << "Log download complete." << endl;
        cout << "Downloaded " << float(bytes_received) / 1024. << "kB, dropped " << disc_cnt
             << " packet(s)" << endl;
        return 1;
    }

    return 0;
}

/***********************************************************************
Function: int mavlink_task()

Description: Thread task to pull mavlink data from the serial port
             and dump it into a mutex-protected mavlink message.

             When log data begins streaming, dumps log data into the
             log file on the filesystem.
***********************************************************************/
void *mavlink_task(void *)
{
    mavlink_message_t _msg;
    mavlink_status_t mavlink_status;
    int read_len;
    int i;
    char buf[BUFSIZE];
    int msgtolookfor;

    while (1) {
        read_len = read(serial_fd, buf, BUFSIZE);

        if (read_len < 0) {
            if (errno != EAGAIN)
                cerr << "Read err: " << errno << endl;
        }

        if (read_len > 0) {
            for (i = 0; i < read_len; ++i) {
                if (mavlink_parse_char(MAVLINK_COMM_0, buf[i], &_msg, &mavlink_status)) {
                    // If this is the type of message we're waiting for, put it on
                    // the latest_msg or handle its log data.
                    pthread_mutex_lock(&mutex_msgtype);
                    msgtolookfor = msg_type;
                    pthread_mutex_unlock(&mutex_msgtype);

                    if (_msg.msgid == msgtolookfor) {
                        if (_msg.msgid == MAVLINK_MSG_ID_LOG_DATA) {
                            if (handle_log_data(&_msg)) {
                                cout << "Writing to logfile...";
                                logfile.write(logbuf, log_size);
                                system("sync");
                                cout << "Done!" << endl;
                                pthread_exit(NULL);
                            }
                        } else {
                            pthread_mutex_lock(&mutex_msg);
                            memcpy(&latest_msg, &_msg, sizeof(mavlink_message_t));
                            pthread_mutex_unlock(&mutex_msg);
                            sem_post(&sem_msg);
                        }
                    }
                }
            }
        }
    }
    pthread_exit(NULL);
}

/***********************************************************************
Function: int wait_for_message()

Description: Blocks until a particular mavlink message type is received.
             A return value of 0 indicates succes, -1 for a timeout.
             Setting timeout_s to 0 blocks indefinitely.
***********************************************************************/
int wait_for_message(int _msg_type, mavlink_message_t *msg, int timeout_s)
{
    struct timespec timeout;
    int ret;

    // Tell the mavlink thread which message to look for
    pthread_mutex_lock(&mutex_msgtype);
    msg_type = _msg_type;
    pthread_mutex_unlock(&mutex_msgtype);

    clock_gettime(CLOCK_REALTIME, &timeout);
    timeout.tv_sec += timeout_s;

    if (timeout_s == 0)
        sem_wait(&sem_msg);
    else {
        ret = sem_timedwait(&sem_msg, &timeout);

        if (ret < 0) {
            if (errno == ETIMEDOUT)
                return -1;
        }
    }

    pthread_mutex_lock(&mutex_msg);
    memcpy(msg, &latest_msg, sizeof(mavlink_message_t));
    pthread_mutex_unlock(&mutex_msg);

    return 0;
}

/***********************************************************************
Function: void request_log()

Description: Request a particular log file from the pixhawk.
***********************************************************************/
void request_log(void)
{
    char buf[BUFSIZE];
    mavlink_message_t msg;
    int msg_len;
    char logfilename[] = "/log/log12345.bin";

    // Wait for a heartbeat
    if (wait_for_message(MAVLINK_MSG_ID_HEARTBEAT, &msg, 5) < 0) {
        cout << "No heartbeat received" << endl;
        exit(1);
    }

    // Get the latest log number (num_logs works, last_log_num doesn't)
    if (get_latest) {
        mavlink_msg_log_request_list_pack(1, 1, &msg, 1, 1, log_num, log_num);
        msg_len = mavlink_msg_to_send_buffer((uint8_t *)buf, &msg);

        if (write(serial_fd, buf, msg_len) != msg_len) {
            cerr << "Serial port write error." << endl;
            exit(1);
        }

        cout << "Requesting latest log number...";

        if (wait_for_message(MAVLINK_MSG_ID_LOG_ENTRY, &msg, 10) < 0) {
            cout << "Unable to get log information" << endl;
            exit(1);
        }

        log_num = mavlink_msg_log_entry_get_num_logs(&msg);
        cout << "Latest log is " << log_num << endl;
    }

    // Get some size information about the log we want.
    mavlink_msg_log_request_list_pack(1, 1, &msg, 1, 1, log_num, log_num);
    msg_len = mavlink_msg_to_send_buffer((uint8_t *)buf, &msg);
    if (write(serial_fd, buf, msg_len) != msg_len) {
        cerr << "Serial port write error." << endl;
        exit(1);
    }

    cout << "Waiting for log information..." << endl;

    if (wait_for_message(MAVLINK_MSG_ID_LOG_ENTRY, &msg, 10) < 0) {
        cout << "Unable to get log information" << endl;
        exit(1);
    }

    log_size = mavlink_msg_log_entry_get_size(&msg);
    if (log_size == 0) {
        cout << "Log " << log_num << " does not exist." << endl;
        exit(1);
    } else {
        cout << "Log size is " << float(log_size) / 1024. << "kB" << endl;

        logbuf = new char[log_size];
        if (logbuf == NULL) {
            cout << "Unable to allocate buffer for log" << endl;
            exit(1);
        }
    }

    // Set up the log file storage
    sprintf(logfilename, "/log/log%i.bin", log_num);
    logfile.open(logfilename, ios::out | ios::binary);

    // Request log data
    cout << "Beginning log download..." << endl;
    mavlink_msg_log_request_data_pack(1, 1, &msg, 1, 1, log_num, 0, 0xFFFFFFFF);
    msg_len = mavlink_msg_to_send_buffer((uint8_t *)buf, &msg);

    // Let the thread know we've requested data.
    pthread_mutex_lock(&mutex_msgtype);
    msg_type = MAVLINK_MSG_ID_LOG_DATA;
    pthread_mutex_unlock(&mutex_msgtype);

    if (write(serial_fd, buf, msg_len) != msg_len) {
        cerr << "Serial port write error." << endl;
        exit(1);
    }

    // Let the mavlink thread do its thing
}

/**********************************************************************
Function: int main(void)

Description: The main function.  Initializes and runs the serial and
             UDP threads.
***********************************************************************/
int main(int argc, char *argv[])
{
    int baudrate;
    pthread_t mavlink_ctx;
    char usbdev_string[256] = "usb-3D_Robotics_PX4_FMU";
    DIR *dir;
    struct dirent *direntry;
    bool foundDevice = false;

    if (argc < 2) {
        cout << "Usage: dflog <lognum|latest>" << endl;
        return -1;
    }

    if (strcmp(argv[1], "latest") == 0) {
        cout << "Pulling latest log" << endl;
        get_latest = true;
    } else {
        log_num = atoi(argv[1]);
        cout << "Pulling log " << log_num << endl;
    }

    // Cout cleanup
    std::cout.precision(2);
    std::cout.setf(ios::fixed, ios::floatfield);

    dir = opendir("/dev/serial/by-id/");
    if (dir == NULL) {
        cerr << "open /dev/serial/by-id failed" << endl;
        return -1;
    }

    while ((direntry = readdir(dir))) {
        if (!strncmp(direntry->d_name, usbdev_string, 23)) {
            foundDevice = true;
            strcpy(usbdev_string, direntry->d_name);
            break;
        }
    }

    if (!foundDevice) {
        cerr << "Unable to find USB device" << endl;
        return -1;
    }

    closedir(dir);

    // Serial port setup
    serialPortName = "/dev/serial/by-id/";
    serialPortName.append(usbdev_string);
    baudrate = 115200;
    if (!serial_setup(baudrate)) {
        cerr << "Unable to initialize the serial send" << endl;
        return -1;
    }

    // Threading initialization
    pthread_mutex_init(&mutex_msg, NULL);
    sem_init(&sem_msg, 0, 0);

    // Start the mavlink rx thread
    pthread_create(&mavlink_ctx, NULL, mavlink_task, NULL);

    // Send a log request to the pixhawk
    request_log();

    // Wait for the mavlink thread to end
    pthread_join(mavlink_ctx, NULL);

    logfile.close();

    return 0;
}
