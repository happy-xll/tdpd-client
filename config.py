"""
配置常量模块

此模块包含计算过程中使用的配置常量。
"""

# 方法切换年份：大于该年份使用 _r 参数作为基准，否则使用原始参数
R_METHOD_SWITCH_YEAR = 2023

# 参数组ID
GROUP_NATION = 21   # 国家级参数组
GROUP_PROVINCE = 7  # 省级参数组

# 区域类型
TYPE_NATION = 'N'    # 国家级
TYPE_PROVINCE = 'P'  # 省级
TYPE_ALL = 'NP'      # 国家级+省级
