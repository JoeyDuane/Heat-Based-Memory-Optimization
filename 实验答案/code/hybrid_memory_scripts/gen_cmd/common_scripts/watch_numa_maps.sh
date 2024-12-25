#!/bin/bash

# 定时监测某个benchmark的numa_maps文件

# usage:
# bash get_numa_maps.sh "benchmark_name"

sleep 5

benchmark_path=$1

case "$benchmark_path" in
    *"graph500"*)
        echo "graph500"
        pid=$(pidof graph500_reference_bfs)
    ;;
    *"runaccel"*)
        echo "runaccel (default lbm)"
        pid=$(pidof lbm_base.none)
    ;;
    *"redis"*)
        echo "redis-server"
        pid=$(pidof redis-server)
    ;;
    *"gups"*)
        echo "gups-pebs"
        pid=$(pidof gups-pebs)
    ;;
    *)
    echo "unkown benchmark, exit"
    exit
    ;;
esac


parse_single_numa_maps()
{
    filename=$1
    awk '{
        for (i = 1; i <= NF; i++) {
            if ($i ~ /^N[0-3]=/) {
                split($i, arr, "=") # e.g. arr = ['N1', '1000']
                num = substr(arr[1], 2)  # 提取N后的数字
                sums[num] += arr[2]      # 将N0到N3的值加到对应的变量中
            }
        }
    }
    END {
        for (i = 0; i <= 3; i++) {
            values[i] = sums[i]
        }
        for (i = 0; i <= 3; i++) {
            printf "N%d:%d ", i, values[i]
        }
        printf "\n"
    }' $filename
}

i=0
echo "pid=$pid"
echo "command: $(cat /proc/$pid/comm)"
while true; do
    # 检查指定PID的进程是否存在
    # kill -0 命令会发送一个空信号给指定的进程，如果进程存在，则不会执行任何操作，如果进程不存在，则会报错
    if ! sudo kill -0 "$pid" >/dev/null 2>&1; then
        echo "进程 $pid 不存在，停止脚本。"
        break
    fi

    # echo $i
    i=`expr $i + 1`
    sudo cat "/proc/$pid/numa_maps" | parse_single_numa_maps

    # 单位：s/秒
    sleep 300
done

# 检测到程序已经结束的话，可以发一封邮件通知
# python3 /home/dell/lmy/linux-lmy-b1/send_email.py "finish"
