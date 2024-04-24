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

使用Docker Compose直接运行，配置的环境变量如下
```
- "ACCESSKEY_ID=<HIDE>"        # 阿里云 AK 访问https://ram.console.aliyun.com/users/ 创建用户并授AliyunDNSFullAccess权限
- "ACCESSKEY_SECRET=<HIDE>"    # 阿里云 AK
- "DOMAIN_TTL=60"              # 高可用解析 TTL 不添加此行则为600 可选60,120,600,1800,3600,36000,86400
- "DOMAIN_NAME=example.com"         # 需要操作的主域名
- "DDNS1_DOMAIN=dns1.example.com"   # DDNS域名1(源)
- "DDNS2_DOMAIN=dns2.example.com"   # DDNS域名2(源)
- "A_DOMAIN=a.dns.example.com"      # 所有DDNS IP 最终解析的简单高可用域名
- "A_RecordId1=1234"           # 最终解析的域名的RecordId 访问https://next.api.aliyun.com/api/Alidns/2015-01-09/DescribeSubDomainRecords 查询获取
- "A_RecordId2=1235"           
```

注意其中的 DOMAIN_TTL 如果你没有购买企业版DNS TTL 1分钟版本，那么建议直接删除`- "DOMAIN_TTL=60"` 整行配置，就会使用默认的600（10分钟）参数

配置例子:
```
主域名: example.com
DDNSIP数量: 3个 IP:10.0.0.10  10.0.0.20  10.0.0.30
DDNS1域名: dns1.example.com 10.0.0.10
DDNS2域名: dns2.example.com 10.0.0.20
DDNS3域名: dns3.example.com 10.0.0.30
```
假设以上部分已经从你的网关或路由中实现了功能，那么久能顺利的利用本项目来继续实现：


域名解析后台建立3个简单高可用域名:
```
a.dns.example.com 1.1.1.1
a.dns.example.com 2.2.2.2
a.dns.example.com 3.3.3.3
```
域名为同一个，但解析到不同的临时IP上。

然后访问 https://next.api.aliyun.com/api/Alidns/2015-01-09/DescribeSubDomainRecords
 
SubDomain中查询 a.dns.example.com 

在调用结果中可以看到3段json，记录他们的RecordId：`1455682456000096`,`1455680456002021`,`1455682456000291`
他们分别对应上面的3个a.dns.example.com

然后作出Docker compose 环境配置:
````
- "ACCESSKEY_ID=xxxxxxxx"
- "ACCESSKEY_SECRET=xxxxxxxxxxxxxxxxxxx" 
- "DOMAIN_NAME=example.com"
- "DDNS1_DOMAIN=dns1.example.com" 
- "DDNS2_DOMAIN=dns2.example.com"
- "DDNS3_DOMAIN=dns3.example.com"
- "A_DOMAIN=a.dns.example.com"
- "A_RecordId1=1455682456000096"
- "A_RecordId2=1455680456002021"
- "A_RecordId3=1455682456000291"     
```

上述例子运行后 则会得到下面结果
```
a.dns.example.com 10.0.0.10
a.dns.example.com 10.0.0.20
a.dns.example.com 10.0.0.30
```