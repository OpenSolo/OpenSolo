
#include <iostream>
#include <iomanip>
#include "SoloMessage.h"

using namespace std;

// instantiate one of these to see debug output at startup
// SoloMessage::Tester tester;

SoloMessage::Tester::Tester(void)
{
    cout << "SoloMessage::Hdr: " << sizeof(Hdr) << " bytes" << endl;
    cout << "SoloMessage::SetButtonString: " << sizeof(SetButtonString) << " bytes" << endl;
    cout << "SoloMessage::SetShotString: " << sizeof(SetShotString) << " bytes" << endl;
}

// Print SoloMessage::Hdr in a human-readable format
ostream &operator<<(ostream &os, const struct SoloMessage::Hdr &msg)
{
    os << "type=" << msg.type;
    os << " length=" << msg.length;
    const uint8_t *p = (const uint8_t *)&msg + sizeof(msg);
    os << setfill('0') << hex;
    for (unsigned i = 0; i < msg.length; i++)
        os << ' ' << setw(2) << int(p[i]);
    os << setfill(' ') << dec;
    return os;
}

// Print SoloMessage::SetButtonString in a human-readable format
ostream &operator<<(ostream &os, const struct SoloMessage::SetButtonString &msg)
{
    os << "type=" << msg.type;
    os << " length=" << msg.length;
    os << " button_id=" << msg.button_id;
    os << " button_event=" << msg.button_event;
    os << " shot_id=" << msg.shot_id;
    os << " state=" << msg.state;
    os << " descriptor=\"" << msg.descriptor << '\"'; // assume EOS-terminated
    return os;
}

// Print SoloMessage::SetShotString in a human-readable format
ostream &operator<<(ostream &os, const struct SoloMessage::SetShotString &msg)
{
    os << "type=" << msg.type;
    os << " length=" << msg.length;
    os << " descriptor=\"" << msg.descriptor << '\"'; // assume EOS-terminated
    return os;
}
