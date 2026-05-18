import json
import os
import io
import requests
import pandas as pd
import time
from configparser import ConfigParser

wolf_rbac_token = ''
wolf_user_data = None

def _get_config(section, option):
    config = ConfigParser()
    # 获取 lib_tdpd.py 所在目录，然后相对于该目录查找 config.ini
    lib_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(lib_dir, 'config.ini')
    config.read(config_path, encoding='utf8')
    return config.get(section,  option)

def authorized():
    # TODO: add wolf token get here
    global wolf_rbac_token
    global wolf_user_data  # 添加全局变量存储用户数据
    AUTH_CENTER = _get_config('TDPD_SERVICE', 'auth_server')
    AUTH_USER = _get_config('TDPD_SERVICE', 'tdpd_user')
    AUTH_PASS = _get_config('TDPD_SERVICE', 'tdpd_pass')

    if not wolf_rbac_token:
        auth_url = '{}/auth-center/login/app/login'.format(AUTH_CENTER)
        jdata = {
            "username": AUTH_USER,
            "password": AUTH_PASS,
            "appid": "tdpd"
        }

        auth_r = requests.post(auth_url, json=jdata)
        print(auth_r.text)
        dt = json.loads(auth_r.text)
        wolf_rbac_token = dt.get('data').get('token')
        wolf_user_data = dt.get('data')  # 保存完整用户数据
        print(wolf_rbac_token)
    return wolf_rbac_token


def get_user_info():
    """获取完整的登录用户信息，包括 userId"""
    global wolf_user_data
    authorized()  # 确保已登录
    return wolf_user_data


def _retry_request(request_func, url, max_retries=3, return_text=False, **kwargs):
    """
    通用的HTTP请求重试辅助函数

    Args:
        request_func: requests 方法 (requests.get/post/put/patch)
        url: 完整的 URL
        max_retries: 最大重试次数（默认 3）
        return_text: 是否返回原始文本而非解析后的 JSON（默认 False）
        **kwargs: 传递给 request_func 的其他参数

    Returns:
        dict 或 str: 根据 return_text 返回解析后的 JSON 数据或原始文本

    Raises:
        Exception: 重试失败后抛出异常
    """
    for attempt in range(max_retries):
        try:
            r = request_func(url, **kwargs)

            # 对于 GET 请求，打印响应；其他请求在调用处打印
            if request_func == requests.get:
                print(r.text)

            # 检查响应是否为空
            if not r.text or r.text.strip() == '':
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    print(f"响应为空，{wait_time}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    raise Exception(f"API 返回空响应，已重试 {max_retries} 次")

            if return_text:
                return r.text
            else:
                return json.loads(r.text)

        except json.JSONDecodeError as e:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2
                print(f"JSON 解析失败: {e}，{wait_time}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
                continue
            else:
                raise Exception(f"JSON 解析失败，已重试 {max_retries} 次: {e}")
        except requests.RequestException as e:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2
                print(f"请求失败: {e}，{wait_time}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
                continue
            else:
                raise Exception(f"请求失败，已重试 {max_retries} 次: {e}")


def authorized_post(url, data, max_retries=3):
    """
    发送 POST 请求（带鉴权），支持自动重试

    Args:
        url: 请求的 URL 路径
        data: 请求数据
        max_retries: 最大重试次数（默认 3）

    Returns:
        dict: 返回的 JSON 数据
    """
    TDPD_SERVER = _get_config('TDPD_SERVICE', 'server')
    wolf_rbac_token = authorized()
    headers = {'x-rbac-token': wolf_rbac_token}
    full_url = '{}/{}'.format(TDPD_SERVER, url)

    result = _retry_request(
        requests.post,
        full_url,
        max_retries=max_retries,
        json=data,
        headers=headers,
        timeout=60
    )
    print(result)  # 保持原有输出习惯
    return result


def authorized_patch(url, data, max_retries=3):
    """
    发送 PATCH 请求（带鉴权），支持自动重试

    Args:
        url: 请求的 URL 路径
        data: 请求数据
        max_retries: 最大重试次数（默认 3）

    Returns:
        dict: 返回的 JSON 数据
    """
    TDPD_SERVER = _get_config('TDPD_SERVICE', 'server')
    wolf_rbac_token = authorized()
    headers = {
        'x-rbac-token': wolf_rbac_token,
        'Content-Type': 'application/json'
    }
    full_url = '{}/{}'.format(TDPD_SERVER, url)
    print(f"PATCH URL: {full_url}")
    print(f"PATCH Data: {json.dumps(data, ensure_ascii=False, indent=2)}")

    result = _retry_request(
        requests.patch,
        full_url,
        max_retries=max_retries,
        json=data,
        headers=headers,
        timeout=60
    )
    print(f"Response: {result}")
    return result

def authorized_put(url, data, max_retries=3):
    """
    发送 PUT 请求（带鉴权），支持自动重试

    Args:
        url: 请求的 URL 路径
        data: 请求数据
        max_retries: 最大重试次数（默认 3）

    Returns:
        dict: 返回的 JSON 数据
    """
    TDPD_SERVER = _get_config('TDPD_SERVICE', 'server')
    wolf_rbac_token = authorized()
    headers = {
        'x-rbac-token': wolf_rbac_token,
        'Content-Type': 'application/json'
    }
    full_url = '{}/{}'.format(TDPD_SERVER, url)
    print(f"PUT URL: {full_url}")
    print(f"PUT Data: {json.dumps(data, ensure_ascii=False, indent=2)}")

    result = _retry_request(
        requests.put,
        full_url,
        max_retries=max_retries,
        json=data,
        headers=headers,
        timeout=60
    )
    print(f"Response: {result}")
    return result


def upload_param_values(df, param_name):
    """
    通过API上传参数值（使用PUT接口，支持插入和更新）

    Args:
        df: 要上传的DataFrame，必须包含以下列：
            - fk_param: 参数ID
            - fk_zone: 区域代码
            - year: 年份
            - month: 月份
            - day: 日
            - hour: 小时
            - minute: 分钟
            - v: 值
        param_name: 参数名称
    """
    import pandas as pd

    if df.empty:
        print("数据为空，跳过上传")
        return

    # 过滤掉 v=None 的记录，避免 JSON 序列化错误
    df = df[df['v'].notna()].copy()

    if df.empty:
        print("所有数据 v 值均为 None，跳过上传")
        return

    pk_param = df['fk_param'].iloc[0]

    # 转换为宽格式（区域作为列）
    dfw = df.pivot(index=['year', 'month'], columns='fk_zone', values='v').reset_index()

    # 转换为 split 格式，但不包含 index 字段
    data = {
        "columns": dfw.columns.tolist(),
        "data": dfw.values.tolist()
    }

    request_data = {
        "param_name": param_name,
        "dataes": data
    }

    try:
        url = f'v1/param/{pk_param}/values'
        result = authorized_put(url, request_data)
        print(f"上传结果: {result}")
    except Exception as e:
        print(f"上传失败: {e}")


def authorized_get(url, rtype='dict', max_retries=3):
    """
    发送 GET 请求到 TDPD API，支持自动重试

    Args:
        url: 请求 URL（相对路径）
        rtype: 返回类型 ('dict' 或 'json')
        max_retries: 最大重试次数（默认 3）

    Returns:
        根据 rtype 返回解析后的数据
    """
    TDPD_SERVER = _get_config('TDPD_SERVICE', 'server')
    wolf_rbac_token = authorized()
    headers = {'x-rbac-token': wolf_rbac_token}
    full_url = '{}/{}'.format(TDPD_SERVER, url)
    print(full_url)

    return _retry_request(
        requests.get,
        full_url,
        max_retries=max_retries,
        return_text=(rtype != 'dict'),
        headers=headers,
        timeout=30
    )

def load_sheet_data(param_id):
    djson = authorized_get('v1/param/{}/values?only_data=1'.format(param_id), 'json')
    dfn = pd.read_json(io.StringIO(djson), orient='split')
    #dfn = dfn.rename(columns={'v': 'value'})
    return dfn

def get_param_by_name( param_name, group=2, dtype=None):
    """
    根据参数名称获取参数信息

    Args:
        param_name: 参数名称
        group: 参数组ID（默认2）
        dtype: 数据类型（可选），如果指定则在查询时添加 dtype 条件

    Returns:
        dict: 包含 pk_param, param_name, time_resolution, dtype 等字段的字典
        None: 未找到参数时返回 None
    """
    # 构建查询 URL
    url = f'v1/params?group={group}&param_name={param_name}'
    if dtype is not None:
        url += f'&dtype={dtype}'

    djson = authorized_get(url, 'json')
    print(djson)
    data = json.loads(djson)

    items = data.get('items')
    if not items or len(items) == 0:
        print(f"参数 {param_name} (group={group}, dtype={dtype}) 未找到")
        return None

    print(items[0])
    return items[0]


def get_middata_group():
    """
    获取Middata参数组配置

    从配置文件中读取middata_group参数，用于计算中间结果。

    Returns:
        int: Middata参数组ID

    Raises:
        Exception: 配置读取失败时抛出异常
    """
    try:
        return int(_get_config('MIDDATA', 'middata_group'))
    except Exception as e:
        raise Exception(f"无法获取 middata_group 配置 [MIDDATA] middata_group: {e}\n"
                       f"请在 config.ini 的 [MIDDATA] 部分配置 middata_group 参数")


def get_dmf_yoy_config():
    """
    获取同比系数计算配置

    从配置文件中读取 DMF_YOY 相关参数。
    source_group 使用 middata_group 配置。

    Returns:
        dict: 包含 source_group (使用 middata_group) 和 target_group 的字典

    Raises:
        Exception: 配置获取失败时抛出异常
    """
    source_group = get_middata_group()
    try:
        target_group = int(_get_config('DMF_YOY', 'target_group'))
    except Exception as e:
        raise Exception(f"无法获取同比系数目标参数组配置 [DMF_YOY] target_group: {e}")

    return {
        'source_group': source_group,
        'target_group': target_group
    }


def get_dmf_mom_config():
    """
    获取环比系数计算配置

    从配置文件中读取 DMF_MOM 相关参数。
    source_group 使用 middata_group 配置。

    Returns:
        dict: 包含 source_group (使用 middata_group) 和 target_group 的字典

    Raises:
        Exception: 配置获取失败时抛出异常
    """
    source_group = get_middata_group()
    try:
        target_group = int(_get_config('DMF_MOM', 'target_group'))
    except Exception as e:
        raise Exception(f"无法获取环比系数目标参数组配置 [DMF_MOM] target_group: {e}")

    return {
        'source_group': source_group,
        'target_group': target_group
    }


def _authorized_get(url, params=None, max_retry=1):
    """
    发送带鉴权的 GET 请求（支持 token 过期重试）

    Args:
        url: 请求的 URL 路径
        params: 请求参数
        max_retry: 最大重试次数（token 过期时）

    Returns:
        Response 对象
    """
    TDPD_SERVER = _get_config('TDPD_SERVICE', 'server')
    headers = {
        'x-rbac-token': authorized()
    }
    full_url = '{}/{}'.format(TDPD_SERVER, url)
    r = requests.get(full_url, params=params, headers=headers)

    # token 过期，清空缓存并重试
    if r.status_code == 401 and max_retry > 0:
        print("Token 已过期，正在重新获取...")
        global wolf_rbac_token
        wolf_rbac_token = ''
        headers['x-rbac-token'] = authorized()
        r = requests.get(full_url, params=params, headers=headers)

    return r


def load_param_value_remote(param_id, year=None, month=None, patch=False, vname='v'):
    """
    从公网接口加载参数值数据（带鉴权）

    与 load_param_value 接口一致，但使用公网地址并带鉴权 token

    Args:
        param_id: 参数ID
        year: 年份（可选）
        month: 月份（可选）
        patch: 是否使用 patch 模式（可选）
        vname: 返回的值列名（可选，默认为'v'）

    Returns:
        DataFrame: 包含 fk_zone, v 等列的数据

    配置要求 (config.ini):
        [TDPD_SERVICE]
        server = 公网服务器地址
        auth_server = 鉴权服务器地址
        tdpd_user = 鉴权用户名
        tdpd_pass = 鉴权密码
    """
    params = {
        'only_data': 1,  # 接口仅仅返回数据
        'pivot': 0,
    }
    if year:
        params['year'] = year
    if month:
        params['month'] = month
    if patch:
        params['patch'] = 1

    # 请求公网接口加载数据（带鉴权）
    response = _authorized_get('v1/param/{}/values'.format(param_id), params=params)

    dfn = pd.read_json(io.StringIO(response.text), orient='split', dtype={'fk_zone':'str'})
    if vname != 'v':
        dfn = dfn.rename(columns={'v': vname})
    return dfn


def load_param_value_remote_v2(param_id, year=None, month=None, patch=False):
    """
    从公网接口加载参数值数据（带鉴权，v2版本，包含pv字段）

    与 load_param_value_remote 类似，但使用 v2 接口，返回结果包含 pv 字段。
    pv 字段用于标识数据是否被人工修改过。

    Args:
        param_id: 参数ID
        year: 年份（可选）
        month: 月份（可选）
        patch: 是否使用 patch 模式（可选）

    Returns:
        DataFrame: 包含 fk_zone, year, month, v, pv 等列的数据

    配置要求 (config.ini):
        [TDPD_SERVICE]
        server = 公网服务器地址
        auth_server = 鉴权服务器地址
        tdpd_user = 鉴权用户名
        tdpd_pass = 鉴权密码
    """
    params = {
        'only_data': 1,  # 接口仅仅返回数据
        'pivot': 0,
    }
    if year:
        params['year'] = year
    if month:
        params['month'] = month
    if patch:
        params['patch'] = 1

    # 请求公网接口加载数据（带鉴权，v2版本）
    response = _authorized_get('v2/param/{}/values'.format(param_id), params=params)

    dfn = pd.read_json(io.StringIO(response.text), orient='split', dtype={'fk_zone':'str'})
    return dfn