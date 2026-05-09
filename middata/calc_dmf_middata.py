#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Middata 计算模块

从 tdpd-spider 移植的参数计算模块
- calc_dmf_middata: 计算非 Ratio 类型参数的中间结果
"""

import os
import sys

import pandas as pd

# 将父目录添加到导入路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib_tdpd import get_param_by_name, load_param_value_remote, load_param_value_remote_v2, upload_param_values, get_middata_group
from config import GROUP_NATION, GROUP_PROVINCE

# =============================================================================
# calc_dmf_middata 的辅助函数
# =============================================================================

def calc_mgr_ratio(year, patch=False):
    """计算采购经理人指数比例"""
    param_id = get_param_by_name('CND_Industry_ManagerIndex', GROUP_PROVINCE).get('pk_param')
    df_mgr = load_param_value_remote(param_id, year, None, patch)
    df_need = df_mgr[(df_mgr['month'] == 1) | (df_mgr['month'] == 2)].copy()
    dtotal = df_need['v'].sum()
    df_need['mgri'] = df_need['v'] / dtotal
    return df_need[['year', 'month', 'mgri']]


def calc_A01(year, month, pam_s, pam_l, param_id_to, param_group=GROUP_NATION, patch=False):
    """计算 A01 类型参数"""
    pname = '{}_ct'.format(pam_l)
    param_info = get_param_by_name(pname, param_group)
    param_id = param_info.get('pk_param')
    mgr_ratio = calc_mgr_ratio(year, patch)

    if (month == 1 or month == 2):
        pname = '{}_mtd'.format(pam_l)
        pinfo = get_param_by_name(pname, param_group)
        param_id = pinfo.get('pk_param')
        df_mon = load_param_value_remote(param_id, year, 2, patch, 'pv')
        if df_mon.empty:
            return pd.DataFrame()

        df_need = df_mon[['year', 'month', 'pv']].copy()
        if month == 1:
            df_need['month'] = 1
        mgr_ratio_n = mgr_ratio[mgr_ratio.month == month]

        if pam_s == 'service':
            df_need['v'] = df_need['pv'] / 100 + 1
        else:
            df_need = df_need.merge(mgr_ratio_n.set_index(['year', 'month']), on=['year', 'month'])
            df_need['v'] = df_need['pv'] * df_need['mgri']

        df_need = df_need[['year', 'month', 'v']]
        df_need['fk_param'] = param_id_to
        df_need['fk_zone'] = 'total'
        df_need['day'] = -1
        df_need['hour'] = -1
        df_need['minute'] = -1
        return df_need[['fk_param', 'fk_zone', 'year', 'month', 'day', 'hour', 'minute', 'v']]
    else:
        df_mon = load_param_value_remote(param_id, year, month, patch)
        df_mon['fk_zone'] = 'total'
        if pam_s == 'service':
            df_mon['v'] = df_mon['v'] / 100 + 1
        if df_mon.empty:
            return pd.DataFrame()
        # 补全缺失列
        for col in ['day', 'hour', 'minute']:
            if col not in df_mon.columns:
                df_mon[col] = -1
        df_mon['fk_param'] = param_id_to

    return df_mon[['fk_param', 'fk_zone', 'year', 'month', 'day', 'hour', 'minute', 'v']]


def calc_E0101(year, month, pam_l, pam_s, param_id_to, patch=False):
    """计算 E0101 类型参数"""
    mgr_ratio = calc_mgr_ratio(year, patch)

    if month == 1 or month == 2:
        pname = '{}_mtd'.format(pam_l)
        param_id = get_param_by_name(pname, GROUP_PROVINCE).get('pk_param')
        df_mon = load_param_value_remote(param_id, year, 2, patch, 'pv')
        df_mon['pv'] = df_mon['pv'].fillna(0)

        if month == 1:
            df_mon = df_mon.copy()
            df_mon['month'] = 1

        df_mon = df_mon.join(mgr_ratio.set_index(['year', 'month']), on=['year', 'month'])

        if pam_s == 'ind-valueadd':
            mgr_r_pre = calc_mgr_ratio(year - 1, patch).rename(columns={'mgri': 'mgrip'})
            mgr_r_pre['year'] = year
            df_mon = df_mon.join(mgr_r_pre.set_index(['year', 'month']), on=['year', 'month'])
            df_mon['v'] = (df_mon['pv'] / 100 + 1) * df_mon['mgri'] / df_mon['mgrip']
        else:
            df_mon['v'] = df_mon['pv'] * df_mon['mgri']
        # 补全缺失列
        for col in ['day', 'hour', 'minute']:
            if col not in df_mon.columns:
                df_mon[col] = -1
    else:
        param_id = get_param_by_name('{}_ct'.format(pam_l), GROUP_PROVINCE).get('pk_param')
        df_mon = load_param_value_remote(param_id, year, month, patch)
        df_mon['v'] = df_mon['v'].fillna(0)
        if pam_s == 'ind-valueadd':
            df_mon['v'] = df_mon['v'] / 100 + 1
        # 补全缺失列
        for col in ['day', 'hour', 'minute']:
            if col not in df_mon.columns:
                df_mon[col] = -1

    if df_mon.empty:
        return pd.DataFrame()
    df_mon['fk_param'] = param_id_to

    return df_mon[['fk_param', 'fk_zone', 'year', 'month', 'day', 'hour', 'minute', 'v']]


def calc_construction(year, month, pam_l, param_id_to, patch=False):
    """计算建筑类型参数"""
    pname = f'{pam_l}_mtd'
    param_id = get_param_by_name(pname, GROUP_PROVINCE).get('pk_param')

    pname_n = f'{pam_l}_N_mtd'
    param_n_id = get_param_by_name(pname_n, GROUP_NATION).get('pk_param')

    if month == 1 or month == 2:
        df_mon = load_param_value_remote(param_id, year, 2, patch)
        df_mon['v'] = df_mon['v'] * 0.5
        if month == 1:
            df_mon = df_mon.copy()
            df_mon['month'] = 1
        # 补全缺失列
        for col in ['day', 'hour', 'minute']:
            if col not in df_mon.columns:
                df_mon[col] = -1

        df_mon_chn = load_param_value_remote(param_n_id, year, 2, patch)
        df_mon_chn['v'] = df_mon_chn['v'] * 0.5
        if month == 1:
            df_mon_chn = df_mon_chn.copy()
            df_mon_chn['month'] = 1
        df_mon_chn['fk_zone'] = 'total'
        # 补全缺失列
        for col in ['day', 'hour', 'minute']:
            if col not in df_mon_chn.columns:
                df_mon_chn[col] = -1
        df_mon = pd.concat([df_mon, df_mon_chn], ignore_index=True)
    else:
        pre_mon = month - 1
        df_pre = load_param_value_remote(param_id, year, pre_mon, patch, 'pv')
        # 补全缺失列（月度数据可能没有 day, hour, minute 列）
        for col in ['day', 'hour', 'minute']:
            if col not in df_pre.columns:
                df_pre[col] = -1
        df_pre = df_pre[['fk_zone', 'year', 'day', 'hour', 'minute', 'pv']].copy()

        dfm = load_param_value_remote(param_id, year, month, patch, 'nv')
        # 补全缺失列（月度数据可能没有 day, hour, minute 列）
        for col in ['day', 'hour', 'minute']:
            if col not in dfm.columns:
                dfm[col] = -1
        dfa = dfm.join(df_pre.set_index(['fk_zone', 'year', 'day', 'hour', 'minute']), on=['fk_zone', 'year', 'day', 'hour', 'minute'])
        dfa['v'] = dfa['nv'] - dfa['pv']
        dfa.loc[dfa['v'] < 0, 'v'] = 0
        df_mon = dfa

        df_chn_pre = load_param_value_remote(param_n_id, year, pre_mon, patch, 'pv')
        # 补全缺失列（月度数据可能没有 day, hour, minute 列）
        for col in ['day', 'hour', 'minute']:
            if col not in df_chn_pre.columns:
                df_chn_pre[col] = -1
        df_chn_pre = df_chn_pre[['fk_zone', 'year', 'day', 'hour', 'minute', 'pv']].copy()

        dfm_chn = load_param_value_remote(param_n_id, year, month, patch, 'nv')
        # 补全缺失列（月度数据可能没有 day, hour, minute 列）
        for col in ['day', 'hour', 'minute']:
            if col not in dfm_chn.columns:
                dfm_chn[col] = -1
        dfa_chn = dfm_chn.join(df_chn_pre.set_index(['fk_zone', 'year', 'day', 'hour', 'minute']), on=['fk_zone', 'year', 'day', 'hour', 'minute'])
        dfa_chn['v'] = dfa_chn['nv'] - dfa_chn['pv']
        dfa_chn.loc[dfa_chn['v'] < 0, 'v'] = 0
        dfa_chn['fk_zone'] = 'total'
        df_mon = pd.concat([df_mon, dfa_chn], ignore_index=True)

    df_mon['fk_param'] = param_id_to

    return df_mon[['fk_param', 'fk_zone', 'year', 'month', 'day', 'hour', 'minute', 'v']]


def calc_hdd(pam_s, year, month, param_id_to, patch=False):
    """计算 HDD 类型参数"""
    param_id = get_param_by_name('era5p_province_month', 6).get('pk_param')

    df_mon = load_param_value_remote(param_id, year, month, patch)
    df_mon = df_mon[df_mon['fk_zone'].str.contains('CHN')].copy()

    df_mon.loc[df_mon['v'] <= 291, 'v'] = round(291 - df_mon['v'])
    df_mon.loc[df_mon['v'] > 291, 'v'] = 0
    df_mon['fk_zone'] = df_mon['fk_zone'].map(lambda x: x.split('_')[1])
    # 补全缺失列
    for col in ['day', 'hour', 'minute']:
        if col not in df_mon.columns:
            df_mon[col] = -1
    df_mon['fk_param'] = param_id_to
    # 补充个total 备用
    df_total = pd.DataFrame([{
        'fk_param': param_id_to, 'fk_zone': 'total', 'year': year, 'month': month,
        'day': -1, 'hour': -1, 'minute': -1, 'v': None
    }], columns=['fk_param', 'fk_zone', 'year', 'month', 'day', 'hour', 'minute', 'v'])
    df_mon = pd.concat([df_mon, df_total], ignore_index=True)
    return df_mon[['fk_param', 'fk_zone', 'year', 'month', 'day', 'hour', 'minute', 'v']]


def calc_none(year, month, param_id_to):
    """计算 NONE 类型参数（默认值为1）"""
    df_mon = pd.DataFrame([{
        'fk_param': param_id_to, 'fk_zone': 'total', 'year': year,
        'month': month, 'day': -1, 'hour': -1, 'minute': -1, 'v': 1
    }])
    return df_mon


def calc_agric(year, month, param_name, param_group, param_id_to, patch=False):
    """计算农业类型参数"""
    param_id = get_param_by_name(param_name, param_group).get('pk_param')
    df_mon = load_param_value_remote(param_id, year, month, patch)
    if df_mon.empty:
        return pd.DataFrame()
    # 补全缺失列
    for col in ['day', 'hour', 'minute']:
        if col not in df_mon.columns:
            df_mon[col] = -1
    df_mon['fk_param'] = param_id_to
    df_mon['fk_zone'] = 'total'
    return df_mon[['fk_param', 'fk_zone', 'year', 'month', 'day', 'hour', 'minute', 'v']]


def calc_trans(year, month, pam_s, patch=False):
    """计算交通类型参数（仅拷贝）"""
    # 仅需要做copy，待交通数据抓取自动化完成后继续
    # TODO:2023 年1月和2月放到了一起，需要单独处理

    pid_from = get_param_by_name(pam_s, 3).get('pk_param')
    pid_to = get_param_by_name(pam_s, 1).get('pk_param')

    # 2023年每个省的客货运周转量依照2022年1月2月的比例进行拆分
    if year == 2023 and month in (1, 2):
        df_22 = load_param_value_remote(pid_from, 2022, 1, patch)
        df_22_2 = load_param_value_remote(pid_from, 2022, 2, patch)
        df_22 = pd.concat([df_22, df_22_2], ignore_index=True)
        dfn = df_22[['fk_zone', 'year', 'month', 'v']]
        dft = dfn.pivot(index=['fk_zone', 'year'], columns='month', values='v').reset_index()
        dft.loc[:, 'ratio1'] = dft[1] / (dft[1] + dft[2])
        dft.loc[:, 'ratio2'] = dft[2] / (dft[1] + dft[2])
        dfr = dft[['fk_zone', 'ratio1', 'ratio2']]
        df_23_2 = load_param_value_remote(pid_from, 2023, 2, patch)
        df_mon = df_23_2.join(dfr.set_index(['fk_zone']), on=['fk_zone'])
        df_mon.loc[:, 'v'] = df_mon['v'] * df_mon['ratio{}'.format(month)]
        df_mon.loc[:, 'month'] = month
    else:
        df_mon = load_param_value_remote(pid_from, year, month, patch)

    df_mon['fk_param'] = pid_to

    # 补全缺失列
    for col in ['day', 'hour', 'minute']:
        if col not in df_mon.columns:
            df_mon[col] = -1

    return df_mon[['fk_param', 'fk_zone', 'year', 'month', 'day', 'hour', 'minute', 'v']]


def calc_dmf_middata(year, month, force=False, pname=None, group=None, patch=False):
    """
    计算非 Ratio 类型参数的中间结果

    Args:
        year: 计算年份
        month: 计算月份
        force: 是否强制重新计算
        pname: 指定参数名称
        group: 参数组ID (必填)
        patch: 是否查询带人工订正的数据 (默认: False)

    Raises:
        ValueError: 当 group 为 None 时抛出异常
    """
    if group is None:
        raise ValueError("group 参数不能为空，请通过命令行 --group 指定或在代码中传入")

    config_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               'db', 'dynamicfactor-bysource.xlsx')

    if not os.path.exists(config_file):
        print(f"配置文件未找到: {config_file}")
        return

    df_params = pd.read_excel(config_file, sheet_name='_Note')
    params = df_params.to_dict(orient='records')

    for param in params:
        # 跳过 ratio 类型的参数
        if param.get('Type') == 'Ratio':
            continue

        if pname and param.get('ID') != pname:
            continue

        pam_o = get_param_by_name(param.get('ID'), group)
        if pam_o is None:
            print(f'{param.get("ID")} 不存在，请检查')
            continue

        param_id_to = pam_o.get('pk_param')

        # 交通不计算
        if param.get('ID') in ('freightturnover', 'passengerturnover'):
            continue

        print(f"正在处理: {param.get('ID')}")

        if not force:
            ppvs = load_param_value_remote(pam_o.get('pk_param'), year, month, True)
            if not ppvs.empty:
                print('  参数值已计算，请使用 --force 强制更新')
                continue

        npt = param.get('N/P')
        pt = param.get('Type')

        df = pd.DataFrame()

        if pt == 'A01' or pt == 'E0101':
            if npt == 'N' or npt == 'NP':
                if year < 2017 and param.get('ID') == 'service':
                    continue
                if year < 2019 and month == 12 and param.get('ID') == 'water_freightturnover':
                    continue
                n_code = '{}_N'.format(param.get('Note'))
                df_a01 = calc_A01(year, month, param.get('ID'), n_code, param_id_to, GROUP_NATION, patch)

            if npt == 'P' or npt == 'NP':
                df_e0101 = calc_E0101(year, month, param.get('Note'), param.get('ID'), param_id_to, patch)

            if npt == 'N':
                df = df_a01
            elif npt == 'P':
                df = df_e0101
            elif npt == 'NP':
                df = pd.concat([df_a01, df_e0101], ignore_index=True)

        elif pt == 'CONST':
            df = calc_construction(year, month, param.get('Note'), param_id_to, patch)

        elif pt == 'HDD':
            df = calc_hdd(param.get('ID'), year, month, param_id_to, patch)

        elif pt == 'NONE':
            df = calc_none(year, month, param_id_to)

        elif False and pt == 'TRANS':
            # 交通的只需要拷贝即可
            # continue
            # 交通数据源网站数据从2020年开始
            if year < 2020 and year > 2023:
                continue
            # 交通数据从23年12月开始失效
            if year == 2023 and month == 12:
                continue
            df = calc_trans(year, month, param.get('ID'), patch)
            # 交通数据缺失掠过
            if df.empty:
                continue

        elif pt == 'AGRIC':
            mp = {'MOA_SowStock_N_ct': 27, 'NAHS_HenStock_N_ct': 28}
            df = calc_agric(year, month, param.get('Note'), mp.get(param.get('Note')), param_id_to, patch)

        else:
            continue

        # 上传结果前，校验已被人工修改的数据
        if not df.empty:
            # 请求 v2 接口获取现有数据（包含 pv 字段）
            existing_df = load_param_value_remote_v2(param_id_to, year, month, True)

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

            if not df.empty:
                upload_param_values(df, param.get('ID'))
            else:
                print(f"  所有数据都被跳过，无需上传")
        else:
            print(f"  结果为空，跳过")


def batch_calc_range(start_ym, end_ym, pname=None, group=None, force=True, patch=False):
    """
    批量计算方法：循环计算指定时间范围内的数据

    Args:
        start_ym: 开始年月，格式 YYYY-MM（例如: 2013-01）
        end_ym: 结束年月，格式 YYYY-MM（例如: 2013-12）
        pname: 指定参数名称（可选）
        group: 参数组ID（可选，默认使用配置文件中的 middata_group）
        force: 是否强制重新计算（默认: True）
        patch: 是否查询带人工订正的数据（默认: False）
    """
    from datetime import datetime
    from lib_tdpd import get_middata_group
    from dateutil.relativedelta import relativedelta

    # 如果未指定 group，从配置文件读取
    if group is None:
        group = get_middata_group()

    # 解析年月字符串
    start = datetime.strptime(start_ym, '%Y-%m')
    end = datetime.strptime(end_ym, '%Y-%m')

    current = start

    print(f"{'='*70}")
    print(f"  批量计算测试")
    print(f"{'='*70}")
    print(f"  时间范围: {start_ym} ~ {end_ym}")
    print(f"  参数: {pname if pname else '全部'}")
    print(f"  参数组ID: {group}")
    print(f"  强制重新计算: {'是' if force else '否'}")
    print(f"  带人工订正: {'是' if patch else '否'}")
    print(f"{'='*70}")
    print()

    while current <= end:
        year = current.year
        month = current.month

        print(f"\n>>> 正在计算 {year}-{month:02d} ...")
        try:
            calc_dmf_middata(year, month, force=force, pname=pname, group=group, patch=patch)
            print(f"    ✓ {year}-{month:02d} 完成")
        except Exception as e:
            print(f"    ✗ {year}-{month:02d} 失败: {e}")

        current += relativedelta(months=1)

    print()
    print(f"{'='*70}")
    print("  批量计算完成!")
    print(f"{'='*70}")
    print(f"{'='*70}")


if __name__ == '__main__':
    import argparse

    # 从配置文件读取默认值
    from lib_tdpd import get_middata_group
    default_group = get_middata_group()

    # 命令行执行方式（不用此方式执行可把498-512行注释掉）
    parser = argparse.ArgumentParser(description='计算参数的中间结果')
    parser.add_argument('--year', '-y', type=int, required=True, help='计算年份')
    parser.add_argument('--month', '-m', type=int, required=True, help='计算月份')
    parser.add_argument('--force', '-f', action='store_true', help='强制重新计算')
    parser.add_argument('--param', '-p', default=None, help='指定参数名称')
    parser.add_argument('--group', '-g', type=int, default=default_group,
                        help=f'参数组ID (默认使用配置文件middata_group={default_group})')
    parser.add_argument('--patch', action='store_true',
                        help='查询结果是否带人工订正')

    args = parser.parse_args()

    print(f"使用参数组ID: {args.group}")
    print(f"带人工订正: {'是' if args.patch else '否'}")
    calc_dmf_middata(args.year, args.month, args.force, args.param, args.group, args.patch)

    # 批量计算示例：取消下面的注释来运行批量计算
    # batch_calc_range('2026-01', '2026-03')