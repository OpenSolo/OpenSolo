
#include <syslog.h>
#include <errno.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <iostream>
#include "ButtonEventMessage.h"
#include "RcLock.h"

// This program is expected to run once at startup. Its job is to notice RC
// is currently locked, and if so, wait for the magic button combo and unlock
// RC if it the magic combo ever seen.
//
// Magic combo is a long-press on A, B, Fly, and Home.
//
// Processing:
// 1. If RC is already unlocked, exit.
// 2. Otherwise, connect to the button event server in the controller and
//    start waiting for button events.
// 3. For each message, save the most recent event for each button.
// 4. When the message says the magic combo buttons are down, and the most
//    recent event for each of those buttons is "long press", unlock RC and
//    exit.

// IP:port of button event server
static const char *server_ip = "10.1.1.1";
static const int server_port = 5016;

// button mask for the magic combo, to be matched against 'allButtons' in
// button event message
static const uint16_t magic_buttons =
    (1 << ButtonEventMessage::ButtonFly) | (1 << ButtonEventMessage::ButtonRTL) |
    (1 << ButtonEventMessage::ButtonA) | (1 << ButtonEventMessage::ButtonB);

int main(int argc, char *argv[])
{
    int s;
    struct sockaddr_in sa;
    ButtonEventMessage msg;
    // save most recent event for each button
    int btn_event[ButtonEventMessage::ButtonMax];

    openlog("unlock", LOG_NDELAY, LOG_LOCAL1);

    syslog(LOG_INFO, "built " __DATE__ " " __TIME__);

    if (!RcLock::locked()) {
        syslog(LOG_INFO, "rc is not locked");
        return 1;
    }

    s = socket(AF_INET, SOCK_STREAM, 0);
    if (s < 0) {
        syslog(LOG_ERR, "socket: %s", strerror(errno));
        return 1;
    }

    memset(&sa, 0, sizeof(sa));
    sa.sin_family = AF_INET;
    sa.sin_port = htons(server_port);
    sa.sin_addr.s_addr = inet_addr(server_ip);
    syslog(LOG_INFO, "connecting to %s:%d", server_ip, server_port);
    while (1) {
        if (connect(s, (struct sockaddr *)&sa, sizeof(sa)) == 0)
            break;
        sleep(1);
    }

    // okay to init to 0 ("Press") since we are looking for LongHold
    memset(&btn_event, 0, sizeof(btn_event));

    // The following assumes button messages are not split across recv calls.
    // They can in theory be split across recv calls, but it would probably
    // have to be forced somehow.
    syslog(LOG_INFO, "waiting for unlock");
    while (1) {
        if (recv(s, &msg, sizeof(msg), 0) == sizeof(msg)) {
            // std::cout << msg << std::endl;

            // accumulate most recent event for each button
            btn_event[msg.id] = msg.event;

            // magic combo is all down, and they are all long-press
            if (msg.allButtons == magic_buttons &&
                btn_event[ButtonEventMessage::ButtonFly] == ButtonEventMessage::LongHold &&
                btn_event[ButtonEventMessage::ButtonRTL] == ButtonEventMessage::LongHold &&
                btn_event[ButtonEventMessage::ButtonA] == ButtonEventMessage::LongHold &&
                btn_event[ButtonEventMessage::ButtonB] == ButtonEventMessage::LongHold) {
                syslog(LOG_INFO, "unlocked");
                RcLock::unlock_override();
                shutdown(s, SHUT_RDWR);
                close(s);
                return 0;
            }
        } else {
            sleep(1);
        }
    }

} // main
