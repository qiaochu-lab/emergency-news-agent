# -*- coding: utf-8 -*-
import json
import urllib.request
import urllib.parse
import time

def main_handler(event, context):
    # 允许的来源（星号表示所有域都可以访问，方便调试）
    allow_origin = "*"

    # 处理 CORS 预检请求
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': allow_origin,
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type',
            },
            'body': ''
        }

    # 解析 POST body
    body = event.get('body', '{}')
    try:
        data = json.loads(body)
    except:
        data = {}

    item_id = data.get('item_id', '')
    title = data.get('title', '')
    url = data.get('url', '')
    reaction = data.get('reaction', '')
    timestamp = data.get('timestamp', str(int(time.time())))

    # ====== 飞书配置（你自己应用的信息）======
    APP_ID = 'cli_a95ca77f46799bce'
    APP_SECRET = 'rJfkNBvcX2g5SRXjVozIwhwHnucuLCO3'
    TABLE_TOKEN = 'tbl5Xgf9mS93KYyb'

    # 1. 获取 tenant_access_token
    token_url = 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal'
    token_data = json.dumps({"app_id": APP_ID, "app_secret": APP_SECRET}).encode('utf-8')
    req = urllib.request.Request(token_url, data=token_data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req) as resp:
        token_result = json.loads(resp.read())
    tenant_token = token_result.get('tenant_access_token', '')

    if not tenant_token:
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': allow_origin},
            'body': json.dumps({'error': 'failed to get token'})
        }

    # 2. 获取表格字段 ID 映射
    fields_url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{TABLE_TOKEN}/tables/tbl5Xgf9mS93KYyb/fields'
    req = urllib.request.Request(fields_url, headers={'Authorization': f'Bearer {tenant_token}'})
    with urllib.request.urlopen(req) as resp:
        fields_result = json.loads(resp.read())

    field_map = {}
    for field in fields_result.get('data', {}).get('items', []):
        field_name = field.get('field_name', '')
        field_id = field.get('field_id', '')
        field_type = field.get('type', 0)
        field_map[field_name] = {'id': field_id, 'type': field_type}

    # 3. 构建写入字段
    fields = {}

    # ItemID - 文本字段
    if 'ItemID' in field_map:
        fields[field_map['ItemID']['id']] = item_id

    # 标题 - 文本字段
    if '标题' in field_map:
        fields[field_map['标题']['id']] = title

    # 原文URL - URL 字段
    if '原文URL' in field_map:
        fields[field_map['原文URL']['id']] = url

    # 操作类型 - 单选字段（type=3）
    if '操作类型' in field_map:
        fid = field_map['操作类型']['id']
        if field_map['操作类型']['type'] == 3:
            fields[fid] = {"text": reaction, "tag": "text"}

    # 处理状态 - 单选字段（type=3），默认写"未处理"
    if '处理状态' in field_map:
        fid = field_map['处理状态']['id']
        if field_map['处理状态']['type'] == 3:
            fields[fid] = {"text": "未处理", "tag": "text"}

    # 4. 写入新记录
    records_url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{TABLE_TOKEN}/tables/tbl5Xgf9mS93KYyb/records'
    record_payload = json.dumps({"fields": fields}).encode('utf-8')
    req = urllib.request.Request(
        records_url,
        data=record_payload,
        headers={
            'Authorization': f'Bearer {tenant_token}',
            'Content-Type': 'application/json'
        },
        method='POST'
    )
    with urllib.request.urlopen(req) as resp:
        write_result = json.loads(resp.read())

    print(f"写入结果: {write_result}")

    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': allow_origin,
            'Content-Type': 'application/json',
        },
        'body': json.dumps({
            'ok': write_result.get('code') == 0,
            'data': write_result
        }, ensure_ascii=False)
    }
