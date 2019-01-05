#ifndef CIRCULAR_BUFFER_H
#define CIRCULAR_BUFFER_H

#include <stdio.h>
#include <stdint.h>
#include <iostream>
#include <new>

// head == tail: empty
// (head - tail) == 1: one byte in buffer
// (head - tail) == (num_bytes - 1): num_bytes - 1 in buffer (full)

class CircularBuffer
{

public:
    // Constructor: allocate buffer and initialize state
    CircularBuffer(unsigned num_bytes) : _buf(NULL), _head(0), _tail(0), _buf_size(0)
    {
        _buf = new (std::nothrow) char[num_bytes];
        if (_buf != NULL)
            _buf_size = num_bytes;
    }

    // Destructor: free buffer
    ~CircularBuffer()
    {
        if (_buf != NULL)
            delete _buf;
        _buf = NULL;
        _head = _tail = 0;
        _buf_size = 0;
    }

    bool invariant(void)
    {
        return (_buf != NULL) && (_buf_size > 0) && (_head < _buf_size) && (_tail < _buf_size);
    }

    // Return size
    unsigned size(void) const
    {
        return _buf_size;
    }

    // Return number of bytes used in buffer.
    unsigned used(void) const
    {
        if (_head >= _tail)
            return _head - _tail;
        else
            return _head + _buf_size - _tail;
    }

    // Return number of free bytes in buffer.
    unsigned free(void) const
    {
        return _buf_size - used() - 1;
    }

    // Put data in buffer.
    // Return true on success, false on error.
    bool put(const void *p, unsigned num_bytes)
    {
        // std::cout << "CircularBuffer::put(" << p << ", " << num_bytes
        //          << ")" << std::endl;
        if (num_bytes > free())
            return false;
        const char *d = (const char *)p;
        while (num_bytes-- > 0) {
            _buf[_head++] = *d++;
            if (_head >= _buf_size)
                _head = 0;
        }
        return true;
    }

    // Put structure in buffer.
    // Return true on success, false on error.
    template < class type >
    bool put(const type p)
    {
        return put(&p, sizeof(type));
    }

    // Get data from buffer.
    // Return true on success, false on error.
    bool get(void *p, unsigned num_bytes)
    {
        if (used() < num_bytes)
            return false;
        char *d = (char *)p;
        while (num_bytes-- > 0) {
            *d++ = _buf[_tail++];
            if (_tail >= _buf_size)
                _tail = 0;
        }
        return true;
    }

    // Get structure from buffer.
    // Return true on success, false on error.
    template < class type >
    bool get(type *p)
    {
        return get(p, sizeof(type));
    }

    // Discard data from buffer.
    // Return true on success, false on error.
    bool discard(unsigned num_bytes)
    {
        if (used() < num_bytes)
            return false;
        while (num_bytes-- > 0) {
            if (++_tail >= _buf_size)
                _tail = 0;
        }
        return true;
    }

private:
    char *_buf;
    unsigned _head;
    unsigned _tail;
    unsigned _buf_size;
};

std::ostream &operator<<(std::ostream &os, const CircularBuffer &c);

#endif // CIRCULAR_BUFFER_H
