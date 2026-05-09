"""
MoM (Month-over-Month) 环比计算核心算法

此模块实现了环比计算的算法，用于处理缺失增长率的区域。

当某个区域缺少YoY或CAGR增长率数据时，使用环比计算作为fallback方案：
    ratio = (去年同月 / 去年上月)
    result = 今月上月 * ratio

计算公式：
    ratio = last_year_same_month / last_year_last_month
    result = last_month * ratio

此计算需要以下历史数据：
    1. 当月上月数据 (last_month)
    2. 去年同月数据 (last_year_same_month)
    3. 去年上月数据 (last_year_last_month)
"""
import pandas as pd
import numpy as np
from datetime import date
from dateutil.relativedelta import relativedelta

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import R_METHOD_SWITCH_YEAR
from .common import (
    get_zone_codes,
    normalize_zone,
    build_full_dataframe,
)


def calc_mom_fallback(
    # ===== 输入数据 =====
    pnr,
    same_period_df,
    # ===== 配置参数 =====
    year,
    month,
    # ===== 参数对象 =====
    pam_o,
    pam_r,
    # ===== 区域类型 =====
    is_nation,
    # ===== 外部依赖（需要注入）=====
    load_param_value_fn=None,
    # ===== 其他参数 =====
    patch=False,
):
    """
    对缺失比率的区域进行环比计算（MoM fallback）

    ┌─────────────────────────────────────────────────────────────────────────────┐
    │                              算法流程图                                      │
    ├─────────────────────────────────────────────────────────────────────────────┤
    │                                                                             │
    │  前提: 某些区域的YoY/CAGR增长率数据缺失（v==0）                              │
    │                                                                             │
    │  1. 找出需要环比计算的区域                                                   │
    │     ┌─────────────────────────────────────────────────────────────┐        │
    │     │ missing_zones = {区域 | pnr[区域].v == 0}                  │        │
    │     └─────────────────────────────────────────────────────────────┘        │
    │                                    ↓                                        │
    │  2. 检查同期数据                                                             │
    │     ┌─────────────────────────────────────────────────────────────┐        │
    │     │ IF 同期数据为0:                                              │        │
    │     │    result = 0  （直接设为0）                                 │        │
    │     │ ELSE:                                                        │        │
    │     │    进行环比计算 ↓                                            │        │
    │     └─────────────────────────────────────────────────────────────┘        │
    │                                    ↓                                        │
    │  3. 计算环比所需的时间点                                                     │
    │     ┌─────────────────────────────────────────────────────────────┐        │
    │     │ last_month       = year/month - 1个月                         │        │
    │     │ last_year_same   = year/month - 1年                          │        │
    │     │ last_year_prev   = year/month - 1年 - 1个月                  │        │
    │     │                                                             │        │
    │     │ 例如: 计算 2024年3月                                         │        │
    │     │   last_month       = 2024年2月                               │        │
    │     │   last_year_same   = 2023年3月                               │        │
    │     │   last_year_prev   = 2023年2月                               │        │
    │     └─────────────────────────────────────────────────────────────┘        │
    │                                    ↓                                        │
    │  4. 加载历史数据                                                             │
    │     ┌─────────────────────────────────────────────────────────────┐        │
    │     │ base_param_id 选择:                                         │        │
    │     │   IF year > 2023: 使用 _r 参数                              │        │
    │     │   ELSE: 使用原始参数                                         │        │
    │     │                                                             │        │
    │     │ data_last_month     = load(base_id, last_month)             │        │
    │     │ data_last_year_same = load(original_id, last_year_same)     │        │
    │     │ data_last_year_prev = load(original_id, last_year_prev)     │        │
    │     └─────────────────────────────────────────────────────────────┘        │
    │                                    ↓                                        │
    │  5. 计算环比比率                                                             │
    │     ┌─────────────────────────────────────────────────────────────┐        │
    │     │ ratio[区域] = data_last_year_same / data_last_year_prev    │        │
    │     │                                                             │        │
    │     │ 特殊处理:                                                    │        │
    │     │   IF 分母=0 且 分子=0: ratio = 0                            │        │
    │     │   IF 分母=0:           ratio = 1                            │        │
    │     │   ELSE:               ratio = 分子/分母                      │        │
    │     └─────────────────────────────────────────────────────────────┘        │
    │                                    ↓                                        │
    │  6. 计算最终结果                                                             │
    │     ┌─────────────────────────────────────────────────────────────┐        │
    │     │ result[区域] = data_last_month * ratio                      │        │
    │     └─────────────────────────────────────────────────────────────┘        │
    │                                    ↓                                        │
    │  7. 返回计算结果                                                             │
    │                                                                             │
    └─────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────────────────────┐
    │                              参数说明                                        │
    ├─────────────────────────────────────────────────────────────────────────────┤
    │                                                                             │
    │  【输入数据】                                                                │
    │  pnr (pd.DataFrame) - 比率数据（全量）                                        │
    │      fk_zone: 区域代码                                                       │
    │      v: 比率值（为0的区域需要fallback）                                     │
    │                                                                             │
    │  same_period_df (pd.DataFrame) - 同期数据（当年）                           │
    │      fk_zone: 区域代码                                                       │
    │      v: 同期值                                                              │
    │                                                                             │
    │  【配置参数】                                                                │
    │  year (int) - 计算年份，例如 2024                                            │
    │  month (int) - 计算月份，1-12                                               │
    │                                                                             │
    │  【参数对象】                                                                │
    │  pam_o (dict) - 原始参数对象（不带_r）                                       │
    │      pk_param: 参数ID                                                       │
    │                                                                             │
    │  pam_r (dict) - Ratio参数对象（带_r）                                       │
    │      pk_param: 参数ID                                                       │
    │                                                                             │
    │  【区域类型】                                                                │
    │  is_nation (bool) - 是否为国家级别                                          │
    │                                                                             │
    │  【外部依赖】                                                                │
    │  load_param_value_fn (function) - 加载参数值的函数                         │
    │      参数: (param_id: int, year: int, month: int, patch: bool)            │
    │      返回: pd.DataFrame (含 fk_zone, v 列)                                  │
    │                                                                             │
    │  【其他参数】                                                                │
    │  patch (bool) - 是否查询带人工订正的数据（默认: False）                     │
    │                                                                             │
    └─────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────────────────────┐
    │                              返回值                                          │
    ├─────────────────────────────────────────────────────────────────────────────┤
    │                                                                             │
    │  list - 计算结果列表，每个元素是一个 DataFrame                                │
    │        fk_zone: 区域代码                                                    │
    │        v: 计算得到的排放值                                                  │
    │                                                                             │
    │  如果没有需要处理的区域，返回空列表                                          │
    │                                                                             │
    └─────────────────────────────────────────────────────────────────────────────┘

    Args:
        pnr: 比率数据（全量）
        same_period_df: 同期数据
        year: 计算年份
        month: 计算月份
        pam_o: 原始参数对象
        pam_r: _r参数对象
        is_nation: 是否为国家级别
        load_param_value_fn: 加载参数值的函数
        patch: 是否查询带人工订正的数据

    Returns:
        计算结果列表（每个元素是一个 DataFrame）
    """
    results = []

    # 步骤1: 找出比率为0的区域（需要fallback的区域）
    pnr_zero_zones = set(pnr[pnr['v'] == 0]['fk_zone'].unique())

    if len(pnr_zero_zones) == 0:
        return results

    # 步骤2: 对同期数据进行补全操作
    same_period_full = build_full_dataframe(is_nation, same_period_df)

    # 步骤3: 找出 pnr=0 且 same_period_df=0 的区域，结果直接为0
    same_period_zero = set(same_period_full[same_period_full['v'] == 0]['fk_zone'].unique())
    direct_zero_zones = pnr_zero_zones & same_period_zero
    if direct_zero_zones:
        zeros_df = pd.DataFrame({
            'fk_zone': list(direct_zero_zones),
            'v': 0
        })
        results.append(zeros_df)
        print(f"    {len(direct_zero_zones)} 个区域同期数据为0，结果设为0")

    # 步骤4: 剩下的需要环比计算的省份
    # （pnr=0 但 same_period_df!=0 的区域）
    mom_zones = pnr_zero_zones - direct_zero_zones

    if len(mom_zones) == 0:
        return results

    print(f"    {len(mom_zones)} 个区域缺失比率数据，使用环比(MoM)计算")

    # 步骤5: 计算环比计算所需的时间点
    dt = date(year, month, 1)
    last_month_dt = dt - relativedelta(months=1)          # 上月
    last_year_dt = dt - relativedelta(years=1)           # 去年同月
    last_months_dt = last_month_dt - relativedelta(years=1)  # 去年上月

    # 步骤6: 加载环比计算所需数据
    # 基准参数ID的选择：根据R_METHOD_SWITCH_YEAR决定
    base_id = pam_r['pk_param'] if year > R_METHOD_SWITCH_YEAR else pam_o['pk_param']

    if load_param_value_fn is None:
        raise ValueError("load_param_value_fn 函数未提供")

    # 加载三个时间点的数据
    last_month_loaded = load_param_value_fn(base_id, last_month_dt.year, last_month_dt.month, patch)
    last_year_loaded = load_param_value_fn(pam_o['pk_param'], last_year_dt.year, last_year_dt.month, patch)
    last_years_loaded = load_param_value_fn(pam_o['pk_param'], last_months_dt.year, last_months_dt.month, patch)

    # 步骤7: 构建全量 DataFrame
    last_month_df = build_full_dataframe(is_nation, last_month_loaded)
    last_year_df = build_full_dataframe(is_nation, last_year_loaded)
    last_years_df = build_full_dataframe(is_nation, last_years_loaded)

    # 步骤8: 筛选出需要环比计算的省份数据
    last_month_df = last_month_df[last_month_df['fk_zone'].isin(mom_zones)]
    last_year_df = last_year_df[last_year_df['fk_zone'].isin(mom_zones)]
    last_years_df = last_years_df[last_years_df['fk_zone'].isin(mom_zones)]

    # 步骤9: 计算环比比率
    # ratio = last_year_same_month / last_year_last_month
    ratio_df = last_year_df[['fk_zone', 'v']].merge(
        last_years_df[['fk_zone', 'v']], on='fk_zone', suffixes=('_num', '_den'))

    # 处理分母为0的情况
    ratio_df['ratio'] = np.where(
        (ratio_df['v_num'] == 0) & (ratio_df['v_den'] == 0), 0,  # 分子分母都为0
        np.where(ratio_df['v_den'] == 0, 1, ratio_df['v_num'] / ratio_df['v_den'])  # 分母为0
    )

    # 步骤10: 计算最终结果
    # result = last_month * ratio
    merged = last_month_df.merge(ratio_df[['fk_zone', 'ratio']], on='fk_zone')
    merged['v'] = merged['v'] * merged['ratio']
    merged = merged.drop(columns=['ratio'])
    merged = normalize_zone(merged)
    results.append(merged[['fk_zone', 'v']])

    return results
