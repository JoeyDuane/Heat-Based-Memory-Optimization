#ifndef _GUPS_SYSCALL_H_
#define _GUPS_SYSCALL_H_

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <err.h>
#include <sys/wait.h>
#include <stdint.h>

void init_area(int nr_thread);
void add_area(uint64_t start_address, uint64_t end_address);
void add_hotset(uint64_t start_address, uint64_t end_address);
void send_to_kernel(void);
void destory_kernel_area(void);

#endif