# Quant Data Fabric

面向量化研究的 Point-in-Time（PIT）金融数据平台。

## 为什么需要 PIT

回测只能使用"当时真实可获得"的信息。每条金融事实都带有三个不同的时间：

| 字段 | 含义 |
|---|---|
| `event_time` | 这条数据描述的报告期（如 2025 年报） |
| `available_time` | 市场第一次知道它的时间（如公告日） |
| `as_of_time` | 你查询时站在哪一天 |

用 `available_time <= as_of_time` 过滤，就能避免未来函数（look-ahead bias）。

举个例子：2025 年报的 `event_time` 是 2025-12-31，但 `available_time` 是 2026-04-30。
在 2026-03-01 做回测时，这条数据必须不可见。

## 架构

```
数据源（Tushare）
      │
      ▼
Connector           拉取原始数据，包装成 RawRecord
      │
      ▼
Validator（格式）    拦截字段缺失、格式错误的数据
      │
      ▼
Normalizer          把数据源字段映射为统一领域模型
      │
      ▼
Validator（业务）    拦截数值不合理的记录
      │
      ▼
Repository          写入 DuckDB，保证幂等
      │
      ▼
Pipeline            编排整条链路，输出处理结果
```

分层原则：

- **格式校验跟随数据源**：不同数据源的字段格式不同，各自校验。
- **业务校验跟随统一模型**：规范化之后的记录结构一致，规则可以全域复用。
- **Connector 返回原始数据而非领域模型**：保留原始证据，便于回溯与重新规范化。

## 数据域

| 数据域 | 数据源接口 | 领域模型 | 数据表 |
|---|---|---|---|
| 财务 | Tushare `income` | `FinancialRecord` | `financial_fact` |
| 行情 | Tushare `daily` | `PriceRecord` | `price_daily` |

## 核心设计

- **幂等**：`UNIQUE` 约束 + `ON CONFLICT DO NOTHING`，重复摄入不会产生重复数据；
  写入接口返回实际插入行数，因此流水线能区分「新增」与「重复跳过」。
- **Revision**：财务事实的唯一键为 `(symbol, metric_name, event_time, revision_id)`，
  同一报告期的不同版本可以共存，查询时按披露时间取最新可用版本。
- **PIT 查询**：以 `available_time <= as_of_time` 为闸门，支持两种模式——
  取全局最新可见值，或通过 `event_time` 精确查询指定报告期。
- **部分成功**：单条坏数据只跳过并记录，不影响整批入库，结果对象汇报
  `total / saved / skipped / failed` 与逐条错误原因。
- **依赖注入**：Connector 由外部注入数据客户端，因此全部测试可离线运行。

## 设计取舍

- **为什么用 DuckDB**：单机研究场景、零部署、列式存储，适合分析型查询；
  当数据量或并发需求上升时再考虑迁移。
- **为什么不引入 ORM**：PIT 查询需要精确控制排序、过滤与冲突处理，显式 SQL 更可控。
- **为什么保留 RawRecord**：原始数据是审计与重放的基础，规范化只做映射不做丢弃。
- **为什么不把业务校验放在数据源层**：业务规则与数据源无关，放在统一模型层只需维护一份。

## 使用示例

```python
from datetime import datetime
from src.repositories.financial import FinancialRepository

repo = FinancialRepository("data/quant_data.duckdb")

# 站在 2026-05-10：只能看到当时已披露的版本
repo.get_pit("600519.SH", "net_income", datetime(2026, 5, 10))
# -> 800 亿（2025 年报初版）

# 修正版 2026-06-15 才披露，因此 7 月查询才能看到
repo.get_pit("600519.SH", "net_income", datetime(2026, 7, 1))
# -> 780 亿（修正版覆盖初版）

# 精确查询指定报告期
repo.get_pit(
    "600519.SH",
    "net_income",
    datetime(2026, 5, 10),
    event_time=datetime(2025, 12, 31),
)
```

## 项目结构

```
src/
├── config.py          配置与密钥加载（从 .env 读取）
├── connectors/        数据接入层（Tushare 财务 / Tushare 行情 / CSV）
├── domain/            领域模型层（RawRecord / FinancialRecord / PriceRecord）
├── normalizers/       规范化层（源字段 → 统一模型）
├── validators/        校验层（格式校验 + 业务校验）
├── repositories/      存储层（DuckDB 读写 + PIT 查询）
└── pipelines/         编排层（串联链路并统计结果）
tests/                 单元测试与集成测试（无需网络）
demo.py                离线演示入口（假数据）
run_daily.py           真实行情摄入入口（需要网络与 token）
```

## 快速开始

需要 Python 3.11 及以上。

```bash
pip install -e .

# 在项目根目录创建 .env，写入你的 Tushare token（不要提交到 Git）
# TUSHARE_TOKEN=***

python demo.py          # 离线演示，使用假数据走完整链路
python run_daily.py     # 真实行情摄入，需要网络与有效 token
python -m pytest        # 运行全部测试，无需网络
```

## 测试

测试覆盖数据模型、连接器、校验器、规范化器、仓储层、PIT 查询与流水线编排。

关键测试场景包括：

- 幂等性：重复写入不产生重复数据，并正确区分「新增」与「跳过」。
- PIT 正确性：未来数据不可见；同一报告期的修正版本覆盖初版。
- 插入顺序无关：查询结果只由数据内容决定，不受写入顺序影响。
- 多报告期演进：不同报告期在同一查询时点返回正确版本。
- 边界情况：如 `high == low` 的平价交易日属于合法数据。
- 测试隔离：每个测试使用独立临时数据库，不污染项目目录。

## 已知局限

- 财务域尚未接入真实数据（Tushare `income` 接口需要 2000 积分），当前由离线假数据测试覆盖。
- `revision_id` 目前恒为 1，同一报告期的重述数据会被唯一键拦截；完整的 revision 生命周期计划在 V0.3 实现。
- 行情域目前仅支持单只股票、日频，未做批量拉取与增量调度。
- 数据规模较小，尚未进行性能优化与压力测试。

## Roadmap

| 版本 | 范围 | 状态 |
|---|---|---|
| V0.1 | 财务数据摄入、PIT 查询、幂等 | 已完成 |
| V0.2 | 真实 Tushare 接入、行情数据域、两层校验 | 已完成 |
| V0.3 | Revision 生命周期、因子计算、数据血缘 | 计划中 |