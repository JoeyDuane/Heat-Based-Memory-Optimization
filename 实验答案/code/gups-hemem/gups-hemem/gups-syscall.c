#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <err.h>
#include <sys/wait.h>
#include <stdint.h>

#include "gups-syscall.h"

int syscall_hotset_init = 451;
int syscall_hotset_exit = 452;

struct area {
    uint64_t start_addr;
    uint64_t end_addr;
};

int gups_area_index = 0;
int hot_area_index = 0;

struct area *gups_areas;
size_t len_gups_areas = 0;
struct area *hot_areas;
size_t len_hot_area = 0;

long hotset_init(struct area *_gups_areas, size_t _len_gups_areas,
                 struct area *_hot_areas,  size_t _len_hot_area)
{
    return syscall(syscall_hotset_init, getpid(), _gups_areas, _len_gups_areas,
                                        _hot_areas,  _len_hot_area);
}

long hotset_exit()
{
    return syscall(syscall_hotset_exit);
}

void init_area(int nr_thread)
{
    len_gups_areas = nr_thread;
    len_hot_area   = nr_thread;
    gups_areas = (struct area*)malloc(nr_thread * sizeof(struct area));
    hot_areas  = (struct area*)malloc(nr_thread * sizeof(struct area));
}

void add_area(uint64_t start_address, uint64_t end_address)
{
    gups_areas[gups_area_index].start_addr = start_address;
    gups_areas[gups_area_index].end_addr   = end_address;
    gups_area_index ++;
}

void add_hotset(uint64_t start_address, uint64_t end_address)
{
    hot_areas[hot_area_index].start_addr = start_address;
    hot_areas[hot_area_index].end_addr   = end_address;
    hot_area_index ++;
}

void send_to_kernel(void)
{
    hotset_init(gups_areas, len_gups_areas, hot_areas, len_hot_area);
    
    len_gups_areas = 0;
    len_hot_area   = 0;
    free(gups_areas);
    free(hot_areas);
}

void destory_kernel_area(void)
{
    hotset_exit();
}
