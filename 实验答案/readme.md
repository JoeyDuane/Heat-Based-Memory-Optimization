# 一、文件说明

- linux-5.15.114-huawei.zip
  - 内核源码，其中也包含了一些脚本
- hybrid_memory_scripts.zip
  - 运行脚本
- ours.patch：
  - 为了便于查看代码修改情况，导出了patch
- gups-hemem.zip
  - gups工作负载的代码（其他工作负载的代码均未进行修改，使用的是官方代码）

# 二、运行步骤（真机）



## 2.1 准备工作

### 2.1.1 编译启动程序

```shell
$ cd hybrid_memory_scripts
$ bash compile_launch_program.sh
```

### 2.1.2 修改环境变量

需要修改的环境变量如下：

1. env.sh脚本（`linux-5.15.114-huawei/env.sh`）

   - scripts_root_path变量
   - 以及各个benchmark路径变量（其中，spec accel需要单独在gen_cmd.py设置）.

2. gen_cmd.py脚本（`hybrid_memory_scripts/gen_cmd/gen_cmd.py`）

   - script_root_path变量，

   - 以及与spec accel相关的accel2023_path和oneapi_path_script_path变量。

3. test_redis_db.sh（`hybrid_memory_scripts/gen_cmd/bench_cmd/test_redis_db.sh`）

   - 修改redis-benchmark的路径，即test_redis_db.sh中的RedisRoot变量

4. [可选] 如果要用qemu，需要修改qemu.sh中的镜像路径。

5. [可选] 如果需要修改默认的syscall参数，可以直接在运行工作负载脚本中进行修改。

6. [可选] 如果要修改输出文件的目录，可以修改gen_cmd.py的参数。



## 2.2 内核安装

```shell
# 解压后进入linux内核目录
cd linux-5.15.114-huawei

# 使用参考配置文件
cp .config.test .config

# 编译并安装内核
bash install.sh

# 使用kexec切换到新内核（同时限制了启动后的dram size）
bash run_kernel.sh
```

> 如果想要在qemu中测试内核，可以在内核安装成功后运行如下命令
>
> ```shell
> bash qemu.sh
> ```

> 如果要提前关闭内存热度检测线程，运行
> ```
> bash kill_kunmap.sh
> ```

## 2.3 运行benchmark

```
# 运行benchmark
bash test-graph500.sh
bash test-redis.sh
bash test-gups.sh

bash test-accel.sh # 注意accel由于工作集大小比较小，需要单独设置pm的size
```



# 附：输出文件说明

输出文件默认位于./out目录下，参考：
```shell
$ ls ./out/default_debug_kernel_20-pebs-default-20240621-19h19m25s
caller_script.sh   my_stat-end.log         node2_vmstat_begin.txt  numa_maps.log     vmstat_diff.log
dmesg-backup.log   node0_vmstat_begin.txt  node2_vmstat_end.txt    run.log           vmstat-end.log
dmesg-begin.log    node0_vmstat_end.txt    node3_vmstat_begin.txt  script.sh
dmesg-end.log      node1_vmstat_begin.txt  node3_vmstat_end.txt    sysctl.log
my_stat-begin.log  node1_vmstat_end.txt    numactl.log             vmstat-begin.log
```
其中，
- run.log为benchmark的运行日志
- vmstat_diff.log为vmstat对比文件
- dmesg*.log为程序运行前/运行后的内核日志文件
- numa_maps.log为每隔5分钟，打印一下工作负载的numa_maps统计文件