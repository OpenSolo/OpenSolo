#include "ui_events.h"

namespace Event {

bool isAlert(ID id) {
    return (id >= AlertBegin && id < AlertEnd);
}

bool isValid(unsigned id) {
    return ((id < NonAlertEnd) || (id >= AlertBegin && id < AlertEnd));
}

}
