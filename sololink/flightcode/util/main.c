#include <stdint.h>
#include <stdio.h>
#include "util_test.h"
#include "syslog_test.h"

int main(int argc, char *argv[])
{

    fprintf(stderr, "util_test...");
    if (util_test() == 0)
        fprintf(stderr, "pass\n");
    else
        fprintf(stderr, "FAIL\n");

    fprintf(stderr, "syslog_test...");
    if (syslog_test() == 0)
        fprintf(stderr, "pass\n");
    else
        fprintf(stderr, "FAIL\n");

    return 0;

} // main
