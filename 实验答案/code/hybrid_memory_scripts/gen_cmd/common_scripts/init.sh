#!/bin/bash

# 设置两个pm容量为xG

# 依赖
# sudo apt install jq

# usage:
# bash init.sh xG

# 获取命令行参数
input="$1"

pm_config_size=""
get_pm_config_size()
{
    # 将输入参数中的小写字母 "g" 转换为大写字母 "G"
    input_uppercase="${input//g/G}"

    # 使用正则表达式从输入参数中提取整数部分
    if [[ $input_uppercase =~ ([0-9]+)G ]]; then
        pm_config_size="${BASH_REMATCH[1]}"
    else
        echo "无效的输入参数: $input (please input xg/xG)"
        exit
    fi

    # 实验中，实际PM大小要多加2G，可能需要用来存元数据
    pm_config_size=$((pm_config_size + 2))
}

pmem_devices=""
get_pm_region_id() {
    # 执行ndctl命令，并将输出保存到变量中
    ndctl_output=$(sudo ndctl list -Rvu)
    
    # 使用jq解析JSON数据，提取pmem设备的region id
    pmem_devices=$(echo "$ndctl_output" | jq -r '.[] | select(.persistence_domain == "memory_controller") | .dev')
    echo $pmem_devices

    # 循环遍历每个pmem设备，提取并输出region id
    for dev in $pmem_devices; do
        region_id=$(echo "$dev" | sed 's/region//')
        echo "Device: $dev, Region ID: $region_id"
    done
}

# numactl -H
node_cnt=$(numactl -H | grep available: |  awk '{print $2}')
if [[ "$node_cnt" -eq 4 ]]; then
    echo "there alreay are 4 numa nodes, exit"
    exit
fi

sudo ndctl disable-namespace all
sudo ndctl destroy-namespace all
get_pm_region_id

echo offline | sudo tee /sys/devices/system/memory/auto_online_blocks

get_pm_config_size
for dev in $pmem_devices; do
    region_id=$(echo "$dev" | sed 's/region//')
    dev_name="$region_id.0"
    # sudo ndctl create-namespace --mode=devdax --size=4G --region=$region_id # 2G
    # sudo ndctl create-namespace --mode=devdax --size=6G --region=$region_id # 4G
    # sudo ndctl create-namespace --mode=devdax --size=8G --region=$region_id # 6G
    # sudo ndctl create-namespace --mode=devdax --size=10G --region=$region_id # 8G
    sudo ndctl create-namespace --mode=devdax --size="$pm_config_size"G --region=$region_id # xG
    
    sudo daxctl reconfigure-device --mode=system-ram $dev_name -u
done

numactl -H
