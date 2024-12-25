RedisRoot=/home/dell/lmy/my_benchmarks/redis-7.2.4

# 每个请求1KB
data_size=1024

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

shutdown_redis_connect()
{
    echo "-----send shutdown signal"
    time $RedisRoot/src/redis-cli shutdown
    echo "-----finish test redis db"
}

redis_benchmark_build_redis_db()
{  
    # build redis db
    set_reqs=$((100 * 1024))
    echo "-----set_reqs: $set_reqs"
    time $RedisRoot/src/redis-benchmark -t set -d $data_size --csv\
            -n $set_reqs -c 50 --threads 50 -r 100000000 --seed 0
}

redis_benchmark_test_redis_db()
{
    # test redis db
    get_reqs=$((100 * 1024))
    echo "-----get_reqs: $get_reqs"
    time $RedisRoot/src/redis-benchmark -t get -d $data_size --csv\
            -n $get_reqs -c 10 --threads 10 -r 100000000 --seed 0
}

memtier_benchmark_build_redis_db()
{
    # build redis db
    # todo
}

memtier_benchmark_test_redis_db()
{
    # build redis db
    # todo
}

# 1. connect
test_redis_connect

# 2. test
redis_benchmark_build_redis_db
redis_benchmark_test_redis_db

# 3. shutdown
shutdown_redis_connect
