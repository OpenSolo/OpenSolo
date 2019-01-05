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
Serial tx/rx buffer size
***********************************************************************/
#define BUFSIZE 256

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

    if(serial_fd < 0)
    {
        cerr << "Unable to open serial port " << serialPortName.c_str() << endl;
        return 0;
    }

    tcflush(serial_fd, TCIOFLUSH);

    //Configure port for 8N1 transmission
    tcgetattr(serial_fd, &options);      //Gets the current options for the port
    //Set the output baud rate
    switch(baud)
    {
        case 57600: cfsetspeed(&options, B57600); break;
        case 115200: cfsetspeed(&options, B115200); break;
        case 1500000: cfsetspeed(&options, B1500000); break;
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
    options.c_cc[VMIN]  = 17;
    options.c_cc[VTIME] = 0;

    tcsetattr(serial_fd, TCSANOW, &options);    //Set the new options for the port "NOW"

    //sleep(1);
    tcflush(serial_fd, TCIOFLUSH);

    cout << "Opened serial port " << serialPortName.c_str() << endl;

    return 1;
}

void connectUSB(void)
{
    system("echo 19 >> /sys/class/gpio/export");
    system("echo 21 >> /sys/class/gpio/export");
    system("echo out >> /sys/class/gpio/gpio19/direction");
    system("echo out >> /sys/class/gpio/gpio21/direction");
    system("echo 1 >> /sys/class/gpio/gpio21/value");
    system("echo 0 >> /sys/class/gpio/gpio19/value");

}

void disconnectUSB(void)
{
    system("echo 0 >> /sys/class/gpio/gpio21/value");
    system("echo 0 >> /sys/class/gpio/gpio19/value");
    system("echo 19 >> /sys/class/gpio/unexport");
    system("echo 21 >> /sys/class/gpio/unexport");
}

/***********************************************************************
Function: int mavlink_task()

Description: Thread task to pull mavlink data from the serial port
             and dump it into a mutex-protected mavlink message.

             When log data begins streaming, dumps log data into the 
             log file on the filesystem.
***********************************************************************/
void *mavlink_task(void*)
{
    mavlink_message_t _msg;
    mavlink_status_t mavlink_status;
    int read_len;
    int i;
    char buf[BUFSIZE];
    int msgtolookfor;

    while(1)
    {
        read_len = read(serial_fd, buf, BUFSIZE);

        if (read_len < 0)
        {
            if (errno != EAGAIN)
                cerr << "Read err: " << errno << endl;
        }

        if(read_len > 0)
        {
            for(i=0; i<read_len; ++i)
            {
                if(mavlink_parse_char(MAVLINK_COMM_0, buf[i], &_msg, &mavlink_status))
                {
                    //If this is the type of message we're waiting for, put it on
                    //the latest_msg or handle its log data.
                    pthread_mutex_lock(&mutex_msgtype);
                    msgtolookfor = msg_type;
                    pthread_mutex_unlock(&mutex_msgtype);

                    if(_msg.msgid == msgtolookfor)
                    {
                        pthread_mutex_lock(&mutex_msg);
                        memcpy(&latest_msg, &_msg, sizeof(mavlink_message_t));
                        pthread_mutex_unlock(&mutex_msg);
                        sem_post(&sem_msg);
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

    //Tell the mavlink thread which message to look for
    pthread_mutex_lock(&mutex_msgtype);
    msg_type = _msg_type;
    pthread_mutex_unlock(&mutex_msgtype);

    clock_gettime(CLOCK_REALTIME, &timeout);
    timeout.tv_sec += timeout_s;
    
    if(timeout_s == 0)
        sem_wait(&sem_msg);
    else
    {
        ret = sem_timedwait(&sem_msg, &timeout);

        if(ret < 0)
        {
            if (errno == ETIMEDOUT)
                return -1;
        }
    }

    pthread_mutex_lock(&mutex_msg);
    memcpy(msg, &latest_msg, sizeof(mavlink_message_t));
    pthread_mutex_unlock(&mutex_msg);

    return 0;
}

int open_USB_serial(void)
{
    char usbdev_string[256] = "usb-3D_Robotics_PX4_FMU";
    struct dirent *direntry;
    bool foundDevice = false;
    DIR *dir;

    connectUSB();
    sleep(1);

    dir = opendir("/dev/serial/by-id/");
    if (dir == NULL) {
        cerr << "open /dev/serial/by-id failed" << endl;
        return -1;
    }

    while((direntry = readdir(dir)))
    {
        if(!strncmp(direntry->d_name, usbdev_string, 23))
        {
            foundDevice = true;
            strcpy(usbdev_string,direntry->d_name);
            break;
        }
    }

    if(!foundDevice)
    {
        cerr << "Unable to find USB device" << endl;
        return -1;
    }

    closedir(dir);

    //Serial port setup
    serialPortName = "/dev/serial/by-id/";
    serialPortName.append(usbdev_string);
    if(!serial_setup(115200))
    {
        cerr << "Unable to initialize the USB serial port" << endl;
        return -1;
    }

    return 0;
}

/***********************************************************************
Function: void request_baudrate()

Description: Request a particular log file from the pixhawk.
***********************************************************************/
void request_baudrate(void)
{
    char buf[BUFSIZE];
    mavlink_message_t msg;
    int msg_len;
    float baud;
    int tries;
    bool gotParam=false;
        
    mavlink_msg_param_request_read_pack(1, 1, &msg, 1, 1, "SERIAL1_BAUD", -1);
    msg_len = mavlink_msg_to_send_buffer((uint8_t*)buf,&msg);

    if(write(serial_fd, buf, msg_len) != msg_len)
    {
        cerr << "Serial port write error." << endl;
        disconnectUSB();
        exit(1);
    }

    for(tries=0; tries<3; ++tries)
    {
        cout << "Requesting SERIAL1_BAUD..." << endl;

        if(wait_for_message(MAVLINK_MSG_ID_PARAM_VALUE, &msg, 3) >= 0)
        {
            baud = mavlink_msg_param_value_get_param_value(&msg);
            cout << "Got param value " << baud << endl;
            disconnectUSB();
            exit(0);
        }
    }

    if(!gotParam)
    {
        cout << "Unable to get SERIAL1_BAUD_VALUE" << endl;
        disconnectUSB();
        exit(1);
    }
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
    mavlink_message_t msg;

    //Cout cleanup
    std::cout.precision(2);
    std::cout.setf( ios::fixed, ios::floatfield );

    cout << "Pixhawk baudrate checker" << endl;
    
    //Serial port setup
    serialPortName = "/dev/ttymxc1";
    baudrate=115200;//57600;
    if(!serial_setup(baudrate))
    {
        cerr << "Unable to initialize the serial send" << endl;
        return -1;
    }

    //Threading initialization
    pthread_mutex_init(&mutex_msg, NULL);
    sem_init(&sem_msg, 0, 0);
    
    //Start the mavlink rx thread
    pthread_create(&mavlink_ctx, NULL, mavlink_task, NULL);

    cout << "Waiting for a hearbeat..." << endl;
    
    //Wait for a heartbeat on the telem port
    if(wait_for_message(MAVLINK_MSG_ID_HEARTBEAT, &msg, 5) < 0)
    {
        cout << "No heartbeat received, requesting baudrate from USB" << endl;
        pthread_cancel(mavlink_ctx);
        close(serial_fd);
        if (open_USB_serial() < 0)
            return -1;
    }
    else
    {
        cout << "Got a heartbeat, exiting" << endl;
        return 0;
    }
    
    pthread_create(&mavlink_ctx, NULL, mavlink_task, NULL);

    //Send a param request to the pixhawk
    request_baudrate();

    //Wait for the mavlink thread to end
    pthread_join(mavlink_ctx, NULL);

    return 0;
}
