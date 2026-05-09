#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DMF 系数计算模块 - 环比（与上月比较）

从 tdpd-spider 移植，适配 tdpd-client 远程调用环境
"""

import os
import sys
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# 将父目录添加到导入路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib_tdpd import get_param_by_name, load_param_value_remote, upload_param_values
from config import GROUP_NATION, GROUP_PROVINCE


def cut_str(zone):
    """处理区域名称"""
    if zone == 'CHN':
        return 'total'
    if zone != 'total':
        return zone[:2]
    return zone


def tidy_df(df):
    """清理数据中的 NaN 和 Inf 值"""
    df = df.copy()
    df = df.replace(np.nan, 1)
    df = df.replace(np.inf, 1)
    df = df.replace(-np.inf, 1)
    return df


def calc_df(df_mon, df_mon_):
    """计算环比系数"""
    df_ = df_mon[['fk_zone', 'v']].join(df_mon_[['fk_zone', 'vm']].set_index(['fk_zone']), on=['fk_zone'])
    df_ = df_.rename(columns={'v': 'vo'})
    df_.dropna(subset=['vo', 'vm'], inplace=True)
    df_['v'] = df_['vo'] / df_['vm']
    df_.dropna(subset=['v'], inplace=True)
    df_ = df_.reset_index()
    return df_[['fk_zone', 'v']]


def calc_dmf_mb_factor(year, month, patch=False, middata_group=None, target_group=None):
    """
    计算环比系数（与上月比较）

    Args:
        year: 计算年份
        month: 计算月份
        patch: 是否打补丁
        middata_group: middata 源数据参数组ID (必填)
        target_group: 计算结果目标参数组ID (必填)

    Raises:
        ValueError: 当 middata_group 或 target_group 为 None 时抛出异常
    """
    if middata_group is None:
        raise ValueError("middata_group 参数不能为空，请通过命令行 --middata-group 指定或在代码中传入")
    if target_group is None:
        raise ValueError("target_group 参数不能为空，请通过命令行 --target-group 指定或在代码中传入")

    tt = datetime.strptime(f'{year}-{month}-01', '%Y-%m-%d')
    # 获取上一月的时间
    tt_mb = tt - timedelta(days=1)

    # 获取各种类型的参数
    # 尝试多个可能的配置文件路径
    possible_paths = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    'db', 'dynamicfactor-bysource.xlsx'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    '..', 'tdpd-spider', 'code', 'db', 'parav_middata', 'dynamicfactor-bysource.xlsx')
    ]

    config_file = None
    for path in possible_paths:
        if os.path.exists(path):
            config_file = path
            break

    if not config_file:
        print(f"配置文件未找到，已尝试的路径:")
        for path in possible_paths:
            print(f"  - {path}")
        return

    params = pd.read_excel(config_file, sheet_name='_Note')
    params_l = list(params['Note'])
    params_l_A01 = list(params[params['Type'] == 'A01']['Note'])
    params_l_E0101 = list(params[params['Type'] == 'E0101']['Note'])
    params_l_other = list(params[~params['Type'].isin(['A01', 'E0101'])]['Note'])

    for _, row in params.iterrows():
        pam_l = row['Note']
        pam_s = row['ID']
        pam_type = row['Type']

        print(pam_s)

        # 获取MIDDATA 参数信息
        pam_oo = get_param_by_name(pam_s, middata_group)
        if not pam_oo:
            print(f"  参数 {pam_s} 在 group={middata_group} 中不存在，跳过")
            continue

        df_mon = load_param_value_remote(pam_oo.get('pk_param'), year, month, patch)
        df_mon_ = load_param_value_remote(pam_oo.get('pk_param'), tt_mb.year, tt_mb.month, False, 'vm')

        # 没有参数跳过
        if df_mon.empty or df_mon_.empty:
            continue

        # 计算系数
        if pam_s == 'service' or pam_s == 'none' or pam_s == 'ind-valueadd':
            df = df_mon.copy()
        else:
            df = calc_df(df_mon, df_mon_)

        if pam_type == 'E0101':
            df = df[~df['fk_zone'].isin(['total'])]

        if df.empty:
            continue

        df = df.copy()
        df['year'] = year
        df['month'] = month

        df['prov'] = df.apply(lambda x: cut_str(x['fk_zone']), axis=1)
        df.pop('fk_zone')
        df = df.rename(columns={'prov': 'fk_zone'})

        dfs = tidy_df(df)

        # 获取目标参数信息
        pam_o = get_param_by_name(pam_s, target_group)
        if not pam_o:
            print(f"  目标参数 {pam_s} 在 group={target_group} 中不存在，跳过")
            continue

        dfs = dfs.copy()
        dfs['fk_param'] = pam_o.get('pk_param')
        dfs['day'] = -1
        dfs['hour'] = -1
        dfs['minute'] = -1

        # 上传结果
        if not dfs.empty:
            # 过滤掉 v=None 的记录
            dfs = dfs[dfs['v'].notna()].copy()
            if not dfs.empty:
                upload_param_values(dfs, pam_s)
                print(f"  上传完成: {len(dfs)} 条记录")


def batch_calc_range(start_ym, end_ym, middata_group=None, target_group=None, patch=False):
    """
    批量计算方法：循环计算指定时间范围内的环比系数

    Args:
        start_ym: 开始年月，格式 YYYY-MM（例如: 2013-01）
        end_ym: 结束年月，格式 YYYY-MM（例如: 2013-12）
        middata_group: middata 源数据参数组 ID（可选，默认使用配置文件）
        target_group: 计算结果目标参数组 ID（可选，默认使用配置文件）
        patch: 是否查询带人工订正的数据（默认: False）
    """
    from datetime import datetime
    from dateutil.relativedelta import relativedelta
    from lib_tdpd import get_dmf_mom_config

    # 如果未指定，从配置文件读取
    config = get_dmf_mom_config()
    if middata_group is None:
        middata_group = config['source_group']
    if target_group is None:
        target_group = config['target_group']

    # 解析年月字符串
    start = datetime.strptime(start_ym, '%Y-%m')
    end = datetime.strptime(end_ym, '%Y-%m')

    current = start

    print(f"{'='*70}")
    print(f"  批量计算环比系数")
    print(f"{'='*70}")
    print(f"  时间范围: {start_ym} ~ {end_ym}")
    print(f"  源参数组ID: {middata_group}")
    print(f"  目标参数组ID: {target_group}")
    print(f"  带人工订正: {'是' if patch else '否'}")
    print(f"{'='*70}")
    print()

    while current <= end:
        year = current.year
        month = current.month

        print(f"\n>>> 正在计算 {year}-{month:02d} ...")
        try:
            calc_dmf_mb_factor(year, month, patch, middata_group, target_group)
            print(f"    ✓ {year}-{month:02d} 完成")
        except Exception as e:
            print(f"    ✗ {year}-{month:02d} 失败: {e}")

        current += relativedelta(months=1)

    print()
    print(f"{'='*70}")
    print("  批量计算完成!")
    print(f"{'='*70}")


if __name__ == '__main__':
    import argparse

    # 从配置文件读取默认值
    from lib_tdpd import get_dmf_mom_config
    default_config = get_dmf_mom_config()

    # 命令行执行方式（不用此方式执行可把230-244行注释掉）
    parser = argparse.ArgumentParser(description='计算环比系数')
    parser.add_argument('--year', '-y', type=int, required=True, help='计算年份')
    parser.add_argument('--month', '-m', type=int, required=True, help='计算月份')
    parser.add_argument('--middata-group', '-mg', type=int,
                        default=default_config['source_group'],
                        help=f'middata源数据参数组ID (默认使用配置文件middata_group={default_config["source_group"]})')
    parser.add_argument('--target-group', '-tg', type=int,
                        default=default_config['target_group'],
                        help=f'计算结果目标参数组ID (默认: {default_config["target_group"]})')
    parser.add_argument('--patch', action='store_true',
                        help='查询结果是否带人工订正')

    args = parser.parse_args()

    calc_dmf_mb_factor(args.year, args.month, args.patch, args.middata_group, args.target_group)

    # 批量计算示例：取消下面的注释来运行批量计算
    # batch_calc_range('2026-01', '2026-03')