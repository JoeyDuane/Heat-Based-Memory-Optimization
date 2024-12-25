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
from threading import Thread

my_stat_path = "/proc/my_stat"
vmstat_path = "/proc/vmstat"
numa_maps_path = "/proc/<pid>/numa_maps"

def parse_arguments():
    parser = argparse.ArgumentParser(description='run')

    benchmark_group = parser.add_argument_group('Group 1', 'benchmark_group')
    benchmark_group.add_argument('--benchmark_path', dest='benchmark_path',
                            default='/home/dell/lmy/graph500/src/graph500_reference_bfs',
                            help='default: "/home/dell/lmy/graph500/src/graph500_reference_bfs"')
    benchmark_group.add_argument('--benchmark_args', dest='benchmark_args',
                            default='10 10',
                            help='default: "10 10"')
    
    benchmark_group.add_argument('--numa_type', dest='numa_type',
                            choices=['default', 'interleave'],
                            default="interleave",
                            help='default, interleave')
    
    run_group = parser.add_argument_group('Group 2', 'run_group')
    run_group.add_argument('--method_type', dest='method_type',
                            help='可选参数: default, autonuma, memtis, autotiering, pebs, custom')
    run_group.add_argument('--enable_markov', action='store_true', 
                            help='set page_predict.enable_markov = 1')

    out_group = parser.add_argument_group('Group 3', 'out_group')
    out_group.add_argument('--out_root', dest='out_root',
                            default="./out",
                            help='default: ./out')
    out_group.add_argument('--out_prefix', dest='out_prefix',
                            default="",
                            help='default: empty str')
    out_group.add_argument('--out_suffix', dest='out_suffix',
                            default="",
                            help='default: empty str')
    out_group.add_argument('--out_dir_name', dest='out_dir_name',
                            default=None,
                            help='default name: [out_prefix]-[method_type]-[numa_type]-[benchmark_args]-[out_suffix]')
    out_group.add_argument('--backup_dir', dest='backup_dir',
                            default="./backup",
                            help='default: ./backup')
    
    log_group = parser.add_argument_group('Group 3', 'log_group')
    log_group.add_argument('--log_my_stat', action='store_true', help='log my_stat')
    log_group.add_argument('--log_numa_maps', action='store_true', help='log numa_maps')
    log_group.add_argument('--log_vmstat', action='store_true', help='log vmstat')
    log_group.add_argument('--log_sysctl', action='store_true', help='log sysctl')

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

    if args.log_my_stat and not os.path.exists(my_stat_path):
        print("my_stat_path not exists: {}".format(my_stat_path))
        exit(0)

    if not os.path.exists(args.out_root):
        print("out_root not exists: {}".format(args.out_root))
        print("ready to create out_root")
        os.mkdir(args.out_root)

def get_out_dir_name(args) -> str:
    benchmark_args = args.benchmark_args.replace(" ", "-")
    arr = [args.out_prefix, 
           args.method_type,
           args.numa_type, 
           benchmark_args,
           args.out_suffix
           ]
    # 列表解析，拼接不为空的元素
    out_dir_name = '-'.join([word for word in arr if word])
    return out_dir_name

def build_out_dir(args) -> str:
    if args.out_dir_name != None:
        out_dir = os.path.join(args.out_root, args.out_dir_name)
    else:
        out_dir = os.path.join(args.out_root, get_out_dir_name(args))

    if not os.path.exists(out_dir):
        os.mkdir(out_dir)
        return out_dir
    elif len(os.listdir(out_dir)) == 0:
        # 空文件夹
        return out_dir

    # else
    if args.delete:
        if not args.quiet:
            print("将要删除文件夹: {}, 请确认".format(out_dir))
            if not get_user_choice():
                print("quit")
                exit()
        # 删除旧文件夹
        shutil.rmtree(out_dir)
        # 重新创建文件夹
        os.mkdir(out_dir)
    elif args.backup:
        if not os.path.exists(args.backup_dir):
            print("备份文件夹: mkdir {}".format(args.backup_dir))
            os.mkdir(args.backup_dir)
        # 移动旧文件夹
        time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
        dir_name = os.path.basename(out_dir)
        shutil.move(out_dir, os.path.join(args.backup_dir, f"{dir_name}-{time_str}"))
        # 重新创建文件夹
        os.mkdir(out_dir)
    else:
        # if args.overwrite:
        if not args.quiet:
            print("将要覆写文件夹: {}, 请确认".format(out_dir))
            if not get_user_choice():
                print("quit")
                exit()

    return out_dir

def get_sysctl_value(parameter):
    try:
        # 使用 subprocess 运行 sysctl 命令并获取输出
        output = subprocess.check_output(['sysctl', parameter])
        output = output.decode('utf-8').strip()  # 解码并去除首尾空白字符
        return output.split(': ')[1]  # 提取参数值部分
    except subprocess.CalledProcessError as e:
        print(f"获取参数 {parameter} 值时出错: {e}")
        return None
    
def set_sysctl_value(parameter, value):
    try:
        # 使用 subprocess 运行 sysctl 命令设置参数的值
        subprocess.run(['sudo', 'sysctl', '-w', f'{parameter}={value}'], check=True)
        print(f"参数 {parameter} = {value} 设置成功")
    except subprocess.CalledProcessError as e:
        print(f"设置参数 {parameter} = {value} 值时出错: {e}")

def run_shell_command(command_str) -> str:
    # 将命令字符串拆分成一个列表
    command_list = shlex.split(command_str)
    # print("command_list:", command_list)

    try:
        # 返回值类型：class subprocess.CompletedProcess
        result = subprocess.run(command_list, capture_output=True, text=True)
        # print("result.stdout:", result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        print(f"命令执行失败: {e}")
        print("result.stderr:", result.stdout)
        return ""

def restore_state(args):
    pass

def raw_shell_command(command_str):
    # print("command_str:", command_str)
    os.system(command_str)

start_time = None
end_time = None
def snapshot(args, out_dir: str, command: str, pid: int, stage = "begin") -> str:
    global start_time
    global end_time

    if stage == "begin":
        isBegin = True
        isEnd = not isBegin
        prefix = "begin"
    else:
        isBegin = False
        isEnd = not isBegin
        prefix = "end"

    print(stage)
    
    if isBegin and args.log_my_stat:
        raw_shell_command("echo reset | sudo tee {}".format(my_stat_path))
    if args.log_my_stat:
        raw_shell_command("cat {} > {}".format(my_stat_path, os.path.join(out_dir, f"my_stat-{prefix}.log")))
    if args.log_vmstat:
        raw_shell_command("cat {} > {}".format(vmstat_path, os.path.join(out_dir, f"vmstat-{prefix}.log")))
    # numactl
    raw_shell_command("numactl -H > {}".format(os.path.join(out_dir, f"numactl.log")))
    # if args.log_numa_maps:
    #     raw_shell_command("cat {} > {}", numa_maps_path.replace("<pid>", pid), os.path.join(out_dir, f"{prefix}-numa_maps.log"))

    if isBegin and args.log_sysctl:
        raw_shell_command("sudo sysctl -a > {}".format(os.path.join(out_dir, "sysctl.log")))

    out_log = os.path.join(out_dir, "run.log")
    if isBegin:
        # 清空
        raw_shell_command(f"echo ' ' > {out_log}")
        # 命令
        raw_shell_command(f"echo command: {command} >> {out_log}")
        # 起始时间
        start_time = time.time()
        start_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time))
        raw_shell_command(f"echo start_time: {start_time_str} >> {out_log}")

    if isEnd:
        # 终止时间与持续时间
        end_time = time.time()
        duration_seconds = end_time - start_time
        duration = datetime.timedelta(seconds = duration_seconds)
        end_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time))
        duration_str = humanize.naturaldelta(duration)
        raw_shell_command(f"echo end_time: {end_time_str} >> {out_log}")
        raw_shell_command(f"echo duration: {duration} >> {out_log}")
        raw_shell_command(f"echo duration: {duration_str} >> {out_log}")

    return out_log

def gen_cmd(args) -> list:
    cmd = []

    # numa type
    if args.numa_type == "default":
        pass
    elif args.numa_type == "interleave":
        cmd += "time numactl --interleave=all".split(" ")

    # method type
    if args.method_type == "default":
        set_sysctl_value("kernel.numa_balancing", 0)
    elif args.method_type == "autonuma":
        set_sysctl_value("kernel.numa_balancing", 1)
    elif args.method_type == "pebs":
        # todo: add page_predict
        cmd += ["sudo /home/dell/lmy/linux-lmy-latest/test_pebs/test_pebs"]

    # enable markov
    if args.enable_markov:
        set_sysctl_value("page_predict.enable_markov", 1)

    # benchmark
    cmd += [args.benchmark_path]
    cmd += args.benchmark_args.split(" ")
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

def run_cmd_by_python(cmd, out_dir) -> int:
    benchmark_log = os.path.join(out_dir, "benchmark.log")
    print(benchmark_log)
    # 运行程序
    with open(benchmark_log, "w") as log_file:
        process = subprocess.Popen(cmd, stdout=log_file, stderr=log_file)
        pid = process.pid

    # 读取并打印子进程的输出到终端
    # for line in iter(process.stdout.readline, b''):
    #     line_str = line.decode('utf-8').strip()
    #     print(line_str)
    #     raw_shell_command(f"echo {line_str} >> {out_log}")

    # for line in iter(process.stderr.readline, b''):
    #     line_str = line.decode('utf-8').strip()
    #     print(line_str)
    #     raw_shell_command(f"echo {line_str} >> {out_log}")

    process.wait()
    return pid

def run_cmd_by_shell(cmd_str: str, out_log: str):
    print(out_log)
    raw_shell_command(f"{cmd_str} >> {out_log} 2>&1")

def log_damen(args, out_dir: str):
    numa_maps_out = os.path.join(out_dir, "numa_maps.log")
    raw_shell_command(f"sudo echo ' ' > {numa_maps_out}")
    time.sleep(1)
    while 1:
        now_time = time.time()
        now_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now_time))

        raw_shell_command(f"sudo echo {now_time_str} >> {numa_maps_out}")
        raw_shell_command("sudo bash get_numa_maps.sh >> {}".format(numa_maps_out))
        time.sleep(60)

def run(args):
    cmd = gen_cmd(args)
    cmd_str = " ".join(cmd)
    print(cmd_str)
    
    out_dir = build_out_dir(args)
    out_log = snapshot(args, out_dir, cmd_str, pid=-1, stage="begin")
    # cmd += cmd + f"> {out_log}".split(" ")

    # pid = run_cmd_by_python(cmd, out_dir)
    # run_cmd_by_shell(cmd_str, out_log)
    thread_bench = Thread(target=run_cmd_by_shell, args=(cmd_str, out_log))
    thread_bench.start()

    # 父线程结束时，daemon线程会随之结束
    thread_log = threading.Thread(target=log_damen, args=(cmd_str, out_dir), name='log_damen', daemon=True)
    thread_log.start()

    # 等待thread_bench线程结束
    thread_bench.join()

    pid = -1
    snapshot(args, out_dir, " ".join(cmd), pid=pid, stage="end")

    resotre_state(args)

def main():
    args = parse_arguments()
    # print(args)
    check_args(args)

    run(args)

if __name__ == "__main__":
    main()
