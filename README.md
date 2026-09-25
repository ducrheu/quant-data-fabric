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

因子域**不在这条链上**：`factor_daily` 由 `price_daily` 本地派生（`run_factor.py`），
写入独立的 DuckDB。上面这条链只负责把外部数据搬进来，因子是链下游的派生计算。

## 数据域

| 数据域 | 数据源接口 | 领域模型 | 数据表 |
|---|---|---|---|
| 财务 | Tushare `income` | `FinancialRecord` | `financial_fact` |
| 行情 | Tushare `daily`（按交易日全市场批量） | `PriceRecord` | `price_daily` |
| 因子 | 由 `price_daily` 本地派生 | `FactorRecord` | `factor_daily` |

因子不是外部数据源，而是行情数据的派生结果：
`mom_20d = close_t / close_{t-20} − 1`，只使用截至 `t` 的收盘价，因此不存在未来函数。

参考数据以快照文件的形式提交进 Git，保证可复现、带出处：

| 快照 | 内容 | 出处 |
|---|---|---|
| `data/universe.json` | 300 只股票池（`as_of` = 20250102，`seed` = 20250102，候选 5106 只） | Tushare `daily` |
| `data/trading_days.json` | 417 个交易日（2025-01-02 ~ 2026-09-18） | 上证指数日线 |

股票池必须从"当时真实存在的全市场"里抽样，不能拿今天的成分股回到过去回测：
否则已经退市、被剔除的股票会从样本里消失，收益被系统性高估（幸存者偏差）。

## 核心设计

- **幂等**：`UNIQUE` 约束 + `ON CONFLICT DO NOTHING`，重复摄入不会产生重复数据；
  写入接口返回实际插入行数，因此流水线能区分「新增」与「重复跳过」。
- **Revision**：财务事实的唯一键为 `(symbol, metric_name, event_time, revision_id)`。
  仓储层支持同一报告期的多个版本共存，PIT 查询按 `available_time` 取"当时可见的
  最新版本"（有测试覆盖）。
  ⚠️ 但摄入层目前恒用 `revision_id = 1`，因此真实的重述数据会被唯一键拦截、写不进去——
  revision 生命周期是 **V0.4** 的范围，见「已知局限」。
- **PIT 查询**：以 `available_time <= as_of_time` 为闸门，支持两种模式——
  取全局最新可见值，或通过 `event_time` 精确查询指定报告期。
- **部分成功**：单条坏数据只跳过并记录，不影响整批入库，结果对象汇报
  `total / saved / skipped / failed` 与逐条错误原因。
- **依赖注入**：Connector 由外部注入数据客户端，因此全部测试可离线运行。
- **参考数据快照**：股票池用固定 seed 抽样，先排序再抽（结果与输入顺序无关），
  快照记录 `as_of` 与来源；交易日历取自指数日线（`trade_cal` 在本账号档位限频不可用）。
- **按日批量摄入 + 断点恢复**：`ingest_log` 以 `(trade_date, source)` 记录 `status` 与
  `market_rows / kept / saved / skipped`；重跑时跳过已成功的交易日，失败的下次重跑，
  收尾时对账"日志说成功的天"与"价格表里实际存在的天"。
- **因子评价可测试**：rank IC、分位组合、多空价差、重叠感知的 t 值都放在
  `src/factors/evaluate.py`，是纯函数、可单测；`run_analysis.py` 只负责打印。

## 设计取舍

- **为什么用 DuckDB**：单机研究场景、零部署、列式存储，适合分析型查询；
  当数据量或并发需求上升时再考虑迁移。
- **为什么不引入 ORM**：PIT 查询需要精确控制排序、过滤与冲突处理，显式 SQL 更可控。
- **为什么保留 RawRecord**：原始数据是审计与重放的基础，规范化只做映射不做丢弃。
- **为什么不把业务校验放在数据源层**：业务规则与数据源无关，放在统一模型层只需维护一份。
- **为什么用秩相关（Spearman）而不是 Pearson**：收益分布存在极端值，秩相关只关心
  排序，不受异常点量级影响。
- **为什么研究脚本可以"看未来"**：`forward_return` 只在因子评价阶段使用；
  `src/` 下的生产管道严禁使用未来信息——这条边界就是"怎么防未来函数"的答案。

## 使用示例

```python
from datetime import datetime
from src.repositories.financial import FinancialRepository

repo = FinancialRepository("data/quant_data.duckdb")

# 站在 2026-05-10：2025 年报（available_time = 2026-04-30）已可见
repo.get_pit("600519.SH", "net_income", datetime(2026, 5, 10))
# -> 800 亿

# 站在披露前：同一份数据在 2026-03-01 还不存在
repo.get_pit("600519.SH", "net_income", datetime(2026, 3, 1))
# -> None

# 精确查询指定报告期
repo.get_pit(
    "600519.SH",
    "net_income",
    datetime(2026, 5, 10),
    event_time=datetime(2025, 12, 31),
)
```

上面两个查询就是 `demo.py` 第 [3] 段打印的内容，可离线复现。

注意：这个示例**不演示"修正版覆盖初版"**。仓储层能做到（有测试覆盖），但摄入层的
`revision_id` 恒为 1，重述数据会被唯一键拦截 —— 完整的 revision 生命周期排在 V0.4。

## 项目结构

```
src/
├── config.py          配置与密钥加载（从 .env 读取）与各数据库路径
├── connectors/        数据接入层（Tushare 财务 / Tushare 行情 / CSV）
├── domain/            领域模型层（RawRecord / FinancialRecord / PriceRecord / FactorRecord）
├── normalizers/       规范化层（源字段 → 统一模型）
├── validators/        校验层（格式校验 + 业务校验）
├── repositories/      存储层（财务 / 行情 / 因子 / 摄入日志）
├── factors/           因子层（动量因子计算 + 因子评价指标）
├── pipelines/         编排层（串联链路并统计结果）
├── trading_calendar.py 交易日历快照的读写
└── universe.py        股票池快照的读写与可复现抽样
tests/                 单元测试与集成测试（21 个文件，无需网络）
demo.py                离线演示入口：假数据走完整链路，演示 PIT 三条保证
demo_replay.py         真实库回放：只读打开本地 DuckDB，打印规模与摄入对账
run_universe.py        构建参考数据快照（股票池 + 交易日历，需要网络与 token）
run_ingest.py          按交易日摄入全市场行情（需要网络与 token，支持断点恢复）
run_daily.py           旧入口：单只股票行情摄入（仅剩旧 10 只池，待清理）
run_factor.py          从行情库计算 mom_20d 因子（本地）
run_analysis.py        因子评价研究脚本（IC / 分位组合 / 多空价差，本地）
```

## 快速开始

需要 Python 3.11 及以上。

```bash
pip install -e .

# 在项目根目录创建 .env，写入你的 Tushare token（不要提交到 Git）
# TUSHARE_TOKEN=***

python demo.py            # 离线演示：假数据、零网络，演示 PIT 三条保证

python run_universe.py    # 重建股票池与交易日历快照（需要网络与 token）
python run_ingest.py 5    # 只摄入前 5 个交易日（试跑）；不带参数则摄入全部
python run_factor.py      # 由行情库计算 mom_20d

python demo_replay.py     # 回放真实库：数据规模 + 摄入对账（需先建库）
python run_analysis.py    # 输出 IC、分位组合收益与多空价差（三种显著口径）

python -m pytest          # 运行全部测试，无需网络
```

注：`data/*.duckdb` 不进 Git，所以 `demo_replay.py` 需要先跑上面三条建库命令；
`demo.py` 不依赖任何数据，clone 下来就能跑。

## 测试

测试覆盖数据模型、连接器、校验器、规范化器、仓储层、PIT 查询、流水线编排、
股票池抽样、交易日历、因子计算与因子评价。

关键测试场景包括：

- 幂等性：重复写入不产生重复数据，并正确区分「新增」与「跳过」。
- PIT 正确性：未来数据不可见；同一报告期的多个版本按 `available_time` 返回
  "当时可见的最新版本"。
- 插入顺序无关：查询结果只由数据内容决定，不受写入顺序影响。
- 多报告期演进：不同报告期在同一查询时点返回正确版本。
- 边界情况：如 `high == low` 的平价交易日属于合法数据。
- 参考数据：股票池抽样与输入顺序无关、固定 seed 可复现；日历快照去重排序。
- 摄入日志：只把 `success` 的日子算作已完成；同一天重复记录按主键覆盖。
- 因子评价：秩相关对手算值、分位组合的分组与顺序、多空价差的符号与方向。
- 测试隔离：每个测试使用独立临时数据库，不污染项目目录。

## 已知局限

- 财务域尚未接入真实数据（Tushare `income` 接口需要 2000 积分），当前由离线假数据测试覆盖。
- `revision_id` 目前恒为 1，同一报告期的重述数据会被唯一键拦截；完整的 revision 生命周期计划在 **V0.4** 实现。
- 行情域当前为 300 只股票池、417 个交易日、约 12.4 万行；价格为**未复权**数据，
  除权除息会造成价格跳空，尚未接入复权因子。
- 行情域尚未做增量调度与性能优化：摄入靠手动重跑，逐日串行请求。
- 因子域目前只有 `mom_20d` 一个因子、一个窗口；评价未做行业/市值中性化，
  也未计交易成本。
- 退市或长期停牌的股票在最后 20 个交易日内没有前瞻收益，会被因子评价自动剔除。
- `run_daily.py` 仍指向旧的 10 只池并写死了结束日期，属于历史遗留入口。

## 因子研究结论

`mom_20d` 在当前样本上的完整结论见 [FINDINGS.md](FINDINGS.md)：
20 日动量呈**弱反转倾向**。rank IC 在两种可信口径（非重叠、Newey-West）下均显著为负，
但 Q5−Q1 多空价差在同样两种口径下都不显著，尚不足以支持"可交易策略"的结论。

## Roadmap

| 版本 | 范围 | 状态 |
|---|---|---|
| V0.1 | 财务数据摄入、PIT 查询、幂等 | 已完成（tag `v0.1`） |
| V0.2 | 真实 Tushare 接入、行情数据域、两层校验 | 已完成（tag `v0.2`） |
| V0.3 | 因子计算与评价、参考数据快照、按日批量摄入与断点恢复、离线与回放两个 demo | 已完成（tag `v0.3`） |
| V0.4 | Revision 生命周期、数据血缘 | 未开始 |
