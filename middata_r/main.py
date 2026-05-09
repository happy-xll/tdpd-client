#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Middata R (Ratio类型) 计算入口
用于调用 middata_tdpd.py 中的 calc_dmf_middata_r

此模块计算Ratio类型参数（带_r后缀）。
1-2月使用累计增长率(CAGR)，3-12月使用同比增长率(YoY)。

用法:
    python main.py --year 2024 --month 3 [--force] [--param PARAM_NAME]
"""
import argparse
import sys
import os

# 将父目录添加到导入路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from middata_r.calc_dmf_middata_r import calc_dmf_middata_r
from dateutil.relativedelta import relativedelta


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
            calc_dmf_middata_r(year, month, force=force, pname=pname, group=group, patch=patch)
            print(f"    ✓ {year}-{month:02d} 完成")
        except Exception as e:
            print(f"    ✗ {year}-{month:02d} 失败: {e}")

        current += relativedelta(months=1)

    print()
    print(f"{'='*70}")
    print("  批量计算完成!")
    print(f"{'='*70}")


def main():
    parser = argparse.ArgumentParser(
        description='计算DMF middata R (Ratio类型参数)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
说明:
  此工具用于计算Ratio类型参数（以_r结尾）。

  计算方法:
    - 1-2月: 使用累计增长率(CAGR)
    - 3-12月: 使用同比增长率(YoY)

  对于缺失比率数据的省份，使用环比(MoM)作为备选方案。

  R_METHOD_SWITCH_YEAR (默认: 2023) 决定使用哪个参数作为计算基准:
    - 年份 <= 2023: 使用原始参数（不带_r）
    - 年份 > 2023: 使用_r参数

示例（注意不能覆盖已修正的数据）:
  # 计算 2024年3月 的 ratio 参数
  python main.py --year 2024 --month 3

  # 强制重新计算已有数据
  python main.py --year 2024 --month 3 --force

  # 仅计算特定参数
  python main.py --year 2024 --month 3 --param service_r

  # 计算 2024年1月 的所有 ratio 参数（使用CAGR）
  python main.py --year 2024 --month 1
        """
    )

    # 从配置文件读取默认值
    from lib_tdpd import get_middata_group
    default_group = get_middata_group()

    parser.add_argument('--year', '-y', type=int, required=True,
                        help='计算年份 (例如: 2024)')
    parser.add_argument('--month', '-m', type=int, required=True,
                        help='计算月份 (1-12)')
    parser.add_argument('--force', '-f', action='store_true',
                        help='强制重新计算，即使数据已存在')
    parser.add_argument('--param', '-p', type=str, default=None,
                        help='指定参数名称计算（必须以_r结尾，默认: 全部）')
    parser.add_argument('--group', '-g', type=int, default=default_group,
                        help=f'参数组ID (默认使用配置文件middata_group={default_group})')
    parser.add_argument('--patch', action='store_true',
                        help='查询结果是否带人工订正')

    args = parser.parse_args()

    # 验证年份和月份
    if not (2000 <= args.year <= 2100):
        print(f"错误: 无效的年份 {args.year}。必须在2000到2100之间。")
        sys.exit(1)

    if not (1 <= args.month <= 12):
        print(f"错误: 无效的月份 {args.month}。必须在1到12之间。")
        sys.exit(1)

    # 验证参数名（如果提供）
    if args.param and not args.param.endswith('_r'):
        print(f"警告: 参数 '{args.param}' 不以 '_r' 结尾")
        print("Ratio类型参数应该以 '_r' 结尾")
        sys.exit(1)

    print(f"{'='*70}")
    print(f"  Middata R (Ratio) 计算")
    print(f"{'='*70}")
    print(f"  年份:         {args.year}")
    print(f"  月份:         {args.month}")
    print(f"  指定参数:      {args.param if args.param else '全部ratio参数'}")
    print(f"  参数组ID:     {args.group}")
    print(f"  带人工订正:   {'是' if args.patch else '否'}")
    print(f"{'='*70}")
    print()

    try:
        calc_dmf_middata_r(args.year, args.month, force=args.force, pname=args.param, group=args.group, patch=args.patch)

        print()
        print(f"{'='*70}")
        print("  计算成功完成!")
        print(f"{'='*70}")

    except Exception as e:
        print()
        print(f"{'='*70}")
        print(f"  计算过程中出错: {e}")
        print(f"{'='*70}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    # 批量计算 2026-01 ~ 2026-03
    # 取消下面的注释来运行批量计算
    # batch_calc_range('2026-01', '2026-03')

    # 正常模式：使用命令行参数
    main()
