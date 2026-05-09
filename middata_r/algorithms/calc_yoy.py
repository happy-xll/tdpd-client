"""
YoY (Year-over-Year) 同比增长率计算核心算法

此模块实现了使用同比增长率计算排放值的核心算法。
适用于3-12月的计算（1-2月使用CAGR，见calc_cagr.py）

算法流程：
    1. 获取同比增长率参数数据
    2. 构建全量区域数据（所有区域默认值为0）
    3. 比率数据不为0的区域：使用同比计算 = base * (ratio/100 + 1)
    4. 比率为0且同期数据也为0的区域：结果直接为0
    5. 比率为0但同期数据不为0的区域：使用环比计算（MoM）作为 fallback
"""
import pandas as pd
import numpy as np

from .common import (
    get_zone_codes,
    normalize_zone,
    build_full_dataframe,
    calc_ratio_period,
)
from .calc_mom import calc_mom_fallback


def calc_by_yoy(
    # ===== 输入数据 =====
    same_period_df,
    base_df,
    # ===== 配置参数 =====
    param_note,
    group,
    year,
    month,
    # ===== 参数对象 =====
    pam_o,
    pam_r,
    # ===== 区域类型 =====
    is_nation,
    # ===== 外部依赖（需要注入）=====
    get_param_by_name_fn=None,
    load_param_value_fn=None,
    # ===== 其他参数 =====
    patch=False,
):
    """
    使用同比增长率（YoY）计算排放值

    ┌─────────────────────────────────────────────────────────────────────────────┐
    │                              算法流程图                                      │
    ├─────────────────────────────────────────────────────────────────────────────┤
    │                                                                             │
    │  1. 获取YoY增长率参数                                                        │
    │     ┌─────────────────────────────────────────────────────────────┐        │
    │     │ param_name = param_note + ('_N_yoy' if 国家级 else '_yoy')  │        │
    │     │ 例如: service + '_yoy' = 'service_yoy'                      │        │
    │     └─────────────────────────────────────────────────────────────┘        │
    │                                    ↓                                        │
    │  2. 加载YoY增长率数据                                                       │
    │     ┌─────────────────────────────────────────────────────────────┐        │
    │     │ pnr_data = load_param_value(param_name, year, month)        │        │
    │     │ 返回: 各区域的YoY增长率（如 5.5 表示同比增长5.5%）            │        │
    │     └─────────────────────────────────────────────────────────────┘        │
    │                                    ↓                                        │
    │  3. 构建全量数据                                                             │
    │     ┌─────────────────────────────────────────────────────────────┐        │
    │     │ base_full = build_full_dataframe(base_df)                  │        │
    │     │ pnr_full = build_full_dataframe(pnr_data)                  │        │
    │     │ 所有区域默认值为0，有数据的区域使用实际值                     │        │
    │     └─────────────────────────────────────────────────────────────┘        │
    │                                    ↓                                        │
    │  4. 分类计算各区域                                                           │
    │     ┌─────────────────────────────────────────────────────────────┐        │
    │     │                                                             │        │
    │     │  有YoY数据区域(v!=0)           无YoY数据区域(v==0)            │        │
    │     │        ↓                            ↓                       │        │
    │     │  使用YoY计算                    判断同期数据                  │        │
    │     │  result = base *              同期=0 → result=0             │        │
    │     │  (yoy/100+1)                   同期≠0 → 使用MoM fallback    │        │
    │     │                                                             │        │
    │     └─────────────────────────────────────────────────────────────┘        │
    │                                    ↓                                        │
    │  5. 合并所有结果并返回                                                       │
    │                                                                             │
    └─────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────────────────────┐
    │                              参数说明                                        │
    ├─────────────────────────────────────────────────────────────────────────────┤
    │                                                                             │
    │  【输入数据】                                                                │
    │  same_period_df (pd.DataFrame) - 同期数据（当年，不带_r的中间结果）          │
    │      fk_zone: 区域代码                                                       │
    │      v: 同期值                                                              │
    │                                                                             │
    │  base_df (pd.DataFrame) - 基准数据（去年同期）                               │
    │      fk_zone: 区域代码                                                       │
    │      v: 去年同期值                                                          │
    │                                                                             │
    │  【配置参数】                                                                │
    │  param_note (str) - 参数名称前缀                                             │
    │      例如: 'service' 表示服务类参数                                          │
    │                                                                             │
    │  group (int) - 参数组ID                                                     │
    │      21 - 国家级参数组                                                       │
    │      7  - 省级参数组                                                         │
    │                                                                             │
    │  year (int) - 计算年份，例如 2024                                            │
    │  month (int) - 计算月份，3-12                                               │
    │                                                                             │
    │  【参数对象】                                                                │
    │  pam_o (dict) - 原始参数对象（不带_r）                                       │
    │      pk_param: 参数ID                                                       │
    │      param_name: 参数名称                                                   │
    │                                                                             │
    │  pam_r (dict) - Ratio参数对象（带_r）                                       │
    │      pk_param: 参数ID                                                       │
    │      param_name: 参数名称                                                   │
    │                                                                             │
    │  【区域类型】                                                                │
    │  is_nation (bool) - 是否为国家级别                                          │
    │      True  - 国家级计算（使用 _N_yoy 后缀）                                 │
    │      False - 省级计算（使用 _yoy 后缀）                                     │
    │                                                                             │
    │  【外部依赖】                                                                │
    │  get_param_by_name_fn (function) - 获取参数信息的函数                       │
    │      参数: (param_name: str, group: int)                                   │
    │      返回: dict 或 None                                                     │
    │                                                                             │
    │  load_param_value_fn (function) - 加载参数值的函数                         │
    │      参数: (param_id: int, year: int, month: int, patch: bool)            │
    │      返回: pd.DataFrame (含 fk_zone, v 列)                                  │
    │                                                                             │
    │  【其他参数】                                                                │
    │  patch (bool) - 是否查询带人工订正的数据                                    │
    │      False: 查询原始数据（默认）                                            │
    │      True:  查询带人工订正的数据                                            │
    │                                                                             │
    └─────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────────────────────┐
    │                              返回值                                          │
    ├─────────────────────────────────────────────────────────────────────────────┤
    │                                                                             │
    │  pd.DataFrame - 计算结果                                                    │
    │      fk_zone: 区域代码（所有区域）                                          │
    │      v: 计算得到的排放值                                                    │
    │                                                                             │
    │  如果计算失败，返回空 DataFrame                                              │
    │                                                                             │
    └─────────────────────────────────────────────────────────────────────────────┘

    Args:
        same_period_df: 同期数据（不带_r的中间结果）
        base_df: 基准数据（去年同期）
        param_note: 参数名称前缀
        group: 参数组（Nation=21, Province=7）
        year: 计算年份
        month: 计算月份
        pam_o: 原始参数对象
        pam_r: _r参数对象
        is_nation: 是否为国家级别
        get_param_by_name_fn: 获取参数信息的函数
        load_param_value_fn: 加载参数值的函数
        patch: 是否带人工订正数据

    Returns:
        计算结果的 DataFrame（仅包含 fk_zone 和 v 列，全量区域）
    """
    # 步骤1: 构建YoY增长率参数名称
    # 国家级使用 _N_yoy 后缀，省级使用 _yoy 后缀
    suffix = '_N_yoy' if is_nation else '_yoy'
    param_name_ratio = param_note + suffix
    # 例如: 'service_N_yoy' 或 'service_yoy'

    # 步骤2: 获取YoY增长率参数对象
    if get_param_by_name_fn is None:
        raise ValueError("get_param_by_name_fn 函数未提供")
    param_ratio_obj = get_param_by_name_fn(param_name_ratio, group)
    if param_ratio_obj is None:
        print(f'{param_name_ratio} 不存在，请检查')
        return pd.DataFrame()

    # 步骤3: 加载YoY增长率数据
    if load_param_value_fn is None:
        raise ValueError("load_param_value_fn 函数未提供")
    pnr_loaded = load_param_value_fn(param_ratio_obj['pk_param'], year, month, patch)
    if not pnr_loaded.empty:
        pnr_loaded = normalize_zone(pnr_loaded)

    # 步骤4: 构建全量基准数据
    # 确保所有区域都有数据，缺失的为0
    base_df_filtered = build_full_dataframe(is_nation, base_df)

    # 步骤5: 构建全量比率数据
    pnr = build_full_dataframe(is_nation, pnr_loaded)

    # 结果收集器
    results = []

    # 步骤6: 使用比率计算有数据的区域
    # 公式: result = base * (ratio/100 + 1)
    ratio_results = calc_ratio_period(pnr, base_df_filtered)
    results.extend(ratio_results)

    # 步骤7: 对缺失比率的区域进行环比计算（MoM fallback）
    mom_results = calc_mom_fallback(
        pnr=pnr,
        same_period_df=same_period_df,
        year=year,
        month=month,
        pam_o=pam_o,
        pam_r=pam_r,
        is_nation=is_nation,
        load_param_value_fn=load_param_value_fn,
        patch=patch,
    )
    results.extend(mom_results)

    # 步骤8: 合并所有结果
    if results:
        return pd.concat(results, ignore_index=True)
    return pd.DataFrame()
