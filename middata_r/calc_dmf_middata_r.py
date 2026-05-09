"""
Middata R (Ratio类型参数) 计算流程控制模块

此模块负责控制Ratio类型参数的计算流程，包括：
1. 参数准备和配置读取
2. 数据加载和验证
3. 调用相应的算法（YoY/CAGR）进行计算
4. 结果上传

算法实现位于 algorithms/ 子模块中，业务人员可专注于修改算法而无需关注流程。
"""
import os
from datetime import date
import sys

# 将父目录添加到导入路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from dateutil.relativedelta import relativedelta

# 从 lib_tdpd 导入
from lib_tdpd import get_param_by_name, load_param_value_remote, load_param_value_remote_v2, upload_param_values, get_middata_group

# 导入共用的配置
from config import (
    R_METHOD_SWITCH_YEAR,
    GROUP_NATION,
    GROUP_PROVINCE,
    TYPE_NATION,
    TYPE_PROVINCE,
    TYPE_ALL,
)

# 本地导入
from .algorithms import calc_by_yoy, calc_by_cagr


def calc_dmf_middata_r(year, month, force=False, pname=None, group=None, patch=False):
    """
    计算Ratio类型参数的middata

    此函数控制Ratio类型参数（带_r后缀）的计算流程。
    计算逻辑：
    - 1-2月使用累计增长率(CAGR)
    - 3-12月使用同比增长率(YoY)

    对于缺失增长率数据的区域，使用环比(MoM)计算作为备选方案。

    Args:
        year: 计算年份 (例如: 2024)
        month: 计算月份 (1-12)
        force: 强制重新计算，即使数据已存在 (默认: False)
        pname: 指定参数名称计算 (默认: None表示全部)
        group: 参数组ID (默认: None，使用配置文件中的 middata_group)
        patch: 是否查询带人工订正的数据 (默认: False)

    处理逻辑:
        1. 从 dynamicfactor-bysource.xlsx 读取参数配置
        2. 筛选类型为'Ratio'且以'_r'结尾的参数
        3. 对每个参数:
           - 加载上一年基准数据(根据R_METHOD_SWITCH_YEAR决定是否带_r)
           - 加载当期数据(不带_r)
           - 检查是否已计算(除非force=True否则跳过)
           - 使用YoY(月份>=3)或CAGR(月份1-2)进行计算
           - 支持国家级(N)和省级(P)计算
           - 通过API上传结果
    """
    if group is None:
        raise ValueError("group 参数不能为空，请通过命令行 --group 指定或在代码中传入")
    # 获取参数配置文件路径
    config_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'db', 'dynamicfactor-bysource.xlsx')

    # 检查配置文件是否存在
    if not os.path.exists(config_file):
        print(f"配置文件未找到: {config_file}")
        print("请确保配置文件存在或更新路径。")
        return

    # 获取参数类型
    df_params = pd.read_excel(config_file, sheet_name='_Note')
    params = df_params.to_dict(orient='records')

    for param in params:
        # 如果指定了参数名，则只处理该参数
        if pname and param.get('ID') != pname:
            continue

        # 仅处理Ratio类型且以_r结尾的参数
        if param.get('Type') != 'Ratio':
            continue
        if not str(param.get('ID', '')).endswith('_r'):
            continue

        param_id_r = str(param.get('ID', ''))
        pam_r = get_param_by_name(param_id_r, group)
        if pam_r is None:
            print(f'{param_id_r} 不存在，请检查')
            continue

        param_r_id_to = pam_r.get('pk_param')
        print(f"正在处理: {param_id_r}")

        # 获取原始参数（不带_r后缀）
        base_df = pd.DataFrame()
        param_id_o = param_id_r.removesuffix('_r')
        pam_o = get_param_by_name(param_id_o, group)
        if pam_o is None:
            print(f'{param_id_o} 不存在，请检查')
            continue

        param_id_to = pam_o.get('pk_param')
        print(f"  原始参数: {param_id_o} (id={param_id_to})")
        print(f"  比率参数: {param_id_r} (id={param_r_id_to})")

        # 加载同期数据（当年，不带_r）
        same_period_df = load_param_value_remote(param_id_to, year, month, patch)

        # 加载上一年基准数据
        if year <= R_METHOD_SWITCH_YEAR:
            # 使用原始参数（不带_r）作为基准
            base_df = load_param_value_remote(param_id_to, year - 1, month, patch)
            if base_df.empty:
                print(f"  基准数据 (year={year-1}, month={month}) 为空，跳过")
                continue
        else:
            # 使用_r参数作为基准
            base_df = load_param_value_remote(param_r_id_to, year - 1, month, patch)
            if base_df.empty:
                print(f"  基准数据 (year={year-1}, month={month}) 为空，跳过")
                continue

        # 检查是否已计算
        if not force:
            pam_r_df = load_param_value_remote(pam_r.get('pk_param'), year, month, patch)
            if not pam_r_df.empty:
                print('  参数值已计算，请使用 --force 强制更新')
                continue

        # 获取计算参数
        param_note = param.get('Note')
        nation_prov = param.get('N/P')

        # 判断区域类型
        is_nation = (nation_prov == TYPE_NATION)
        is_province = (nation_prov == TYPE_PROVINCE)
        is_all = (nation_prov == TYPE_ALL)

        if not (is_nation or is_province or is_all):
            print('  参数值错误')
            continue

        df = pd.DataFrame()

        # 根据月份和类型进行计算
        if is_nation or is_all:
            print(f"  正在计算国家级...")
            if month >= 3:
                # 月份>=3使用YoY
                merged = calc_by_yoy(
                    same_period_df=same_period_df,
                    base_df=base_df,
                    param_note=param_note,
                    group=GROUP_NATION,
                    year=year,
                    month=month,
                    pam_o=pam_o,
                    pam_r=pam_r,
                    is_nation=True,
                    get_param_by_name_fn=get_param_by_name,
                    load_param_value_fn=load_param_value_remote,
                    patch=patch,
                )
                if not merged.empty:
                    df = pd.concat([df, merged], ignore_index=True)
            else:
                # 月份1-2使用CAGR
                merged = calc_by_cagr(
                    same_period_df=same_period_df,
                    base_df=base_df,
                    param_note=param_note,
                    group=GROUP_NATION,
                    year=year,
                    month=month,
                    pam_o=pam_o,
                    pam_r=pam_r,
                    is_nation=True,
                    get_param_by_name_fn=get_param_by_name,
                    load_param_value_fn=load_param_value_remote,
                    patch=patch,
                )
                if not merged.empty:
                    df = pd.concat([df, merged], ignore_index=True)

        if is_province or is_all:
            print(f"  正在计算省级...")
            if month >= 3:
                # 月份>=3使用YoY
                merged = calc_by_yoy(
                    same_period_df=same_period_df,
                    base_df=base_df,
                    param_note=param_note,
                    group=GROUP_PROVINCE,
                    year=year,
                    month=month,
                    pam_o=pam_o,
                    pam_r=pam_r,
                    is_nation=False,
                    get_param_by_name_fn=get_param_by_name,
                    load_param_value_fn=load_param_value_remote,
                    patch=patch,
                )
                if not merged.empty:
                    df = pd.concat([df, merged], ignore_index=True)
            else:
                # 月份1-2使用CAGR
                merged = calc_by_cagr(
                    same_period_df=same_period_df,
                    base_df=base_df,
                    param_note=param_note,
                    group=GROUP_PROVINCE,
                    year=year,
                    month=month,
                    pam_o=pam_o,
                    pam_r=pam_r,
                    is_nation=False,
                    get_param_by_name_fn=get_param_by_name,
                    load_param_value_fn=load_param_value_remote,
                    patch=patch,
                )
                if not merged.empty:
                    df = pd.concat([df, merged], ignore_index=True)

        # 准备输出DataFrame
        df['fk_param'] = param_r_id_to
        df['year'] = year
        df['month'] = month
        df['day'] = -1
        df['hour'] = -1
        df['minute'] = -1
        print(f"  结果: {len(df)} 行")

        # 通过API上传结果前，筛选掉已被人工修改的数据
        if not df.empty:
            # 请求 v2 接口获取现有数据（包含 pv 字段）
            existing_df = load_param_value_remote_v2(param_r_id_to, year, month, True)

            # 筛选掉已被人工修改的数据（pv 不为空的记录）
            if not existing_df.empty and 'pv' in existing_df.columns:
                # 获取已被人工修改的记录（pv 不为 null）
                modified_records = existing_df[existing_df['pv'].notna()][['fk_zone', 'year', 'month', 'v', 'pv']]
                print(f"  已被人工修改的记录数: {len(modified_records)}")

                if not modified_records.empty:
                    print(f"  人工修正结果:")
                    for _, row in modified_records.iterrows():
                        print(f"    fk_zone={row['fk_zone']}, year={row['year']}, month={row['month']}, v={row['v']}, pv={row['pv']}")

                # 从结果中排除已被修改的记录
                df_filtered = df.merge(
                    modified_records[['fk_zone', 'year', 'month']],
                    on=['fk_zone', 'year', 'month'],
                    how='left',
                    indicator=True
                )
                df_filtered = df_filtered[df_filtered['_merge'] == 'left_only']
                df_filtered = df_filtered.drop(columns=['_merge'])

                skipped_count = len(df) - len(df_filtered)
                if skipped_count > 0:
                    print(f"  跳过 {skipped_count} 条已被人工修改的记录")

                df = df_filtered

            upload_param_values(df, param_id_r)
        else:
            print("  结果为空，跳过上传")
