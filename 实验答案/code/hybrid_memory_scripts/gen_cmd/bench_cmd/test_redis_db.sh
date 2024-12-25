RedisRoot=/home/dell/lmy/my_benchmarks/redis-7.2.4

test_redis_connect()
{       
    # 最大尝试连接次数和超时时间（秒）
    MAX_ATTEMPTS=10
    TIMEOUT=1

    # 连接计数器
    try_cnt=0

    # 循环尝试连接Redis服务器
    while true; do
    # 尝试连接Redis服务器
    $RedisRoot/src/redis-cli ping &> /dev/null

    # 检查连接状态
    if [ $? -eq 0 ]; then
        echo "succeed connecting redis-server"
        break
    fi

    # 增加尝试计数器
    try_cnt=$((try_cnt + 1))

    # 检查是否达到最大尝试次数
    if [ $try_cnt -eq $MAX_ATTEMPTS ]; then
        echo "failed to connect redis-server, quit"
        exit
    fi

    # 等待1秒
    sleep $TIMEOUT
    done
}

test_redis_connect

# 每个请求1KB
data_size=1024

# build redis db
# 16M个写请求
set_reqs=$((16 * 1024 * 1024))
echo "-----set_reqs: $set_reqs"
time $RedisRoot/src/redis-benchmark -t set -d $data_size --csv\
        -n $set_reqs -c 50 --threads 50 -r 100000000 --seed 0

# test redis db
get_reqs=$((8 * 16 * 1024 * 1024))
echo "-----get_reqs: $get_reqs"
time $RedisRoot/src/redis-benchmark -t get -d $data_size --csv\
        -n $get_reqs -c 10 --threads 10 -r 100000000 --seed 0

echo "-----send shutdown signal"
time $RedisRoot/src/redis-cli shutdown

echo "-----finish test redis db"