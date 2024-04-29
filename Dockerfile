# 第一阶段：构建可执行文件
# 使用Alpine Python镜像作为构建环境
FROM python:3.9-alpine as builder

# 设置工作目录
WORKDIR /build

# 安装依赖
RUN sed -i 's#https://dl-cdn.alpinelinux.org#https://mirrors.tuna.tsinghua.edu.cn#g' /etc/apk/repositories

# 安装PyInstaller和所需的依赖
RUN apk add --no-cache build-base libffi-dev binutils

RUN pip install --no-cache-dir aliyun-python-sdk-core-v3 aliyun-python-sdk-alidns pyinstaller colorama -i https://pypi.tuna.tsinghua.edu.cn/simple

# 拷贝源代码
COPY alidns.py .

# 使用pyinstaller编译成单文件可执行程序
RUN pyinstaller --onefile alidns.py


################### 第二阶段：构建最终镜像 ###################
# 第二阶段
FROM alpine:latest

# 设置工作目录
WORKDIR /app

# 控制日志类型
ENV CRON_LOG_LEVEL=error

# 拷源二进制到目录
COPY --from=builder /build/dist/alidns .

# 在这里下载 https://github.com/aptible/supercronic/releases 考虑到国内网络环境 不使用ADD了
# 使用ADD命令直接下载supercronic，并赋予执行权限
COPY supercronic-linux-amd64 /usr/local/bin/supercronic
RUN chmod +x /usr/local/bin/supercronic && chmod +x /app/alidns

# 创建一个crontab文件
RUN echo "* * * * * /app/alidns 2>&1" > /etc/crontab

# 使用supercronic运行crontab
CMD ["/usr/local/bin/supercronic", "-quiet", "-passthrough-logs", "/etc/crontab"]