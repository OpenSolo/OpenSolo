
#include <iostream>
#include "CircularBuffer.h"

// Print CircularBuffer status to a stream (debug)
std::ostream &operator<<(std::ostream &os, const CircularBuffer &c)
{
    os << "size=" << c.size() << " used=" << c.used() << " free=" << c.free();
    return os;
}
