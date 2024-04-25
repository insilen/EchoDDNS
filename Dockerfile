# 第一阶段：构建可执行文件
# 使用Python官方镜像作为构建环境
FROM python:3.9 AS builder

# 设置工作目录
WORKDIR /build

# 安装依赖
RUN pip install --no-cache-dir aliyun-python-sdk-core-v3 aliyun-python-sdk-alidns pyinstaller -i https://pypi.tuna.tsinghua.edu.cn/simple

# 拷贝源代码
COPY alidns.py .

# 使用pyinstaller编译成单文件可执行程序
RUN pyinstaller --onefile alidns.py


################### 第二阶段：构建最终镜像 ###################
# 第二阶段：使用Debian Buster Slim镜像运行
FROM debian:buster-slim

# 设置工作目录
WORKDIR /app

# 从构建阶段拷贝编译好的二进制文件
COPY --from=builder /build/dist/alidns .

# 安装glibc库和cron
RUN sed -i 's#http://deb.debian.org#http://mirrors.tuna.tsinghua.edu.cn#g' /etc/apt/sources.list
RUN apt-get update && apt-get install -y libc6 cron && rm -rf /var/lib/apt/lists/*

# 拷贝supercronic到容器中，并赋予执行权限
COPY supercronic-linux-amd64 /usr/local/bin/supercronic
RUN chmod +x /usr/local/bin/supercronic && chmod +x /app/

# 创建一个crontab文件
RUN echo "* * * * * root ./alidns 2>&1" > /etc/crontab/alidns

# 使用supercronic运行crontab
CMD ["/usr/local/bin/supercronic", "-quiet", "-passthrough-logs", "/etc/crontab"]