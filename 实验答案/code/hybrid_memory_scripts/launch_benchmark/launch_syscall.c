#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <err.h>
#include <sys/wait.h>
#include <time.h>

int syscall_benchamrk_start = 449;
int syscall_benchmark_end = 450;

long benchamrk_start(pid_t pid, int node)
{
    long ret = syscall(syscall_benchamrk_start, pid, node);
    if (ret)
        perror("Failed call page_pebs_start");

    return ret;
}

long benchmark_end(pid_t pid)
{
    long ret = syscall(syscall_benchmark_end, pid);
    if (ret)
        perror("Failed call page_pebs_start");

    return ret;
}

int main(int argc, char** argv)
{
    pid_t pid;
    int state;
    clock_t start_time, end_time, duration;

    if (argc < 2) {
        printf("Usage %s [BENCHMARK]\n", argv[0]);	
        benchmark_end(-1);
        return 0;
    }

    pid = fork();
    if (pid == 0) {
        execvp(argv[1], &argv[1]);
        perror("Fails to run bench");
        exit(-1);
    }

    start_time = clock();
    printf("pid: %d\n", pid);
    benchamrk_start(pid, 0);

    waitpid(pid, &state, 0);
    end_time = clock();

    // 计算时间
    // double execution_time = ((double)(end_time - start_time)) / CLOCKS_PER_SEC * 1000.0;
    // int hours = (int)(execution_time / 3600);
    // int minutes = (int)((execution_time - hours * 3600) / 60);
    // int seconds = (int)(execution_time - hours * 3600 - minutes * 60);
    // // 输出运行时间
    // printf("程序运行时间:%02d:%02d:%02d\n", hours, minutes, seconds);

    benchmark_end(-1);

    return 0;
}
