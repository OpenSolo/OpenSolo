
#include <iostream>
#include "CircularBuffer.h"

using namespace std;

int main(int argc, char *argv[])
{
    static const unsigned size = 16;
    CircularBuffer cb(size);
    bool b[10];
    uint32_t u32[10];
    uint64_t u64[10];
    char c[10];

    cout << cb << endl;

    cout << "put uint32_t...";
    u32[0] = 0x12345678;
    b[0] = cb.put(u32[0]);
    if (b[0] && cb.used() == 4 && cb.free() == cb.size() - 4 - 1)
        cout << "OK" << endl;
    else
        cout << "ERROR" << endl;

    cout << cb << endl;

    cout << "get uint32_t...";
    cb.get(&u32[1]);
    if (b[0] && u32[1] == u32[0] && cb.used() == 0 && cb.free() == cb.size() - 1)
        cout << "OK" << endl;
    else
        cout << "ERROR" << endl;

    cout << cb << endl;

    cout << "put 3x uint32_t...";
    u32[0] = 0x11223344;
    u32[1] = 0x55667788;
    u32[2] = 0x99aabbcc;
    b[0] = cb.put(u32[0]);
    b[1] = cb.put(u32[1]);
    b[2] = cb.put(u32[2]);
    if (b[0] && b[1] && b[2] && cb.used() == 12 && cb.free() == cb.size() - 12 - 1)
        cout << "OK" << endl;
    else
        cout << "ERROR" << endl;

    cout << cb << endl;

    cout << "put uint32_t (fail)...";
    u32[3] = 0xdeadbeef;
    b[3] = cb.put(u32[3]);
    if (!b[3] && cb.used() == 12 && cb.free() == cb.size() - 12 - 1)
        cout << "OK" << endl;
    else
        cout << "ERROR" << endl;

    cout << cb << endl;

    cout << "put 3x char...";
    c[0] = 'a';
    c[1] = 'b';
    c[2] = 'c';
    b[0] = cb.put(c[0]);
    b[1] = cb.put(c[1]);
    b[2] = cb.put(c[2]);
    if (b[0] && b[1] && b[2] && cb.used() == 15 && cb.free() == cb.size() - 15 - 1)
        cout << "OK" << endl;
    else
        cout << "ERROR" << endl;

    cout << cb << endl;

    cout << "put char (fail)...";
    c[3] = 'x';
    b[3] = cb.put(c[3]);
    if (!b[3] && cb.used() == 15 && cb.free() == cb.size() - 15 - 1)
        cout << "OK" << endl;
    else
        cout << "ERROR" << endl;

    cout << cb << endl;

    cout << "get 3x uint32_t...";
    u32[0] = 0;
    u32[1] = 0;
    u32[2] = 0;
    b[0] = cb.get(&u32[0]);
    b[1] = cb.get(&u32[1]);
    b[2] = cb.get(&u32[2]);
    if (b[0] && b[1] && b[2] && u32[0] == 0x11223344 && u32[1] == 0x55667788 &&
        u32[2] == 0x99aabbcc && cb.used() == 3 && cb.free() == cb.size() - 3 - 1)
        cout << "OK" << endl;
    else
        cout << "ERROR" << endl;

    cout << cb << endl;

    cout << "get 3x char...";
    c[0] = 0;
    c[1] = 0;
    c[2] = 0;
    b[0] = cb.get(&c[0]);
    b[1] = cb.get(&c[1]);
    b[2] = cb.get(&c[2]);
    if (b[0] && b[1] && b[2] && c[0] == 'a' && c[1] == 'b' && c[2] == 'c' && cb.used() == 0 &&
        cb.free() == cb.size() - 1)
        cout << "OK" << endl;
    else
        cout << "ERROR" << endl;

    cout << cb << endl;

    cout << "put char...";
    c[0] = 'z';
    b[0] = cb.put(c[0]);
    if (b[0] && cb.used() == 1 && cb.free() == cb.size() - 1 - 1)
        cout << "OK" << endl;
    else
        cout << "ERROR" << endl;

    cout << cb << endl;

    cout << "put uint64_t...";
    u64[0] = 0x123456789abcdef0ULL;
    b[0] = cb.put(u64[0]);
    if (b[0] && cb.used() == 9 && cb.free() == cb.size() - 9 - 1)
        cout << "OK" << endl;
    else
        cout << "ERROR" << endl;

    cout << cb << endl;

    cout << "get char...";
    c[0] = 0;
    b[0] = cb.get(&c[0]);
    if (b[0] && c[0] == 'z' && cb.used() == 8 && cb.free() == cb.size() - 8 - 1)
        cout << "OK" << endl;
    else
        cout << "ERROR" << endl;

    cout << cb << endl;

    cout << "get uint64_t...";
    u64[0] = 0;
    b[0] = cb.get(&u64[0]);
    if (b[0] && u64[0] == 0x123456789abcdef0ULL && cb.used() == 0 && cb.free() == cb.size() - 0 - 1)
        cout << "OK" << endl;
    else
        cout << "ERROR" << endl;

    cout << cb << endl;

    cout << "get char (fail)...";
    c[0] = 0;
    b[0] = cb.get(&c[0]);
    if (!b[0] && cb.used() == 0 && cb.free() == cb.size() - 0 - 1)
        cout << "OK" << endl;
    else
        cout << "ERROR" << endl;

    cout << cb << endl;

    return 0;

} // main
