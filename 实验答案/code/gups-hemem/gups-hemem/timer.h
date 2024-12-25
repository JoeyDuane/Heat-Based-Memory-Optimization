#ifndef __TIMER_H__
#define __TIMER_H__

#define tv_to_double(t) (t.tv_sec + (t.tv_usec / 1000000.0))

double elapsed(struct timeval *starttime, struct timeval *endtime);

#endif