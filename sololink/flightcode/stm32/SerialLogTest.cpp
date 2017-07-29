
#include <iostream>
#include <string.h>
#include "SerialLog.h"

using namespace std;

int main(int argc, char *argv[])
{
    static const unsigned log_size = 100;
    SerialLog sl(log_size);
    const char *s;
    bool b;
    static const unsigned num_pkts = 1000;
    unsigned n[num_pkts];
    unsigned pkt_num_oldest = 0;
    unsigned total = 0;
    unsigned pkt_num;
    const char *pkts[10] = {"",      "1",      "12",      "123",      "1234",
                            "12345", "123456", "1234567", "12345678", "123456789"};
    uint8_t f;
    const uint8_t flags[2] = {SerialLog::PKTFLG_UP, SerialLog::PKTFLG_DOWN};

    cout << sl << endl;

    for (pkt_num = 0; pkt_num < num_pkts; pkt_num++) {
        s = pkts[pkt_num % 10];
        f = flags[pkt_num % 2];
        cout << "log_packet \"" << s << "\"...";
        b = sl.log_packet(s, strlen(s), f);
        n[pkt_num] = sizeof(SerialLog::PacketEntry) + strlen(s);
        total += n[pkt_num];
        while (total >= log_size)
            total -= n[pkt_num_oldest++];
        if (b && sl.used() == total && sl.free() == sl.size() - total - 1)
            cout << "OK" << endl;
        else
            cout << "ERROR" << endl;
    }

    cout << sl << endl;

    return 0;

} // main
