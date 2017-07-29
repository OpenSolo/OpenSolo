#ifndef SOLO_MESSAGE_H
#define SOLO_MESSAGE_H

#include <stdint.h>
#include <iostream>

// Messages to/from App or ShotMgr

namespace SoloMessage
{

struct Hdr {
    uint32_t type;
    uint32_t length; // bytes following this header

    // type field:
    // MUST MATCH: SoloLink/app/shots/app_packet.py
    // MUST MATCH: iSolo/networking/SoloPacket.swift
    static const uint32_t GET_CURRENT_SHOT = 0;
    static const uint32_t SET_CURRENT_SHOT = 1;
    static const uint32_t LOCATION = 2;
    static const uint32_t RECORD_POSITION = 3;
    static const uint32_t CABLE_CAM_OPTIONS = 4;
    // MUST MATCH: SoloLink/flightcode/stm32/btn_msg.py
    static const uint32_t BUTTON_EVENT = 2000;
    static const uint32_t SET_BUTTON_STRING = 2001;
    static const uint32_t SET_SHOT_STRING = 2002;
};

struct SetButtonString : public Hdr {
    uint8_t button_id;
    uint8_t button_event;
    uint8_t shot_id;
    uint8_t state;
    char descriptor[0];
};

struct SetShotString : public Hdr {
    char descriptor[0];
};

struct Tester {
    Tester(void);
};

}; // namespace SoloMessage

std::ostream &operator<<(std::ostream &os, const struct SoloMessage::Hdr &msg);

std::ostream &operator<<(std::ostream &os, const struct SoloMessage::SetButtonString &msg);

std::ostream &operator<<(std::ostream &os, const struct SoloMessage::SetShotString &msg);

#endif // SOLO_MESSAGE_H
