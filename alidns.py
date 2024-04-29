import os
import re
import queue
import sys
import json
from colorama import Fore,Back,Style
import logging
from aliyunsdkcore.client import AcsClient
from aliyunsdkalidns.request.v20150109.DescribeDomainRecordsRequest import DescribeDomainRecordsRequest
from aliyunsdkalidns.request.v20150109.UpdateDomainRecordRequest import UpdateDomainRecordRequest
from aliyunsdkalidns.request.v20150109.DescribeDomainRecordInfoRequest import DescribeDomainRecordInfoRequest


# 环境安装
## pip install aliyun-python-sdk-core-v3 aliyun-python-sdk-alidns pyinstaller colorama -i https://pypi.tuna.tsinghua.edu.cn/simple
## pip install aliyun-python-sdk-alidns -i https://pypi.tuna.tsinghua.edu.cn/simple
## pip install pyinstaller  -i https://pypi.tuna.tsinghua.edu.cn/simple

# 设置日志格式和日期格式
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

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

# 参数检测
# 必需的参数列表
required_params = {
    'ACCESSKEY_ID': accesskey_id,
    'ACCESSKEY_SECRET': accesskey_secret,
    'DOMAIN_NAME': domain_name,
    'A_DOMAIN': a_domain,
}

# 检查基本必需的参数是否提供
missing_params = [key for key, value in required_params.items() if value is None]

# 检查DDNS和A_RecordId配对
ddns_provided = False
for i in range(1, 4):
    ddns = os.getenv(f'DDNS{i}_DOMAIN')
    record_id = os.getenv(f'A_RecordId{i}')
    if ddns or record_id:
        if not ddns:
            missing_params.append(f'DDNS{i}_DOMAIN')
        if not record_id:
            missing_params.append(f'A_RecordId{i}')
        if ddns and record_id:
            ddns_provided = True

# 至少需要提供一组DDNS_DOMAIN和A_RecordId
if not ddns_provided:
    missing_params.append('[🚫] 至少要提供一组 DDNS_DOMAIN 和 A_RecordId')

# 检查是否有缺失的参数
if missing_params:
    logging.info("[🚫] Error: 请检查环境变量 缺少必需的参数:")
    for param in missing_params:
        print(f" - {param}")
    sys.exit(1)


# 初始化客户端
client = AcsClient(accesskey_id, accesskey_secret, service_loctaion)

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
#print(rr_domain)
 
# A_RecordId 字典
record_ids = {key: value for key, value in os.environ.items() if key.startswith('A_RecordId')}
#print(record_ids)

# 从SDK中获取IP的方法
def getips_sdk(rr_domains):
    """
    获取多个域名前缀对应的IP地址。
    :param rr_domains: 域名前缀列表
    :return: 一个字典，键为域名前缀，值为对应的IP地址
    """
    ips_dict = {}
    for rr_domain in rr_domains:
        request = DescribeDomainRecordsRequest()
        request.set_DomainName(domain_name)
        request.set_TypeKeyWord('A')
        request.set_RRKeyWord(rr_domain)  # 使用RR值进行查询
        response = client.do_action_with_exception(request)
        records = json.loads(response)
        # print(f"SDK Response for {rr_domain}: {records}")  # 调试打印
        for record in records['DomainRecords']['Record']:
            if record['RR'] == rr_domain:
                # print(f"IP found for {rr_domain}: {record['Value']}")  # 调试打印
                ips_dict[rr_domain] = record['Value']
                break  # 找到匹配的记录后，跳出循环
        if rr_domain not in ips_dict:
            logging.info(f"[🚫] 未找到DDNS子域的相关记录: {rr_domain}")
            ips_dict[rr_domain] = None  # 如果未找到记录，设置为 None   
    return ips_dict

# 获得DDNS域名和IP
ddnsips_dict = getips_sdk(rr_domain)
logging.info("[DDNS解析域名]:" + Fore.BLUE + str(ddnsips_dict) + Style.RESET_ALL)


def get_record_ids_ips(record_ids):
    """
    查询 record_ids 中 RecordId 值对应的 A 记录 IP。
    
    :param record_ids: 包含 RecordId 的字典
    :return: 一个字典，键为 RecordId，值为对应的 IP 地址。
    """
    ips_dict = {}
    for key, record_id in record_ids.items():
        try:
            request = DescribeDomainRecordInfoRequest()
            request.set_RecordId(record_id)
            response = client.do_action_with_exception(request)
            current_ip = json.loads(response)['Value']
            ips_dict[record_id] = current_ip
        except Exception as e:
            logging.info(f"[🚫] 获取RecordId时候出错: {record_id}: {str(e)}")
            ips_dict[record_id] = None  # 或者选择其他方式来处理错误
    return ips_dict

# 获得负载均衡域名RecordId和IP
aips_dict = get_record_ids_ips(record_ids)
logging.info("[负载均衡域名]:" + Fore.BLUE +  str(aips_dict) + Style.RESET_ALL)

 
def find_mismatched_ips(ddnsips_dict, aips_dict):
    # 删除aips_dict中值与ddnsips_dict中值匹配的键值对
    for key, value in list(aips_dict.items()):
        for ddns_key, ddns_value in list(ddnsips_dict.items()):
            if value == ddns_value:
                del aips_dict[key]
                del ddnsips_dict[ddns_key]

    # 重新组合aips_dict的键与ddnsips_dict的值
    new_aips_dict = dict(zip(aips_dict.keys(), ddnsips_dict.values()))
    # 如果有更新则返回字典 无更新则 None
    return new_aips_dict if new_aips_dict else None


def update_arecord(updates_dict, a_domain):
    """
    更新A记录的IP地址。
    
    :param updates_dict: 包含记录ID和新IP地址的字典
    :param a_domain: 要更新的子域名
    """
    for record_id, new_ip in updates_dict.items():
        try:
            request = UpdateDomainRecordRequest()
            request.set_RecordId(record_id)
            request.set_RR(a_domain)  # 子域名
            request.set_Type('A')
            request.set_TTL(domain_ttl)  # TTL时间，默认600
            request.set_Value(new_ip)  # 新的IP地址
            # 发送请求并打印响应
            response = client.do_action_with_exception(request)
            #logging.info(f"[📥] 发现并更新了子域名 {a_domain} 的新IP: {new_ip}")
        except Exception as e:
            logging.error(f"[❌] 更新子域名 {a_domain} IP时发生错误: {str(e)}")



def main():
    # 比对负载均衡域名的IP和DDNS的IP是否有区别
    mismatched_ips_output = find_mismatched_ips(ddnsips_dict, aips_dict)
    #print(mismatched_ips_output)
    # 打印输出结果
    if mismatched_ips_output:
        update_arecord(mismatched_ips_output, a_domain)
        logging.info(f"[📥]  " + Back.YELLOW + f"发现新IP 更新了子域名{a_domain}.{domain_name}: {mismatched_ips_output}" + Style.RESET_ALL)
    else:
        logging.info(f"[💤] " + Fore.GREEN + "例行查询负载均衡子域名 IP没有变动 程序自动跳过" + Style.RESET_ALL)


if __name__ == '__main__':
    main()



    