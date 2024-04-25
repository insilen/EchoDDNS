import os
import re
import json
import logging
from aliyunsdkcore.client import AcsClient
from aliyunsdkalidns.request.v20150109.DescribeDomainRecordsRequest import DescribeDomainRecordsRequest
from aliyunsdkalidns.request.v20150109.UpdateDomainRecordRequest import UpdateDomainRecordRequest
from aliyunsdkalidns.request.v20150109.DescribeDomainRecordInfoRequest import DescribeDomainRecordInfoRequest

# 环境安装
## pip install aliyun-python-sdk-core-v3 -i https://pypi.tuna.tsinghua.edu.cn/simple
## pip install aliyun-python-sdk-alidns -i https://pypi.tuna.tsinghua.edu.cn/simple
## pip install pyinstaller  -i https://pypi.tuna.tsinghua.edu.cn/simple

# 环境变量读取
accesskey_id = os.getenv('ACCESSKEY_ID')                              #  阿里云 AK
accesskey_secret = os.getenv('ACCESSKEY_SECRET')                      #  阿里云 AK
service_loctaion = os.getenv('SERVICE_LOCATION', 'cn-chengdu')        #  阿里云服务区地域 
domain_name = os.getenv('DOMAIN_NAME')                                #  主域名
query_mode = os.getenv('QUERY_MODE', 'SDK')                           #  运行模式SDK 或 DNS
query_dns = os.getenv('QUERY_DNS', '223.5.5.5,223.6.6.6').split(',')  #  运行模式为 DNS 时候可自定义
domain_ttl = os.getenv('DOMAIN_TTL', 600)                             #  A解析域名TTL 默认600
sub_domains = [os.getenv(f'DDNS{i}_DOMAIN') for i in range(1, 4) if os.getenv(f'DDNS{i}_DOMAIN')]   # 获取DDNS域名
a_domain = os.getenv('A_DOMAIN')                                      # 获取主域名

# 初始化客户端
client = AcsClient(accesskey_id, accesskey_secret, service_loctaion)

# 设置日志格式和日期格式
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# AliyunDNS SDK只需要域名前缀的问题 域名解析前缀
def get_subdomain(domain_name, ddns_domains):
    pattern = r"^(.*?)(?:\." + re.escape(domain_name) + r")?$"
    sub_domains = []
    #判断数组还是单个域名用不同的处理方法
    if isinstance(ddns_domains, list):
        for ddns_domain in ddns_domains:
            match = re.match(pattern, ddns_domain)
            if match:
                sub_domains.append(match.group(1))
            else:
                sub_domains.append(ddns_domain)
    else:
        match = re.match(pattern, ddns_domains)
        if match:
            return match.group(1)
        else:
            return ddns_domains
    return sub_domains

# 通过上方前缀解析 切换到需要的前缀类型RR
rr_domain = get_subdomain(domain_name, sub_domains)
a_domain = get_subdomain(domain_name, a_domain)
#print(a_domain)
 
# 解析对应表 字典
record_ids = {rr_domain: os.getenv(f'A_RecordId{i}') for i, rr_domain in enumerate(rr_domain, 1)}

# 从SDK中获取IP的方法
def getip_sdk(rr_domain):
    request = DescribeDomainRecordsRequest()
    request.set_DomainName(domain_name)
    request.set_TypeKeyWord('A')
    request.set_RRKeyWord(rr_domain)  # 使用RR值进行查询
    response = client.do_action_with_exception(request)
    records = json.loads(response)
    #print(f"SDK Response for {rr_domain}: {records}")  # 调试打印
    for record in records['DomainRecords']['Record']:
        if record['RR'] == rr_domain:
            #print(f"IP found for {rr_domain}: {record['Value']}")  # 调试打印
            return record['Value']
    return None

def update_arecord(record_id, a_domain, new_ip):
    # 先获取当前的A记录的IP地址
    request = DescribeDomainRecordInfoRequest()
    request.set_RecordId(record_id)
    response = client.do_action_with_exception(request)
    current_ip = json.loads(response)['Value']
    
    # 只有当新的IP地址与当前的IP地址不同时，才更新A记录
    if new_ip != current_ip:
        request = UpdateDomainRecordRequest()
        request.set_RecordId(record_id)
        request.set_RR(a_domain)
        request.set_Type('A')
        request.set_TTL(domain_ttl)  #TTL时间  默认600
        request.set_Value(new_ip)
        # 发送请求并打印响应
        response = client.do_action_with_exception(request)
        logging.info(f"[📥] 发现并更新了子域名 {rr_domain} 的新IP: {new_ip}")
    else:
        logging.info(f"[💤] 例行查询子域名 {rr_domain}. IP没有变动 程序自动跳过")

def main():
    global rr_domain
    # 获取每个子域名的IP地址
    ips = {rr: getip_sdk(rr) for rr in rr_domain}
    #print(ips)
    # 更新A记录
    for rr_domain, ip in ips.items():
        if ip:
            record_id = record_ids.get(rr_domain)
            if record_id:
                update_arecord(record_id, a_domain, ip)
            else:
                logging.info(f"[🚫] 未找到子域的RecordId记录: {rr_domain}")
        else:
            logging.info(f"[🚫] 无法获取子域的IP: {rr_domain}")

if __name__ == '__main__':
    main()



    