#!/bin/bash

# usage:
# bash calc_vmstat_diff.sh  vmstat-start.log vmstat-end.log

# 使用 awk 计算两个vmstat文件中统计变量的差值并输出
calculate_difference() {
    local file1="$1"
    local file2="$2"

    # 使用 awk 处理文件，计算差值并输出
    awk '
        # 处理第一个文件，将数据存入数组 stats1
        NR == FNR {
            stats1[$1] = $2
            next
        }
        # 处理第二个文件，计算差值并输出
        ($1 in stats1) {
            difference = $2 - stats1[$1]
            printf "%s: %d\n", $1, difference
        }
    ' "$file1" "$file2"
}

file1=$1
file2=$2

# 调用函数计算差值
calculate_difference "$file1" "$file2"