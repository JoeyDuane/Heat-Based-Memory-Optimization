python3 gen_cmd.py\
    --add_out_dir_time_suffix\
    --out_script_path="./test.sh"\
    --caller_script_path="/home/dell/lmy/linux-lmy-b1/test.sh"\
    --out_dir_prefix="functest"\
    --benchmark_args "10 10"\
    --method_type="pebs"\
    --log_my_stat\
    --log_numa_maps\
    --log_vmstat\
    --log_sysctl\
    --log_dmesg\
    --quiet