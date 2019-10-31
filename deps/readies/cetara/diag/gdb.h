
#pragma once

#include <stdbool.h>

extern bool __via_gdb;

#ifdef __arm__
#define BB do { if (__via_gdb) { __asm__("trap"); } } while(0)
#else
#define BB do { if (__via_gdb) { __asm__("int $3"); } } while(0)
#endif