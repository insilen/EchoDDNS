# 使用Alpine作为基础镜像
FROM python:3-alpine

# 设置工作目录
WORKDIR /app

# 控制日志类型
ENV CRON_LOG_LEVEL=error

# 安装Python依赖
# 合并安装命令，并清理pip缓存
RUN sed -i 's#https://dl-cdn.alpinelinux.org#https://mirrors.tuna.tsinghua.edu.cn#g' /etc/apk/repositories && \
    pip install --no-cache-dir aliyun-python-sdk-core-v3 aliyun-python-sdk-alidns -i https://pypi.tuna.tsinghua.edu.cn/simple

# 拷源代码到工作目录
COPY alidns.py ./alidns.py

# 在这里下载 https://github.com/aptible/supercronic/releases
# 使用ADD命令直接下载supercronic，并赋予执行权限
COPY supercronic-linux-amd64 /usr/local/bin/supercronic
RUN chmod +x /usr/local/bin/supercronic

# 创建一个crontab文件
RUN echo "* * * * * python /app/alidns.py 2>&1" > /etc/crontab

# 使用supercronic运行crontab
CMD ["/usr/local/bin/supercronic", "-quiet", "-passthrough-logs", "/etc/crontab"]