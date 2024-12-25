# Usage: %s [threads] [updates per thread] [date size exponent] [element size (bytes)] [hot size exponent]

# test ./gups-pebs
# 1M : 0.5M
# echo -e "\n=== gups-pebs ==="
# ./gups-pebs 1 10000 10 8 9
# /home/dell/lmy/my_scripts/pebs_syscall/test_pebs ./gups-pebs 1 10000 10 8 9

# sudo cgcreate -g cpu,memory:mygroup
# sudo chown dell:dell -R /sys/fs/cgroup

# 4G : 1G
# echo -e "\n=== gups-pebs ==="
# cgexec -g cpu:mygroup  
time cgexec -g cpu:mygroup /home/dell/lmy/my_scripts/pebs_syscall/test_pebs ./gups-pebs 4 1000000000 34 8 30

# # test ./gups-random
# echo -e "\n=== gups-random ==="
# ./gups-random 1 10000 10 8 9

# echo -e "\n=== gups-hotset-move ==="
# ./gups-hotset-move 1 10000 10 8 9
