#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <err.h>
#include <sys/wait.h>

int syscall_benchamrk_start = 449;
int syscall_benchmark_end = 450;

long benchamrk_start(pid_t pid, int node)
{
    return syscall(syscall_benchamrk_start, pid, node);
}

long benchmark_end(pid_t pid)
{
    return syscall(syscall_benchmark_end, pid);
}

int main(int argc, char** argv)
{
    pid_t pid;
    int state;

    benchmark_end(-1);
    printf("benchmark_end\n");
    return 0;
}