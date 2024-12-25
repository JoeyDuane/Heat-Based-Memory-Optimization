# coding: utf-8

import os
import time
import argparse
import subprocess
import shutil
import shlex
import datetime
import humanize
import threading
import textwrap
from threading import Thread

# 需修改script_root_path
script_root_path = "/home/dell/lmy/hybrid_memory_scripts"
launch_script_path = f"{script_root_path}/launch_benchmark/launch_syscall"
vmstat_diff_path = f"{script_root_path}/gen_cmd/common_scripts/calc_vmstat_diff.sh"
watch_numamaps_script_path = f"{script_root_path}/gen_cmd/common_scripts/watch_numa_maps.sh"

# 需修改accel2023_path, oneapi_path_script_path
accel2023_path = "/home/dell/lmy/my_benchmarks/accel2023/"
oneapi_path_script_path = "/home/dell/intel/oneapi/setvars.sh"

def parse_arguments():
    parser = argparse.ArgumentParser(description='run')

    script_group = parser.add_argument_group('Script Group', 'script_group')
    script_group.add_argument('--out_script_path', dest='out_script_path',
                            default='test.sh',
                            help='default: "test.sh"')
    script_group.add_argument('--caller_script_path', dest='caller_script_path',
                            default="",
                            help='default: NULL')

    benchmark_group = parser.add_argument_group('Benchmark Group', 'benchmark_group')
    benchmark_group.add_argument('--benchmark_path', dest='benchmark_path',
                            default='/home/dell/lmy/graph500/src/graph500_reference_bfs',
                            help='default: "/home/dell/lmy/graph500/src/graph500_reference_bfs"')
    benchmark_group.add_argument('--benchmark_args', dest='benchmark_args',
                            default='',
                            help='default: "null"')
    benchmark_group.add_argument('--daemon_script_path', dest='daemon_script_path',
                            default='',
                            help='default: "null"')
    # 
    benchmark_group.add_argument('--cgroup_prefix', dest='cgroup_prefix',
                            default='cgexec -g cpu:mygroup',
                            help='default: "cgexec -g cpu:mygroup" (example: cgexec -g cpu:mygroup)')
    benchmark_group.add_argument('--numa_type', dest='numa_type',
                            choices=['default', 'interleave'],
                            default="default",
                            help='default, interleave')
    
    run_group = parser.add_argument_group('Run Group', 'run_group')
    run_group.add_argument('--method_type', dest='method_type',
                            help='可选参数: default, autonuma, memtis, autotiering, pebs, ours, custom')
    run_group.add_argument('--enable_markov', action='store_true', 
                            help='(deprecated) set page_predict.enable_markov = 1')
    run_group.add_argument('--set_spec_env', action='store_true', help='set spec acel env')

    out_group = parser.add_argument_group('Out group', 'out_group')
    out_group.add_argument('--out_root', dest='out_root',
                            default="./out",
                            help='default: ./out')
    out_group.add_argument('--out_dir_prefix', dest='out_dir_prefix',
                            default="",
                            help='default: empty str')
    out_group.add_argument('--out_dir_suffix', dest='out_dir_suffix',
                            default="",
                            help='default: empty str')
    out_group.add_argument('--add_out_dir_time_suffix', dest='add_out_dir_time_suffix',
                            action='store_true',
                            help='append time str to out_dir')
    out_group.add_argument('--out_dir_name', dest='out_dir_name',
                            default=None,
                            help='default name: [out_dir_prefix]-[method_type]-[numa_type]-[benchmark_args]-[out_dir_suffix]-[add_out_dir_time_suffix]')
    out_group.add_argument('--backup_dir', dest='backup_dir',
                            default="./backup",
                            help='default: ./backup')
    
    log_group = parser.add_argument_group('Group 3', 'log_group')
    log_group.add_argument('--log_my_stat', action='store_true', help='log my_stat')
    log_group.add_argument('--log_numa_maps', action='store_true', help='log numa_maps')
    log_group.add_argument('--log_vmstat', action='store_true', help='log vmstat')
    log_group.add_argument('--log_sysctl', action='store_true', help='log sysctl')
    log_group.add_argument('--log_dmesg', action='store_true', help='log dmesg(tail 100 lines)')

    config_group = parser.add_argument_group('Group 3', 'config_group')
    config_group.add_argument('--quiet', action='store_true', help='')

    exclusive_group = parser.add_mutually_exclusive_group()
    exclusive_group.add_argument('--overwrite', action='store_true', help='覆盖旧文件')
    exclusive_group.add_argument('--backup', action='store_true', help='备份旧文件')
    exclusive_group.add_argument('--delete', action='store_true', help='直接删除旧文件') 

    return parser.parse_args()

def get_user_choice():
    while True:
        user_input = input("请输入 'y/Y' 或 'n/N': ")
        if user_input.lower() == 'y':
            return True
        elif user_input.lower() == 'no':
            return False
        else:
            print("输出有误, 请重新输入")

def check_args(args):
    if not os.path.exists(args.benchmark_path):
        print("benchmark_path not exists: {}".format(args.benchmark_path))
        exit(0)

    if not os.path.exists(args.out_root):
        print("out_root not exists: {}".format(args.out_root))
        print("ready to create out_root")
        os.mkdir(args.out_root)

def gen_shell_command(command_str, comment=None):
    global out_script
    if comment:
        out_script.write(f"\n#{comment}\n")
    out_script.write(command_str + "\n")

def get_out_dir_name(args) -> str:
    arr = [args.out_dir_prefix, 
           args.method_type,
           args.numa_type,
           args.out_dir_suffix
           ]
    # 列表解析，拼接不为空的元素
    out_dir_name = '-'.join([word for word in arr if word])
    return out_dir_name

def build_out_dir(args) -> str:
    if args.out_dir_name != None:
        out_dir = os.path.join(args.out_root, args.out_dir_name)
    else:
        out_dir = os.path.join(args.out_root, get_out_dir_name(args))

    # 设置out_dir变量
    if args.add_out_dir_time_suffix:
        gen_shell_command('time_suffix=`date "+%Y%m%d-%Hh%Mm%Ss"`')
        gen_shell_command(f'out_dir="{out_dir}"-"$time_suffix"')
    else:
        gen_shell_command(f"out_dir={out_dir}")

    if args.delete:
        # 删除旧文件夹
        gen_shell_command(f'[ "$(ls -A "$out_dir")" ] && rm -r $out_dir"')
    elif args.backup:
        # 移动旧文件夹
        gen_shell_command('backup_time=`date "+%Y%m%d-%Hh%Mm%Ss"`')
        gen_shell_command('backup_dir="$out_dir-$backup_time"')
        gen_shell_command('[ "$(ls -A "$out_dir")" ] && mv "$out_dir" "$backup_dir"')

    # 创建文件夹
    gen_shell_command(f"mkdir -p $out_dir")
    return out_dir

def build_out_log(args):
    gen_shell_command("out_log=$out_dir/run.log", comment="set log")
    gen_shell_command('echo $(realpath "$out_dir/run.log")')
    # clear out_log
    gen_shell_command('echo "" > $out_log')
    
def set_sysctl_value(parameter, value):
    gen_shell_command(f"sudo sysctl -w {parameter}={value}")


def snapshot(args, pid:int, stage:str) -> str:
    if stage == "begin":
        isBegin = True
        isEnd = not isBegin
        prefix = "begin"
        gen_shell_command("\n# log start")
    else:
        isBegin = False
        isEnd = not isBegin
        prefix = "end"
        gen_shell_command("\n# log end")

    my_stat_path = "/proc/my_stat"
    numa_maps_path = "/proc/<pid>/numa_maps"

    if isBegin:
        # log out_script
        gen_shell_command(f"cat {args.out_script_path} > $out_dir/script.sh")

        # log caller_script
        if not os.path.exists(args.caller_script_path):
            print(f"input script: {args.caller_script_path} not exist, skip")
        else:
            gen_shell_command(f"cat {args.caller_script_path} > $out_dir/caller_script.sh")

        # log and clear dmesg
        gen_shell_command(f"sudo dmesg -c > $out_dir/dmesg-backup.log")

    # reset my_stat
    if isBegin and args.log_my_stat:
        gen_shell_command(f"echo reset | sudo tee {my_stat_path}")

    # log my_stat
    if args.log_my_stat:
        gen_shell_command(f"cat {my_stat_path} > $out_dir/my_stat-{prefix}.log")
    
    # log vmstat
    if args.log_vmstat:
        vmstat_path = "/proc/vmstat"
        gen_shell_command(f"cat {vmstat_path} > $out_dir/vmstat-{prefix}.log")

    if isEnd and args.log_vmstat:
        gen_shell_command(f'bash {vmstat_diff_path} $out_dir/vmstat-begin.log $out_dir/vmstat-end.log > $out_dir/vmstat_diff.log')

    # log node vmstat
    if args.log_vmstat:
        cmd = f'for file in /sys/devices/system/node/node*/vmstat; do cat "$file" > $out_dir/"$(basename "$(dirname "$file")")_vmstat_{prefix}.txt"; done'
        gen_shell_command(cmd)

    # log numactl
    if isBegin:
        gen_shell_command(f"numactl -H > $out_dir/numactl.log")

    # if args.log_numa_maps:
    #     gen_shell_command("cat {} > {}", numa_maps_path.replace("<pid>", pid), os.path.join(out_dir, f"{prefix}-numa_maps.log"))

    # log sysctl
    if isBegin and args.log_sysctl:
        gen_shell_command(f"sudo sysctl -a > $out_dir/sysctl.log")

    # log dmesg
    if args.log_dmesg:
        gen_shell_command(f'sudo dmesg -c > $out_dir/dmesg-{prefix}.log')

    gen_shell_command(f'echo $(realpath "$out_dir/run.log")')
    gen_shell_command(f'ls $out_dir')
    if isEnd:
        gen_shell_command(f'echo $out_dir/dmesg-end.log')

    return

def build_run_cmd(args) -> list:
    cmd = ["(time"]

    # cgroup config
    if args.cgroup_prefix:
        cmd += args.cgroup_prefix.split(" ")

    # numa type
    if args.numa_type == "default":
        pass
    elif args.numa_type == "interleave":
        cmd += "numactl --interleave=all".split(" ")

    # method type
    if args.method_type == "default":
        set_sysctl_value("kernel.numa_balancing", 0)
    elif args.method_type == "autonuma":
        set_sysctl_value("kernel.numa_balancing", 1)
    elif args.method_type == "pebs" or args.method_type == "ours":
        # todo: add page_predict
        cmd += [f"{launch_script_path}"]

    # enable markov
    if args.enable_markov:
        set_sysctl_value("page_predict.enable_markov", 1)

    # benchmark
    cmd += [args.benchmark_path]
    if args.benchmark_args:
        cmd += args.benchmark_args.split(" ")
    cmd += f") >> $out_log 2>&1".split(" ")

    return cmd

def resotre_state(args):
    # restore_state(args)
    if args.method_type == "default":
        set_sysctl_value("kernel.numa_balancing", 0)
    elif args.method_type == "autonuma":
        set_sysctl_value("kernel.numa_balancing", 0)

    # restore markov
    if args.enable_markov:
        set_sysctl_value("page_predict.enable_markov", 0)

def log_damen(args, out_dir: str):
    numa_maps_out = os.path.join(out_dir, "numa_maps.log")
    gen_shell_command(f"sudo echo ' ' > {numa_maps_out}")
    time.sleep(1)
    while 1:
        now_time = time.time()
        now_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now_time))

        gen_shell_command(f"sudo echo {now_time_str} >> {numa_maps_out}")
        gen_shell_command("sudo bash get_numa_maps.sh >> {}".format(numa_maps_out))
        time.sleep(60)

def set_env(args):
    if args.set_spec_env:
        gen_shell_command(textwrap.dedent(f'''\
        cd {accel2023_path}
        source {oneapi_path_script_path}
        source shrc
        cd -
        '''))

def run(args):
    # set var
    set_env(args)

    # build out dir
    out_dir = build_out_dir(args)

    # build out log
    build_out_log(args)

    # log start status
    snapshot(args, pid=-1, stage="begin")

    # set daemon
    gen_shell_command("", comment="set daemon")
    gen_shell_command(f"bash {watch_numamaps_script_path} {args.benchmark_path} > $out_dir/numa_maps.log &")
    if args.daemon_script_path:
        gen_shell_command(f'cat {args.daemon_script_path} > $out_dir/daemon_script.sh')
        gen_shell_command(f'bash {args.daemon_script_path} > $out_dir/daemon.log &')

    # log start time
    gen_shell_command('start_time=`date "+%Y-%m-%d %H:%M:%S"`')
    gen_shell_command('echo "start_time:"$start_time >> $out_log')

    # set cmd and log
    cmd = build_run_cmd(args)
    cmd_str = " ".join(cmd)
    print(cmd_str)

    # run
    gen_shell_command(f'echo "{cmd_str}"', comment="run")
    gen_shell_command(" ".join(cmd))

    # log end time
    gen_shell_command('end_time=`date "+%Y-%m-%d %H:%M:%S"`')
    gen_shell_command(textwrap.dedent("""\
        duration=`echo $(($(date +%s -d "${end_time}") - $(date +%s -d "${start_time}")))\ | awk '{t=split("60 s 60 m 24 h 999 d",a);for(n=1;n<t;n+=2){if($1==0)break;s=$1%a[n]a[n+1]s;$1=int($1/a[n])}print s}'`\
        """
    ))
    gen_shell_command('echo "end_time: $end_time, duration: $duration" >> $out_log')
    
    # log end status
    snapshot(args, pid=-1, stage="end")

    # resoter status
    # resotre_state(args)

def main():
    global out_script

    args = parse_arguments()
    # print(args)
    # check_args(args)
    out_script = open(args.out_script_path, "w")
    run(args)
    out_script.close()

    print(f"succeed generating script: {os.path.abspath(args.out_script_path)}")

if __name__ == "__main__":
    main()
