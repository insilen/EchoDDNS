# 基于阿里云DDNS A记录简单高可用性负载均衡解决方案

## 项目概述
在多IP(宽带)接入环境下，为了实现动态域名解析的高可用性和负载均衡，本项目提供了一套基于阿里云服务的动态域名解析（DDNS）解决方案。它能够将多个宽带出口的IPv4地址动态绑定到同一个子域名上实现负载均衡与简单服务高可用性。

## 适用场景

假设您有3个宽带出口，通过网关功能或其他脚本将出口的IPv4地址解析到以下子域名：

```
dns1.abc.com
dns2.abc.com
dns3.abc.com
```

在传统情况下，大多数平台对于同一个域名只能绑定一个IP地址，无法实现多个IP地址的负载均衡。

虽然可以通过CNAME记录将多个子域名指向同一个主域名（例如home.abc.com）以实现负载均衡。但这种方式存在一个显著的缺陷：一旦某个子域名对应的服务掉线，CNAME机制无法感知，导致访问时可能会出现超时。

假设home.abc.com CNAME了上述3个域名后设置了一定的权重或轮询后，nslookup测试如下
第1次
```
nslookup home.abc.com
...
Non-authoritative answer:
home.abc.com	canonical name = dns1.abc.com
Name:	dns1.abc.com
Address: 1.1.1.1
```

第2次
```
nslookup home.abc.com
...
Non-authoritative answer:
home.abc.com	canonical name = dns1.abc.com
Name:	dns2.abc.com
Address: 2.2.2.2
```
这时候 如果dns3.abc.com对应的IP切换或掉线后，轮询到dns3的时候，服务无法感知，导致访问时可能会出现超时


A记录负载均衡与CNAME负载均衡相比，A记录负载均衡（我更倾向于称之为简单高可用性负载均衡）能够提供更高的稳定性。

> Q: 简单高可用？
> A: 可用性交给你的浏览器来挑选

这种方法已经被许多大型CDN服务商采用。举例来说，当您查询`www.baidu.com`时，您会发现其A记录会解析到多个IP地址，这样即使某个IP服务不可用，浏览器也会自动尝试下一个IP地址，直至找到可用的服务。
```
nslookup www.baidu.com
...
Non-authoritative answer:
www.baidu.com	canonical name = www.a.shifen.com.
Name:	www.a.shifen.com
Address: 183.2.172.42
Name:	www.a.shifen.com
Address: 183.2.172.185
```


## 项目特色
本项目利用阿里云DNS API SDK接口，自动将多个DDNS域名的IP地址解析到同一个主域名下，确保了即使其中一个IP地址不可用时，用户的访问仍然可以被重新路由至其他在线的IP地址，从而大大提高了域名解析的可用性和稳定性。


## 快速开始
###  运行条件

- 在阿里云帐户中获取您的 [凭证](https://usercenter.console.aliyun.com/#/manage/ak)
  设置环境变量的 ACCESS_KEY_ID 以及 ACCESS_KEY_SECRET;

- 按要求设置域名

#### 打包方法
首先，你需要安装PyInstaller。你可以使用pip进行安装：
pip install pyinstaller

然后，你可以使用下面的命令将你的python脚本（例如main.py）打包为一个独立的可执行文件：
   pyinstaller --onefile --hidden-import=queue main.py

dockerfile
```
# 使用Alpine作为基础镜像
FROM python:3-alpine

# 安装supercronic
RUN sed -i 's#https://dl-cdn.alpinelinux.org#https://mirrors.tuna.tsinghua.edu.cn#g' /etc/apk/repositories
   
# 设置工作目录
WORKDIR /app

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
RUN echo "* * * * * python /app/alidns.py >> /var/log/cron.log 2>&1" > /etc/crontab

# 使用supercronic运行crontab
CMD ["/usr/local/bin/supercronic", "/etc/crontab"]
```



## 贡献指南
(在这一部分，您可以说明如何为项目贡献代码，包括代码提交规范、测试要求等。)


## 许可证
(在这一部分，您可以指出项目采用的许可证类型。)


## 联系方式
(在这一部分，您可以提供项目维护者的联系方式，方便用户反馈问题或建议。)
以上内容只是一个大致框架，具体的安装使用说明和贡献指南需要根据您项目的实际情况来编写。希望这个README模板对您的项目有所帮助！