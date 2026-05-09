"""
算法模块包

此包包含Ratio类型参数计算的所有核心算法：
- calc_yoy: 同比增长率算法
- calc_cagr: 累计增长率算法
- calc_mom: 环比算法（用于fallback）
"""

from .calc_yoy import calc_by_yoy
from .calc_cagr import calc_by_cagr
from .calc_mom import calc_mom_fallback

__all__ = ['calc_by_yoy', 'calc_by_cagr', 'calc_mom_fallback']
