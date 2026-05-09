"""
公共辅助函数模块

此模块包含所有算法共享的辅助函数：
- get_zone_codes: 获取区域代码列表
- normalize_zone: 标准化区域名称
- build_full_dataframe: 构建全量区域数据框
- calc_ratio_period: 使用比率计算排放值
"""
import pandas as pd


# =============================================================================
# 常量定义
# =============================================================================

# 省份代码列表 - 31个省份的行政区划代码
PROVINCE_CODE = [
    110000, 120000, 130000, 140000, 150000,  # 北京、天津、河北、山西、内蒙古
    210000, 220000, 230000,  # 辽宁、吉林、黑龙江
    310000, 320000, 330000, 340000, 350000, 360000, 370000,  # 上海、江苏、浙江、安徽、福建、江西、山东
    410000, 420000, 430000, 440000, 450000, 460000,  # 河南、湖北、湖南、广东、广西、海南
    500000, 510000, 520000, 530000, 540000,  # 重庆、四川、贵州、云南、西藏
    610000, 620000, 630000, 640000, 650000  # 陕西、甘肃、青海、宁夏、新疆
]

# 国家级区域代码
CHN_CODE = ['total']


# =============================================================================
# 辅助函数
# =============================================================================

def get_zone_codes(is_nation):
    """
    获取区域代码列表

    Args:
        is_nation (bool): 是否为国家级别
            True  - 返回国家级代码 ['total']
            False - 返回省级代码列表（31个省份）

    Returns:
        list: 区域代码列表
    """
    return CHN_CODE if is_nation else [str(c) for c in PROVINCE_CODE]


def normalize_zone(df):
    """
    标准化区域名称

    将 CHN 替换为 total（仅当存在 CHN 且不存在 total 时）

    Args:
        df (pd.DataFrame): 包含 fk_zone 列的数据框

    Returns:
        pd.DataFrame: 标准化后的数据框
    """
    if 'CHN' in df['fk_zone'].values and 'total' not in df['fk_zone'].values:
        df['fk_zone'] = df['fk_zone'].replace('CHN', 'total')
    return df


def build_full_dataframe(is_nation, source_df, default_value=0):
    """
    构建全量区域数据框

    创建包含所有区域的 DataFrame，缺失的区域使用默认值填充。

    Args:
        is_nation (bool): 是否为国家级别
        source_df (pd.DataFrame): 源数据，必须包含 fk_zone 和 v 列
        default_value (float): 缺失区域的默认值，默认为 0

    Returns:
        pd.DataFrame: 全量数据框，包含所有区域的 fk_zone 和 v 列
    """
    zone_codes = get_zone_codes(is_nation)
    full_df = pd.DataFrame({'fk_zone': zone_codes, 'v': default_value})

    if source_df.empty:
        return full_df

    # 筛选对应区域的数据
    if is_nation:
        filtered_data = source_df[source_df['fk_zone'].isin(CHN_CODE)][['fk_zone', 'v']]
    else:
        filtered_data = source_df[source_df['fk_zone'].isin(zone_codes)][['fk_zone', 'v']]

    if filtered_data.empty:
        return full_df

    # 使用 merge 回填数据
    full_df = full_df.drop(columns=['v']).merge(
        filtered_data[['fk_zone', 'v']], on='fk_zone', how='left'
    ).fillna(default_value)

    return full_df


def calc_ratio_period(pnr, base_df_filtered):
    """
    使用比率计算排放值

    对于有比率数据的区域，使用公式：result = base * (ratio/100 + 1)

    Args:
        pnr (pd.DataFrame): 比率数据（全量，包含所有区域）
            - fk_zone: 区域代码
            - v: 比率值（百分比形式，如 5.5 表示 5.5%）

        base_df_filtered (pd.DataFrame): 基准数据（全量，包含所有区域）
            - fk_zone: 区域代码
            - v: 基准值

    Returns:
        list: 计算结果列表，每个元素是一个 DataFrame，包含 fk_zone 和 v 列

    计算逻辑:
        1. 筛选出 v != 0 的区域（有比率数据）
        2. 将比率转换为乘数：multiplier = ratio/100 + 1
        3. 计算：result = base * multiplier
    """
    results = []

    # pnr 有数据的区域（v != 0）- 使用比率计算
    pnr_existing = pnr[pnr['v'] != 0].copy()
    if not pnr_existing.empty:
        # 将百分比转换为乘数，例如 5.5% -> 1.055
        pnr_existing['v'] = pnr_existing['v'] * 0.01 + 1
        pnr_existing = normalize_zone(pnr_existing)
        merged = pnr_existing.merge(base_df_filtered[['fk_zone', 'v']], on='fk_zone', suffixes=('', '_base'))
        merged['v'] = merged['v'] * merged['v_base']
        merged = merged.drop(columns=['v_base'])
        results.append(merged[['fk_zone', 'v']])

    return results
