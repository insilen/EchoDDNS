# 使用Alpine作为基础镜像
FROM python:3-alpine

# 安装supercronic
RUN sed -i 's#https://dl-cdn.alpinelinux.org#https://mirrors.tuna.tsinghua.edu.cn#g' /etc/apk/repositories
   
# 设置工作目录
WORKDIR /app

# 控制日志类型
ENV CRON_LOG_LEVEL=error

# 安装Python依赖
RUN pip install aliyun-python-sdk-core-v3 -i https://pypi.tuna.tsinghua.edu.cn/simple \
    && pip install aliyun-python-sdk-alidns -i https://pypi.tuna.tsinghua.edu.cn/simple 

# 拷贝您的源代码到工作目录
COPY alidns.py ./alidns.py

# 在这里下载 https://github.com/aptible/supercronic/releases
COPY supercronic-linux-amd64 ./supercronic-linux-amd64

RUN chmod +x supercronic-linux-amd64 \
    && mv supercronic-linux-amd64 /usr/local/bin/supercronic

# 创建一个crontab文件
RUN echo "* * * * * python /app/alidns.py 2>&1" > /etc/crontab

# 使用supercronic运行crontab
CMD ["/usr/local/bin/supercronic", "-silent", "-passthrough", "/etc/crontab"]