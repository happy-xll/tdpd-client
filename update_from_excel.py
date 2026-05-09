#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
从 Excel 文件更新数据到数据库

读取 modify_template.xlsx 文件，将数据更新到 TDPD 数据库。

用法:
    python update_from_excel.py --excel /path/to/modify_template.xlsx
"""
import argparse
import sys
import os
import pandas as pd

# 将父目录添加到导入路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib_tdpd import get_user_info, get_param_by_name, get_middata_group, authorized_patch


def update_data_from_excel(excel_path):
    """
    从 Excel 文件读取数据并更新到数据库

    Args:
        excel_path: Excel 文件路径
    """
    # 读取 Excel 文件
    try:
        # 读取 modify_data sheet
        modify_df = pd.read_excel(excel_path, sheet_name='modify_data')
        print(f"读取 modify_data sheet: {len(modify_df)} 行")

        # 读取 comment sheet
        comment_df = pd.read_excel(excel_path, sheet_name='comment')
        print(f"读取 comment sheet: {len(comment_df)} 行")
    except Exception as e:
        print(f"读取 Excel 文件失败: {e}")
        return

    # 获取用户信息
    user_info = get_user_info()
    if not user_info or 'userId' not in user_info:
        print("获取用户信息失败")
        return

    user_id = str(user_info['userId'])
    print(f"用户ID: {user_id}")

    # 获取参数组
    group = get_middata_group()
    print(f"参数组: {group}")

    # 获取 comment（取最新的）
    if not comment_df.empty:
        latest_comment = comment_df.sort_values('modify_time', ascending=False).iloc[0]
        comment = str(latest_comment['comment'])
        print(f"备注: {comment}")
    else:
        comment = ""
        print("没有备注信息")

    # 按 param_name 分组处理
    param_groups = modify_df.groupby('param_name')

    for param_name, group_df in param_groups:
        print(f"\n处理参数: {param_name} ({len(group_df)} 条数据)")

        # 获取参数信息
        param_info = get_param_by_name(param_name, group)
        if not param_info:
            print(f"  参数 {param_name} 未找到，跳过")
            continue

        pk_param = param_info.get('pk_param')
        print(f"  pk_param: {pk_param}")

        # 构建数据列表
        dataes = []
        for _, row in group_df.iterrows():
            data_item = {
                "year": int(row['year']),
                "month": int(row['month']),
                "fk_zone": str(row['fk_zone']),
                "ov": float(row['ov']) if pd.notna(row['ov']) else None,
                "v": float(row['v']) if pd.notna(row['v']) else None
            }
            dataes.append(data_item)

        # 构建请求数据
        request_data = {
            "pk_param": pk_param,
            "dataes": dataes,
            "comment": comment,
            "fk_user": user_id,
            "param_name": param_name
        }

        # 发送 PATCH 请求
        try:
            url = f'v1/param/{pk_param}/values'
            result = authorized_patch(url, request_data)
            print(f"  更新结果: {result}")
        except Exception as e:
            print(f"  更新失败: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='从 Excel 文件更新数据到 TDPD 数据库',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
说明:
  此工具读取 modify_template.xlsx 文件，将数据更新到 TDPD 数据库。

  Excel 文件结构:
    - modify_data sheet: param_name, year, month, fk_zone, ov, v
    - comment sheet: modify_time, comment

示例:
  python update_from_excel.py --excel /path/to/modify_template.xlsx
        """
    )

    parser.add_argument('--excel', '-e', type=str, required=True,
                        help='Excel 文件路径')

    args = parser.parse_args()

    # 检查文件是否存在
    if not os.path.exists(args.excel):
        print(f"错误: 文件不存在: {args.excel}")
        sys.exit(1)

    print(f"{'='*70}")
    print(f"  从 Excel 更新数据到 TDPD 数据库")
    print(f"{'='*70}")
    print(f"  文件: {args.excel}")
    print(f"{'='*70}")
    print()

    try:
        update_data_from_excel(args.excel)

        print()
        print(f"{'='*70}")
        print("  更新完成!")
        print(f"{'='*70}")

    except Exception as e:
        print()
        print(f"{'='*70}")
        print(f"  更新过程中出错: {e}")
        print(f"{'='*70}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
    # update_data_from_excel('/Users/Lily/Downloads/tdpd/modify_template.xlsx')
