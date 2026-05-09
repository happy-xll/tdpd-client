# TDPD Client 工具使用文档

本文档介绍 TDPD 客户端工具的使用方法，包括数据导出、数据计算和数据更新功能。

---

## 目录

1. [参数数据导出工具 (tdpd2excel.py)](#1-参数数据导出工具-tdpd2excelpy)
2. [中间数据计算工具 (middata/calc_dmf_middata.py)](#2-中间数据计算工具-middatacalc_dmf_middatapypy)
3. [中间数据比率计算工具 (middata_r/main.py)](#3-中间数据比率计算工具-middata_rmainpy)
4. [Excel 数据更新工具 (update_from_excel.py)](#4-excel-数据更新工具-update_from_excelpy)
5. [同比系数计算工具 (dmf.py)](#5-同比系数计算工具-dmfpy)
6. [环比系数计算工具 (dmf_mb.py)](#6-环比系数计算工具-dmf_mbpy)

---

## 1. 参数数据导出工具 (tdpd2excel.py)

### 功能说明

从 TDPD 服务器导出指定参数组（group）的所有参数数据到 Excel 文件，并自动添加数据质量检测功能。

### 主要特性

- 导出指定 group 的所有参数数据
- 每个参数对应 Excel 中的一个 sheet
- 自动添加 **2σ 异常值检测**
  - 红色高亮：超出 2 倍标准差的数据
  - 黄色标记：状态列显示"超出2σ"
- 支持按年份过滤数据

### 命令格式

```bash
python tdpd2excel.py [OPTIONS]
```

### 参数说明

| 参数 | 简写 | 类型 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--excel` | `-e` | string | `tdpd_param_value_by_group.xlsx` | 指定导出文件名 |
| `--group` | `-g` | int | `配置文件中的 middata_group` | 指定参数组 ID |
| `--year` | `-y` | int | `None` | 指定数据年份（可选） |

### 使用示例

```bash
# 使用默认 group（从 config.ini 的 middata_group 读取）
python tdpd2excel.py

# 导出指定 group 的所有参数（25为开发环境中间结果分组ID，1为线上环境中间结果分组ID）
python tdpd2excel.py -g 25

# 导出 2024 年的数据
python tdpd2excel.py -g 1 -y 2024

# 指定输出文件名
python tdpd2excel.py -e my_export.xlsx
```

### 输出说明

生成的 Excel 文件结构：

| Sheet 名称 | 内容 |
|------------|------|
| 参数名 1 | 该参数的完整数据 |
| 参数名 2 | 该参数的完整数据 |
| ... | ... |

每个 Sheet 的列结构：

| 列名 | 说明 |
|------|------|
| year, month, day... | 时间维度列 |
| fk_zone | 区域代码 |
| 原始数值列 | 参数值 |
| 原始数值列_状态 | 自动添加的状态列（"正常" 或 "超出2σ"） |

**条件格式说明**：
- 🔴 红色背景：超出 2σ 的数据点
- 🟡 黄色背景：状态列中的"超出2σ"标记

---

## 2. 中间数据计算工具 (middata/calc_dmf_middata.py)

### 功能说明

计算非 Ratio 类型参数的中间结果，支持多种参数类型（A01、E0101、CONST、HDD、NONE、AGRIC 等）。

### 支持的参数类型

| 类型 | 说明 | 计算方法 |
|------|------|----------|
| A01 | 基于 PMI 指数的参数 | 1-2 月使用累计数据并分配，其他月份使用当月数据 |
| E0101 | 省级排放参数 | 所有月份均结合 PMI 指数分配到各省 |
| CONST | 建筑类参数 | 使用累计数据和上月差值计算 |
| HDD | 采暖度日参数 | 基于 ERA5 温度数据计算 |
| NONE | 无数据参数 | 设置默认值为 1 |
| AGRIC | 农业类参数 | 直接使用源数据 |
| TRANS | 交通类参数 | 数据拷贝（当前未启用） |

### 命令格式

```bash
python middata/calc_dmf_middata.py [OPTIONS]
```

### 参数说明

| 参数 | 简写 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| `--year` | `-y` | int | ✅ | 计算年份 |
| `--month` | `-m` | int | ✅ | 计算月份 |
| `--force` | `-f` | flag | ❌ | 强制重新计算已有数据（已经计算过的可以覆盖，但人工订正的除外） |
| `--param` | `-p` | string | ❌ | 指定参数名称计算（不带此参数默认计算所有） |
| `--group` | `-g` | int | ❌ | 参数组 ID（默认使用配置文件 middata_group） |
| `--patch` | - | flag | ❌ | 查询结果是否带人工订正（暂时无作用，因为人工订正的数据会同时写入t_param_value和t_param_value_patch表） |

### 使用示例

```bash
# 计算 2024 年 3 月的中间数据
python middata/calc_dmf_middata.py -y 2024 -m 3

# 强制重新计算
python middata/calc_dmf_middata.py -y 2024 -m 3 --force

# 仅计算指定参数
python middata/calc_dmf_middata.py -y 2024 -m 3 -p service

# 使用人工订正数据计算
python middata/calc_dmf_middata.py -y 2024 -m 3 --patch

# 指定参数组
python middata/calc_dmf_middata.py -y 2024 -m 3 -g 25
```

### 批量计算

批量计算指定时间范围的数据，需要在代码中修改并取消注释：

```python
# 在 middata/calc_dmf_middata.py 文件末尾
if __name__ == '__main__':
    # 批量计算示例（取消下面的注释来运行）
    # batch_calc_range('2024-01', '2024-12', patch=False)
```

然后执行：
```bash
python middata/calc_dmf_middata.py
```

**批量计算参数：**
- `start_ym`: 开始年月，格式 `YYYY-MM`
- `end_ym`: 结束年月，格式 `YYYY-MM`
- `pname`: 指定参数名称（可选，默认全部）
- `group`: 参数组 ID（可选，默认使用配置文件）
- `force`: 是否强制重新计算（默认 True）
- `patch`: 是否查询带人工订正的数据（默认 False）

### 注意事项

⚠️ **重要**：计算结果不会覆盖已被人工修改的数据（通过 `pv` 字段判断）。

⚠️ **group 参数必填**：如果不通过命令行指定 `--group`，将使用配置文件中的 `middata_group` 值。

### 配置依赖

计算依赖配置文件 `db/dynamicfactor-bysource.xlsx`，须包含以下信息：

| 列名 | 说明 |
|------|------|
| ID | 参数名称 |
| Type | 参数类型（A01/E0101/CONST/HDD/NONE/AGRIC/TRANS） |
| N/P | N=国家级、P=省级、NP=全部 |
| Note | 计算参数说明 |

---

## 3. 中间数据比率计算工具 (middata_r/main.py)

### 功能说明

计算 Ratio 类型中间数据（参数名以 `_r` 结尾），根据月份自动选择计算方法。

### 计算规则

| 月份 | 计算方法 | 说明 |
|------|----------|------|
| 1-2 月 | CAGR（累计增长率） | 使用累计数据计算增长率 |
| 3-12 月 | YoY（同比增长率） | 使用同期数据计算同比增长 |

**基准数据选择**（由 `R_METHOD_SWITCH_YEAR` 控制，默认为 2023）：
- 年份 ≤ 2023：使用原始参数（不带 `_r`）作为基准
- 年份 > 2023：使用 `_r` 参数作为基准

**备选方案**：对于缺失比率数据的区域，自动使用环比（MoM）计算。

### 命令格式

```bash
python middata_r/main.py [OPTIONS]
```

### 参数说明

| 参数 | 简写 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| `--year` | `-y` | int | ✅ | 计算年份（2000-2100） |
| `--month` | `-m` | int | ✅ | 计算月份（1-12） |
| `--force` | `-f` | flag | ❌ | 强制重新计算已有数据（已经计算过的可以覆盖，但人工订正的除外） |
| `--param` | `-p` | string | ❌ | 指定参数名（须以 `_r` 结尾，不带此参数默认计算所有） |
| `--group` | `-g` | int | ❌ | 参数组 ID（默认使用配置文件 middata_group） |
| `--patch` | - | flag | ❌ | 查询结果是否带人工订正（暂时无作用，因为人工订正的数据会同时写入t_param_value和t_param_value_patch表） |

### 使用示例

```bash
# 计算 2024 年 3 月的所有 ratio 参数
python middata_r/main.py -y 2024 -m 3

# 强制重新计算
python middata_r/main.py -y 2024 -m 3 --force

# 仅计算指定参数
python middata_r/main.py -y 2024 -m 3 -p service_r

# 计算 2024 年 1 月（使用 CAGR 方法）
python middata_r/main.py -y 2024 -m 1

# 使用人工订正数据计算
python middata_r/main.py -y 2024 -m 3 --patch
```

### 批量计算

批量计算指定时间范围的 ratio 参数，需要在代码中修改并取消注释：

```python
# 在 middata_r/main.py 文件末尾
if __name__ == '__main__':
    # 批量计算示例（取消下面的注释来运行）
    # batch_calc_range('2024-01', '2024-12', patch=False)
```

然后执行：
```bash
python middata_r/main.py
```

### 注意事项

⚠️ **重要**：计算结果不会覆盖已被人工修改的数据（通过 `pv` 字段判断）。

### 配置依赖

计算依赖配置文件 `db/dynamicfactor-bysource.xlsx`，须包含以下信息：

| 列名 | 说明 |
|------|------|
| ID | 参数名称（须以 `_r` 结尾） |
| Type | 须为 `Ratio` |
| N/P | `N`=国家级、`P`=省级、`ALL`=全部 |
| Note | 计算参数说明 |

---

## 4. 中间数据更新（人工订正）工具 (update_from_excel.py)

### 功能说明

从 Excel 模板文件读取人工修正的数据，更新到 TDPD 数据库。使用 PATCH 接口，支持更新已有数据。

### 命令格式

```bash
python update_from_excel.py [OPTIONS]
```

### 参数说明

| 参数 | 简写 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| `--excel` | `-e` | string | ✅ | Excel 文件路径 |

### 使用示例

```bash
# 从 Excel 文件更新数据
python update_from_excel.py -e /path/to/modify_template.xlsx
```

### Excel 文件格式

Excel 文件须包含两个 sheet：

#### Sheet 1: `modify_data`

| 列名 | 说明 | 示例 |
|------|------|------|
| param_name | 参数名称 | `service_r` |
| year | 年份 | `2024` |
| month | 月份 | `3` |
| fk_zone | 区域代码 | `110000` |
| ov | 原始值 | `100.0` |
| v | 修正值 | `105.5` |

#### Sheet 2: `comment`

| 列名 | 说明 | 示例 |
|------|------|------|
| modify_time | 修改时间 | `2024-03-15 10:30:00` |
| comment | 备注说明 | `根据统计局数据修正` |

### 处理流程

1. 读取 Excel 文件的两个 sheet
2. 获取当前登录用户信息（从配置文件）
3. 按 `param_name` 分组处理数据
4. 对每个参数调用 PATCH 接口更新数据
5. 记录更新结果和修改历史

---

## 5. 同比系数计算工具 (dmf.py)

### 功能说明

计算同比系数（与去年同期比较），用于衡量指标的年度变化趋势。

### 计算公式

```
同比系数 = 当期值 / 去年同期值
```

**特殊处理**：
- `service`、`none`、`ind-valueadd` 参数：直接使用当期值
- `E0101` 类型参数：排除 `total` 区域

### 命令格式

```bash
python dmf.py [OPTIONS]
```

### 参数说明

| 参数 | 简写 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| `--year` | `-y` | int | ✅ | 计算年份 |
| `--month` | `-m` | int | ✅ | 计算月份 |
| `--middata-group` | `-mg` | int | ❌ | middata 源数据参数组 ID（默认使用配置文件） |
| `--target-group` | `-tg` | int | ❌ | 计算结果目标参数组 ID（默认使用配置文件） |
| `--patch` | - | flag | ❌ | 查询结果是否带人工订正（暂时无作用，因为人工订正的数据会同时写入t_param_value和t_param_value_patch表） |

### 使用示例

```bash
# 使用配置文件中的默认参数组
python dmf.py -y 2024 -m 3

# 指定源和目标参数组
python dmf.py -y 2024 -m 3 -mg 25 -tg 26

# 使用人工订正数据计算
python dmf.py -y 2024 -m 3 --patch
```

### 批量计算

批量计算指定时间范围的同比系数，需要在代码中修改并取消注释：

```python
# 在 dmf.py 文件末尾
if __name__ == '__main__':
    # 批量计算示例（取消下面的注释来运行）
    # batch_calc_range('2024-01', '2024-12', patch=False)
```

然后执行：
```bash
python dmf.py
```

### 注意事项

⚠️ **参数组必填**：`middata_group` 和 `target_group` 必须指定，可以通过命令行参数或配置文件设置。

---

## 6. 环比系数计算工具 (dmf_mb.py)

### 功能说明

计算环比系数（与上月比较），用于衡量指标的月度变化趋势。

### 计算公式

```
环比系数 = 当期值 / 上月值
```

**特殊处理**：
- `service`、`none`、`ind-valueadd` 参数：直接使用当期值
- `E0101` 类型参数：排除 `total` 区域

### 命令格式

```bash
python dmf_mb.py [OPTIONS]
```

### 参数说明

| 参数 | 简写 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| `--year` | `-y` | int | ✅ | 计算年份 |
| `--month` | `-m` | int | ✅ | 计算月份 |
| `--middata-group` | `-mg` | int | ❌ | middata 源数据参数组 ID（默认使用配置文件） |
| `--target-group` | `-tg` | int | ❌ | 计算结果目标参数组 ID（默认使用配置文件） |
| `--patch` | - | flag | ❌ | 查询结果是否带人工订正（暂时无作用，因为人工订正的数据会同时写入t_param_value和t_param_value_patch表） |

### 使用示例

```bash
# 使用配置文件中的默认参数组
python dmf_mb.py -y 2024 -m 3

# 指定源和目标参数组
python dmf_mb.py -y 2024 -m 3 -mg 25 -tg 29

# 使用人工订正数据计算
python dmf_mb.py -y 2024 -m 3 --patch
```

### 批量计算

批量计算指定时间范围的环比系数，需要在代码中修改并取消注释：

```python
# 在 dmf_mb.py 文件末尾
if __name__ == '__main__':
    # 批量计算示例（取消下面的注释来运行）
    # batch_calc_range('2024-01', '2024-12', patch=False)
```

然后执行：
```bash
python dmf_mb.py
```

### 注意事项

⚠️ **参数组必填**：`middata_group` 和 `target_group` 必须指定，可以通过命令行参数或配置文件设置。

---

## 配置文件说明

所有工具依赖 `config.ini` 配置文件，须包含以下配置：

```ini
[TDPD_SERVICE]
server = http://tdpd.makenv.com
auth_server = https://auth-center.city.makenv.com
tdpd_user = your_username
tdpd_pass = your_password

[MIDDATA]
middata_group = 25

[DMF_YOY]
target_group = 26

[DMF_MOM]
target_group = 29
```

### 配置项说明

| 配置项 | 说明 |
|--------|------|
| `server` | TDPD 服务器地址 |
| `auth_server` | 认证服务器地址 |
| `tdpd_user` | 登录用户名 |
| `tdpd_pass` | 登录密码 |
| `middata_group` | 中间数据源参数组 ID |
| `DMF_YOY.target_group` | 同比系数目标参数组 ID |
| `DMF_MOM.target_group` | 环比系数目标参数组 ID |

---

## 附录：参数组 ID

| 说明 | 线上环境Group ID | 开发环境Group ID |
|------|------|------|
| 中间数据参数组（可配置） | 1 | 25 |
| 同比系数参数组（可配置） | 2 | 26 |
| 环比系数参数组（可配置） | 30 | 29 |

---

## 故障排查

### 常见错误

1. **获取用户信息失败**
   - 检查 `config.ini` 中的用户名密码配置
   - 确认网络连接正常

2. **参数不存在**
   - 检查参数名拼写
   - 确认参数组 ID 正确

3. **group 参数为空**
   - 确保配置文件中设置了 `middata_group`
   - 或通过命令行 `--group` 参数指定

4. **middata_group/target_group 参数为空**
   - 确保配置文件中设置了相应的配置项
   - 或通过命令行参数指定

5. **数据已存在**
   - 使用 `--force` 参数强制重新计算
   - 计算工具会跳过已被人工修改的数据

6. **语法错误**
   - 确保年份范围在 2000-2100 之间
   - 确保月份范围在 1-12 之间
   - ratio 参数名须以 `_r` 结尾

---

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0 | 2024-03-15 | 初始版本 |
| 2.0 | 2024-05-09 | 更新配置文件读取方式，新增中间数据计算工具文档 |
| 2.1 | 2025-01-XX | 更新 E0101 计算方法说明，新增批量计算功能说明 |
