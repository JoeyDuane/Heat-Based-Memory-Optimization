/*
 * =====================================================================================
 *
 *       Filename:  gups.c
 *
 *    Description:
 *
 *        Version:  1.0
 *        Created:  02/21/2018 02:36:27 PM
 *       Revision:  none
 *       Compiler:  gcc
 *
 *         Author:  YOUR NAME (),
 *   Organization:
 *
 * =====================================================================================
 */

#define _GNU_SOURCE

#include <stdlib.h>
#include <stdio.h>
#include <assert.h>
#include <unistd.h>
#include <sys/time.h>
#include <fcntl.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <math.h>
#include <string.h>
#include <pthread.h>
#include <sys/mman.h>
#include <errno.h>
#include <stdint.h>
#include <stdbool.h>

#include "timer.h"
#include "gups.h"
#include "gups-syscall.h"

#define MAX_THREADS     64

#define GUPS_PAGE_SIZE      (4 * 1024)

int threads;

struct gups_args {
  int tid;                      // thread id
  uint8_t* field;                  // pointer to start of thread's region
  uint64_t iters;          // iterations to perform
  uint64_t size;           // size of region
  uint64_t elt_size;       // size of elements
  uint64_t hot_start;            // start of hot set
  uint64_t hotsize;        // size of hot set
};

static unsigned long updates, nelems;

static uint64_t lfsr_fast(uint64_t lfsr)
{
  lfsr ^= lfsr >> 7;
  lfsr ^= lfsr << 9;
  lfsr ^= lfsr >> 13;
  return lfsr;
}

FILE *hotsetfile = NULL;

bool hotset_only = false;

static void *prefill_hotset(void* arguments)
{
  struct gups_args *args = (struct gups_args*)arguments;
  uint8_t *field = (uint8_t*)(args->field);
  uint64_t i;
  uint64_t index1;
  uint64_t elt_size = args->elt_size;
  char data[elt_size];

  index1 = 0;

  for (i = 0; i < args->hotsize; i++) {
    index1 = i;
    if (elt_size == 8) {
      uint64_t *tmp = (uint64_t*)field;
      tmp[index1] += i;
    }
    else {
      memcpy(data, &field[index1 * elt_size], elt_size);
      memset(data, data[0] + (char)i, elt_size);
      memcpy(&field[index1 * elt_size], data, elt_size);
    }
  }
  return 0;
  
}

static void *do_gups(void *arguments)
{
  //printf("do_gups entered\n");
  struct gups_args *args = (struct gups_args*)arguments;
  uint8_t *field = (uint8_t*)(args->field);
  uint64_t i;
  uint64_t index;
  uint64_t elt_size = args->elt_size;
  char data[elt_size];
  uint64_t lfsr;
  uint64_t hot_num;
  // uint64_t start, end;

  srand(args->tid);
  lfsr = rand();

  index = 0;

  fprintf(hotsetfile, "Thread %d region: %p - %p\thot set: %p - %p\n", args->tid, 
                  field, field + (args->size * elt_size),
                  field + args->hot_start, field + args->hot_start + (args->hotsize * elt_size));   

  for (i = 0; i < args->iters; i++) {
    hot_num = lfsr_fast(lfsr) % 100;
    if (hot_num < 90) { // 90% 请求落在热集合中
      lfsr = lfsr_fast(lfsr);
      index = args->hot_start + (lfsr % args->hotsize);
    } else { // 10% 请求落在全部集合中（包括热集合以及非热集合）
      lfsr = lfsr_fast(lfsr);
      index = lfsr % (args->size);
    }

    if (elt_size == 8) {
      uint64_t *tmp = (uint64_t*)field;
      tmp[index] += i;
    }
    else {
      memcpy(data, &field[index * elt_size], elt_size);
      memset(data, data[0] + i, elt_size);
      memcpy(&field[index * elt_size], data, elt_size);
    }
  }
  return 0;
}

int main(int argc, char **argv)
{
  uint64_t expt;
  uint64_t size, elt_size;
  uint64_t tot_hot_size;
  uint64_t log_hot_size;
  struct timeval starttime, stoptime;
  double secs, gups;
  int i;
  void *p;
  struct gups_args** ga;
  pthread_t t[MAX_THREADS];

  if (argc != 6) {
    fprintf(stderr, "Usage: %s [threads] [updates per thread] [date size exponent] [element size (bytes)] [hot size exponent]\n", argv[0]);
    fprintf(stderr, "  threads\t\t\tnumber of threads to launch\n");
    fprintf(stderr, "  updates per thread\t\tnumber of updates per thread\n");
    fprintf(stderr, "  exponent\t\t\tlog size of region\n");
    fprintf(stderr, "  data size\t\t\tsize of data in array (in bytes)\n");
    fprintf(stderr, "  hot size\t\t\tlog size of hot set (size exponent)\n");
    return 0;
  }

  gettimeofday(&starttime, NULL);

  threads = atoi(argv[1]);
  assert(threads <= MAX_THREADS);
  ga = (struct gups_args**)malloc(threads * sizeof(struct gups_args*));

  updates = atol(argv[2]);
  updates -= updates % 256;
  expt = atoi(argv[3]);
  assert(expt > 8);
  assert(updates > 0 && (updates % 256 == 0));
  size = (unsigned long)(1) << expt;
  size -= (size % 256);
  assert(size > 0 && (size % 256 == 0));
  elt_size = atoi(argv[4]);
  log_hot_size = atof(argv[5]);
  tot_hot_size = (unsigned long)(1) << log_hot_size;

  fprintf(stderr, "%lu updates per thread (%d threads)\n", updates, threads);
  fprintf(stderr, "field of 2^%lu (%lu) bytes\n", expt, size);
  fprintf(stderr, "%ld byte element size (%ld elements total)\n", elt_size, size / elt_size);

  // lmy
  init_area(threads);

  assert(tot_hot_size < size);
  // p = mmap(NULL, size, PROT_READ | PROT_WRITE, MAP_SHARED | MAP_ANONYMOUS | MAP_HUGETLB | MAP_POPULATE, -1, 0);
  p = mmap(NULL, size, PROT_READ | PROT_WRITE, MAP_SHARED | MAP_ANONYMOUS | MAP_POPULATE, -1, 0);
  if (p == MAP_FAILED) {
    perror("mmap");
    assert(0);
  }

  gettimeofday(&stoptime, NULL);
  fprintf(stderr, "Init took %.4f seconds\n", elapsed(&starttime, &stoptime));
  fprintf(stderr, "Region address: %p - %p\t size: %ld\n", p, (p + size), size);
  
  nelems = (size / threads) / elt_size; // number of elements per thread
  fprintf(stderr, "Elements per thread: %lu\n", nelems);

  hotsetfile = fopen("hotsets.txt", "w");
  if (hotsetfile == NULL) {
    perror("fopen");
    assert(0);
  }

  gettimeofday(&stoptime, NULL);
  secs = elapsed(&starttime, &stoptime);
  fprintf(stderr, "Initialization time: %.4f seconds.\n", secs);

  // 一个线程的 hotsize，单位：元素个数
  unsigned long hotsize = (tot_hot_size / threads) / elt_size;
  printf("hot_start: %p\thot_end: %p\thot_size: %lu\n", p, p + (hotsize * elt_size), hotsize);

  gettimeofday(&starttime, NULL);
  for (i = 0; i < threads; i++) {
    //printf("starting thread [%d]\n", i);
    ga[i] = (struct gups_args*)malloc(sizeof(struct gups_args));
    ga[i]->tid = i;
    ga[i]->field = p + (i * nelems * elt_size);
    ga[i]->iters = updates;
    ga[i]->size = nelems;
    ga[i]->elt_size = elt_size;
    ga[i]->hot_start = 0;        // hot set at start of thread's region
    ga[i]->hotsize = hotsize;
    
    void* next_addr = p + ((i + 1) * nelems * elt_size);
    add_area((uint64_t)ga[i]->field, (uint64_t)next_addr);

    void* next_hot_addr = ga[i]->field + (ga[i]->hot_start + hotsize * elt_size);
    add_hotset((uint64_t)ga[i]->field, (uint64_t)next_hot_addr);
  }
  send_to_kernel();

  if (hotset_only) {
    for (i = 0; i < threads; i++) {
      int r = pthread_create(&t[i], NULL, prefill_hotset, (void*)ga[i]);
      assert(r == 0);
    }
    // wait for worker threads
    for (i = 0; i < threads; i++) {
      int r = pthread_join(t[i], NULL);
      assert(r == 0);
    }
  }

  // run through gups once to touch all memory
  // spawn gups worker threads
  for (i = 0; i < threads; i++) {
    int r = pthread_create(&t[i], NULL, do_gups, (void*)ga[i]);
    assert(r == 0);
  }

  // wait for worker threads
  for (i = 0; i < threads; i++) {
    int r = pthread_join(t[i], NULL);
    assert(r == 0);
  }
  //hemem_print_stats();

  gettimeofday(&stoptime, NULL);

  secs = elapsed(&starttime, &stoptime);
  printf("Elapsed time: %.4f seconds.\n", secs);
  gups = threads * ((double)updates) / (secs * 1.0e9);
  printf("GUPS = %.10f\n", gups);

  fprintf(stderr, "Timing.\n");
  gettimeofday(&starttime, NULL);

  // spawn gups worker threads
  for (i = 0; i < threads; i++) {
    int r = pthread_create(&t[i], NULL, do_gups, (void*)ga[i]);
    assert(r == 0);
  }

  // wait for worker threads
  for (i = 0; i < threads; i++) {
    int r = pthread_join(t[i], NULL);
    assert(r == 0);
  }
  gettimeofday(&stoptime, NULL);

  secs = elapsed(&starttime, &stoptime);
  printf("Elapsed time: %.4f seconds.\n", secs);
  gups = threads * ((double)updates) / (secs * 1.0e9);
  printf("GUPS = %.10f\n", gups);

  // FILE* pebsfile = fopen("pebs.txt", "w+");
  // assert(pebsfile != NULL);
  // for (uint64_t addr = (uint64_t)p; addr < (uint64_t)p + size; addr += (2*1024*1024)) {
  //   struct hemem_page *pg = get_hemem_page(addr);
  //   assert(pg != NULL);
  //   if (pg != NULL) {
  //     fprintf(pebsfile, "0x%lx:\t%lu\t%lu\t%lu\n", pg->va, pg->tot_accesses[DRAMREAD], pg->tot_accesses[NVMREAD], pg->tot_accesses[WRITE]);
  //   }
  // }

  for (i = 0; i < threads; i++) {
    free(ga[i]);
  }
  destory_kernel_area();
  free(ga);
  fclose(hotsetfile);
  munmap(p, size);

  return 0;
}


