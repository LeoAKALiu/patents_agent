# Golden-set 评测体系与工程化设计

## 目的

当前 structured generation（Component 1）已经解决「脏内容结构性进不来」的问题——LLM 按 schema 输出，正文由代码确定性渲染。但没有回答「生成的东西到底好不好」。

本设计建立一套 golden-set 驱动的评测体系：以已通过实质审查的 CNIPA 授权专利作为真值，对每次生成结果做确定性评分（零 API 成本）+ LLM-as-Judge 双盲评分（可选，有 API 成本），并把确定性部分集成到 CI 门禁，实现「每次改生成器都能看到质量变化」。

本设计是 `2026-06-08-anti-contamination-structured-generation-design.md` 的后续迭代，沿用其结构化输出（`ClaimsOutput` / `DescriptionOutput` / `DrawingsOutput`）与确定性渲染管线，不推翻已落地成果。

## 已确认范围

本版做（4 件）：

1. **Golden-set 采集**：从 CNIPA 已授权专利中选取 20 篇，覆盖 4 个技术领域，格式化为标准 JSON，免人工审校。
2. **确定性评分器**：结构对齐度 (SAS) + 信息覆盖度 (CCS) + 增强结构化校验，零 API 成本，可本地跑。
3. **LLM-as-Judge 双盲评分**：4 个 CNIPA 维度 × 20 篇专利，独立模型独立 API key，每周/发布前手动触发。
4. **CI 集成**：确定性评测 → PR 门禁；LLM-Judge → `workflow_dispatch` 手动触发。

本版不做：

- 不引入生成质量评测集以外的标的（如客体问题检测、多国适配、护城河深度分析）。
- 不修改 Generator 公开 API 或生成管线。
- 不新建前端路由或评测专用页面（仅最小化卡片）。
- 不建立 golden-set 的自动化抓取 + 持续更新（v1 为手工采集，后续迭代）。

## 核心思路

### 为什么授权专利可以不做人工审校

授权专利文本已经过实质审查，天然满足 CNIPA 的**清楚**（专利法第 26 条第 4 款）、**支持**（实施细则第 20 条第 2 款）、**新颖性**要求。用它做 golden-set 不需要专利代理师逐篇审校——生成物与原授权文本的结构化差异就是真实的质量信号。

评测指标不是「生成物与原授权文本一致」，而是：
- **结构对齐度**：claims 数量/层级/依赖关系是否合理
- **信息覆盖度**：生成物是否遗漏输入中的关键技术特征
- **污染检出**：结构化字段中是否混入 AI 开场白 / meta / 样板

### 评测流水线

```
golden_set/v1/{patent_id}.json × 20
         │
         ├── 从 input 构造 InventionBrief + PatentChunk
         │
         ▼
    Generator.generate() → DraftPackage
         │
         ├── ① 结构化校验门禁（已有 + 增强，零成本）
         ├── ② 结构对齐度 SAS（确定性，零成本）
         ├── ③ 信息覆盖度 CCS（确定性，零成本）
         └── ④ LLM-as-Judge 双盲评分（可选，有 API 成本）
         │
         ▼
    eval_report.json（含 per_patent 明细 + summary + 与前次 diff）
```

## Golden-set 数据格式

### 筛选标准

- 授权公告日在 2020-2025 年
- 覆盖四个技术领域：
  - AI 软件方法：8 篇
  - 机械结构：4 篇
  - 电学电路：4 篇
  - 化学工艺：4 篇
- 权利要求数在 6-20 之间（避免过简或过繁）
- 优先选有独立方法 + 系统权利要求的专利（匹配本系统的生成范式）
- 来源：国家知识产权局专利公布公告（epub.cnipa.gov.cn）或 Google Patents CN 子集

### 单篇 schema

每篇存储为 `golden_set/v1/{patent_id}.json`：

```json
{
  "id": "CN123456789B",
  "title": "一种图像缺陷识别方法及系统",
  "technical_field": "ai_software",
  "publication_date": "2023-06-15",
  "claims_count": 8,
  "input": {
    "description_full": "技术领域\n本发明涉及人工智能检测技术领域...\n背景技术\n...\n发明内容\n...\n具体实施方式\n...",
    "drawings_description": "图1为方法流程图。\n图2为系统结构图。"
  },
  "ground_truth": {
    "claims": [
      {
        "number": 1,
        "kind": "independent",
        "category": "method",
        "depends_on": null,
        "preamble": "一种图像缺陷识别方法，其特征在于，包括：",
        "features": ["采集待检测图像", "通过神经网络模型提取特征", "输出缺陷位置"]
      }
    ],
    "description_sections": {
      "technical_field": "本发明涉及人工智能检测技术领域...",
      "background": "现有技术中...",
      "summary": "本发明提供一种...",
      "embodiments": "下面结合附图对本发明的具体实施方式进行描述..."
    },
    "figures": [
      {"figure_no": "图1", "title": "方法流程图"},
      {"figure_no": "图2", "title": "系统结构图"}
    ]
  }
}
```

### manifest 索引

`golden_set/v1/manifest.json`：

```json
{
  "version": "v1",
  "created": "2026-06-08",
  "entries": [
    {"id": "CN123456789B", "title": "...", "technical_field": "ai_software", "claims_count": 8},
    ...
  ]
}
```

### 构造 InventionBrief 的规则

评测器从 golden-set JSON 的 `input` 构造 `InventionBrief`：

| InventionBrief 字段 | 来源 |
|---|---|
| `title` | golden_set 的 `title` |
| `technical_field` | 按 `technical_field` 映射到中文标签（`{"ai_software": "人工智能软件方法", ...}`） |
| `technical_problem` | 从 `input.description_full` 的「背景技术」段首句截取 80 字；段定位按章节标题正则 `背景技术|技术背景` 匹配 |
| `technical_solution` | 从 `input.description_full` 的「发明内容」段截取前 500 字；段定位按章节标题正则 `发明内容|技术方案` 匹配 |
| `beneficial_effects` | 从 `input.description_full` 中解析与效果/效率/准确率相关的句子（含「提高」「降低」「提升」「减少」「避免」「实现」且非空，最多 3 条） |
| `key_steps` | 按动词关键词（采集/获取/解析/训练/检索/生成/输出/审核/导出）从 `input.description_full` 中提取 |

`PatentChunk` 上下文传空列表（评测不依赖 RAG）。

## 评分维度

### ① 结构化校验门禁（fast-fail）

在已有 JSON schema 校验之上，加入三个增强规则：

| 规则 | 判定 | 级别 |
|---|---|---|
| claims 至少 1 条 `kind=independent` | 不通过 → 该专利评测失败 | **阻断** |
| 每条 independent claim 的 `features` 数量 ≥ 2 | 不通过 → 警告 | 警告 |
| 说明书四段均非空（非空定义：≥ 20 字符） | 不通过 → 警告 | 警告 |
| 摘要 ≤ 300 字（已有规则） | 不通过 → 警告 | 警告 |

### ② 结构对齐度（Structure Alignment Score, SAS）

0-1 区间，确定性计算，零 API 成本。

| 子指标 | 计算方法 | 权重 |
|---|---|---|
| Claims 数量对齐 | `min(gold_n, gen_n) / max(gold_n, gen_n)` | 0.3 |
| 独立权项占比对齐 | `1 - abs(gen_independent_ratio - gold_independent_ratio)` | 0.25 |
| Claim 类别覆盖 | `len(gen_categories ∩ gold_categories) / len(gold_categories)` | 0.25 |
| 说明书章节完整性 | 四段均非空的加权分（4/4 = 1.0, 3/4 = 0.75, ...） | 0.2 |

```
SAS = 0.3 × claims_count_align
    + 0.25 × independent_ratio_align
    + 0.25 × category_coverage
    + 0.2 × section_completeness
```

### ③ 信息覆盖度（Content Coverage Score, CCS）

0-1 区间，确定性计算，零 API 成本。

| 子指标 | 计算方法 | 权重 |
|---|---|---|
| 关键名词召回 | gold claims features 中提取的名词（≥ 2 字、去重）在 gen claims features + gen description 中的命中率 | 0.6 |
| 主题词保持 | gold title + summary 中的主题词（取前 5 个 TF-IDF 或频率最高的关键词）在 gen description 中的命中率 | 0.4 |

```
CCS = 0.6 × key_noun_recall + 0.4 × topic_term_recall
```

### ④ LLM-as-Judge 双盲评分

每个维度 1-5 分，有 API 成本，可选触发。

| 维度 | 审查指南锚点 | 评分焦点 | 对比基线 |
|---|---|---|---|
| 清楚（Clarity） | 专利法第 26 条第 4 款 | 权项边界清晰、特征无歧义、步骤顺序明确 | 授权权项 |
| 支持（Support） | 实施细则第 20 条第 2 款 | 每个权项特征在说明书中有对应实施例 | 授权说明书 |
| 技术效果（Effect） | 审查指南第二部分第四章 | beneficial_effects 具体、不与区别特征脱钩 | 授权技术效果段 |
| 清洁度（Cleanliness） | 本系统独有维度 | 无 AI 开场白、meta、样板、内部会审痕迹 | 授权文本零 AI 痕迹 |

#### Judge prompt 结构

```
System:
  你是 CNIPA 发明专利实质审查员，熟悉审查指南。
  请对以下两段专利文本进行双盲对比评分，你不知道哪段是生成文本、哪段是授权文本。

  【审查指南相关条文】
  {dimension_guideline_excerpt}

  【技术领域关键词】
  {domain_keywords}

  评分标准：5 = 与授权文本质量相当，1 = 存在严重缺陷。
  只输出 JSON：{"score_a": N, "score_b": N, "reason_a": "...", "reason_b": "..."}

User:
  【文本 A】{shuffled_text_a}
  【文本 B】{shuffled_text_b}
  【评分维度】{dimension}
```

#### 双盲与独立调用

- 两条文本 shuffle 后标注为 A/B，Judge 分别打分，评测器解开映射后只取生成文本侧的得分
- 4 个维度分 4 次独立模型调用，每次不看其他维度的结果，避免交叉污染
- Judge 模型与生成模型分离：生成用 DeepSeek → Judge 用 Claude 或 GPT-4o；不同模型家族降低「自己评自己」的 bias
- Judge API key 独立配置（`EVAL_LLM_API_KEY` 环境变量）

#### 总调用量

20 篇 × 4 维度 = 80 次 LLM 调用。按 Claude Haiku $0.25/M input tokens、$1.25/M output tokens 估算，每调用约 3000 tokens（system + user prompt + response），总成本约 $0.50-1.00/次全量评测。

## 数据模型变更

### 新增（`backend/app/schemas.py`）

```python
class EvalPatentResult(BaseModel):
    patent_id: str
    title: str
    technical_field: str
    gate_pass: bool
    gate_warnings: list[str] = Field(default_factory=list)
    sas: float  # 0-1
    sas_detail: dict[str, float]
    ccs: float  # 0-1
    ccs_detail: dict[str, float]
    llm_judge: dict[str, float | None] | None = None  # {"clarity": 4.0, "support": 3.5, ...} 仅当 Judge 运行时填充


class GoldenEvalReport(BaseModel):
    run_id: str
    commit: str
    golden_set_version: str
    timestamp: datetime
    summary: GoldenEvalSummary
    per_patent: list[EvalPatentResult]
    diff_from_previous: dict[str, Any] | None = None


class GoldenEvalSummary(BaseModel):
    sas_avg: float
    ccs_avg: float
    gate_pass_rate: float
    llm_judge_avg: dict[str, float] | None = None
    pass_: bool  # SAS ≥ 0.6 AND CCS ≥ 0.5 AND gate_pass_rate ≥ 0.9
    warnings: int
```

## 评测引擎设计

### `backend/app/golden_eval.py`

```python
class GoldenSetEvaluator:
    def __init__(self, golden_set_dir: Path, llm: LLMClient, judge_llm: LLMClient | None = None):
        ...

    def load_golden_set(self) -> list[dict]:
        """加载 manifest 和所有 JSON 文件，校验 schema。"""

    def run(self, generator: PatentDraftGenerator) -> GoldenEvalReport:
        """全量评测：对每篇 golden 专利 run_one()，汇总为 eval_report。"""

    def run_one(self, entry: dict, generator: PatentDraftGenerator) -> EvalPatentResult:
        """单篇评测：构造成 InventionBrief → generate() → 跑 4 个评分器。"""

    def _gate_check(self, package: DraftPackage) -> tuple[bool, list[str]]:
        """① 结构化校验门禁。"""

    def _sas(self, gen: DraftPackage, gold: dict) -> tuple[float, dict]:
        """② 结构对齐度评分。"""

    def _ccs(self, gen: DraftPackage, gold: dict) -> tuple[float, dict]:
        """③ 信息覆盖度评分。"""

    def _llm_judge(self, gen: DraftPackage, gold: dict) -> dict | None:
        """④ LLM-as-Judge 双盲评分。judge_llm 为 None 时跳过。"""
```

### 设计约束

- 评测器**只读消费** `Generator.generate()`，不修改生成管线
- Golden-set 数据**只读**，不入库、不进入生成上下文
- LLM-Judge 的 API key 独立配置（`EVAL_LLM_API_KEY`），不与 `DEEPSEEK_API_KEY` 混淆
- 评测器**不导入** `main.py` 或任何 API 路由模块，独立可测

## CI 集成

### GitHub Actions workflow（新建）

```yaml
# .github/workflows/eval.yml
name: Golden-set Evaluation

on:
  pull_request:
    paths:
      - 'backend/app/generator.py'
      - 'backend/app/llm.py'
      - 'backend/app/schemas.py'
      - 'golden_set/v1/**'
  workflow_dispatch:  # 手动触发 LLM-Judge

jobs:
  fast-eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -e ".[dev]"
      - run: python3 -m pytest tests/test_golden_set_eval.py -m "not llm_judge" -q

  judge-eval:
    if: github.event_name == 'workflow_dispatch'
    runs-on: ubuntu-latest
    env:
      EVAL_LLM_API_KEY: ${{ secrets.EVAL_LLM_API_KEY }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -e ".[dev]"
      - run: python3 -m pytest tests/test_golden_set_eval.py -m "llm_judge" -q
```

### 门禁阈值

| 条件 | 动作 |
|---|---|
| SAS 均值 ≥ 0.6 | 通过 |
| CCS 均值 ≥ 0.5 | 通过 |
| gate_pass_rate ≥ 0.9 | 通过 |
| SAS 较上次下降 > 0.05 | 警告（不阻断） |
| SAS 较上次下降 > 0.1 | **阻断** |

### pytest 标记

```ini
# pyproject.toml
[tool.pytest.ini_options]
markers = [
    "golden_eval: golden-set evaluation tests",
    "llm_judge: LLM-as-Judge tests (require EVAL_LLM_API_KEY)",
]
```

## 前端最小适配

在 GuidedPatentFlow 的「质量检查」步骤新增一个「评测基准」小卡片：

- 显示上次 eval 的 SAS / CCS 均值 + 趋势箭头（↑/→/↓）
- LLM-Judge 分数在可用时展示
- 不新建路由，复用现有组件结构

## 文件清单

```
新增:
  golden_set/v1/                        # 20 篇授权专利的 JSON 文件
  golden_set/v1/manifest.json           # 索引
  scripts/scrape_golden_set.py          # CNIPA/Google Patents 抓取脚本
  tests/test_golden_set_eval.py         # 评测流水线测试
  backend/app/golden_eval.py            # 评测引擎
  .github/workflows/eval.yml            # CI 评测流水线

修改:
  backend/app/schemas.py                # 新增 EvalReport / EvalPatentResult 等模型
  pyproject.toml                        # 新增 pytest 标记 golden_eval / llm_judge
```

## 实现阶段

| 阶段 | 内容 | 依赖 | 产出 |
|---|---|---|---|
| **E1** | Golden-set 采集：写抓取脚本，从 CNIPA epub 拉取 20 篇，格式化为标准 JSON + manifest | 无 | 20 个 JSON + manifest |
| **E2** | 确定性评分器：在 `golden_eval.py` 实现 SAS + CCS + 增强门禁，在 `test_golden_set_eval.py` 写对应的 pytest | E1 的 golden-set 数据 | 零 API 成本可本地跑 |
| **E3** | LLM-Judge 评分器：实现 `_llm_judge()` 函数，4 维度 × 20 专利 = 80 次 LLM 调用，支持独立模型配置 | E2 的 scorer 骨架 | 可选跑，有 API 成本 |
| **E4** | 评测报告生成：综合 SAS + CCS + Judge 分数 → `eval_report.json`，支持与前次 diff 对比 | E2 + E3 | CI 可消费 |
| **E5** | CI 集成：写 `.github/workflows/eval.yml`，fast-eval 在 PR 时自动跑，judge-eval 手动触发 | E4 | GitHub Actions 门禁 |
| **E6** | 前端评测卡片：在 GuidedPatentFlow 质量检查步骤新增评测基准小卡片 | E4 的报告格式 | UI 可见 |

E2-E4 可合并为一个实现阶段，E5-E6 独立。

## 错误处理

- Golden-set JSON 文件缺失或 schema 不匹配 → `FileNotFoundError` 或 `ValidationError`，评测器报告具体文件而非崩溃
- 单篇专利 construct InventionBrief 失败 → 记录 `EvalPatentResult(gate_pass=False, gate_warnings=["input_construction_failed: ..."])`，不中断全量评测
- LLM-Judge API 调用失败 → 该维度置为 `null`，评测报告注明 `judge_errors: ["patent_id: dimension: error"]`
- `EVAL_LLM_API_KEY` 未配置 → `_llm_judge()` 返回 `None`，评测报告不包含 LLM-Judge 分数

## 测试计划

### 新增测试（`tests/test_golden_set_eval.py`）

- 从 golden-set JSON 构造 InventionBrief 的正确性
- SAS 计算：已知 gen 和 gold 输入，验证 SAS 输出在预期范围内
- CCS 计算：已知文本输入，验证名词召回和主题词覆盖计算正确
- 门禁规则：独立权项缺失 → gate_pass=False；features < 2 → 警告
- 评测报告序列化/反序列化（Pydantic 校验）
- LLM-Judge prompt 结构：JSON 可解析、shuffle 不丢失信息
- `FakeLLMClient` 模拟 Judge 返回 → 验证报告正确取用分数
- 边界条件：空 golden_set → 报告错误不为空；单篇失败不中断全量

### 回归验证

- 已有 130 测试不能变红
- `pytest` / `npm test` / `npm run build` 全绿

## 不变量

1. 已有 130 测试不能变红（`test_golden_set_eval.py` 作为新测试文件并存）
2. `PatentDraftGenerator.generate()` 公开 API 不变（评测器消费同一个接口）
3. Golden-set JSON 与项目代码解耦（可通过 `GOLDEN_SET_PATH` 环境变量指向外部目录）
4. 评测器不修改任何生产数据（generator / store / package 均为只读消费）

## 验收标准

- 20 篇 golden-set JSON 通过 manifest schema 校验
- 零 API 成本评测（SAS + CCS + 门禁）可在本地 `python3 -m pytest tests/test_golden_set_eval.py -m "not llm_judge"` 跑通
- `eval_report.json` 格式符合 `GoldenEvalReport` schema
- 修改 `generator.py` 的 claims prompt 导致 SAS/CCS 变化可被捕捉
- CI fast-eval 在 PR 时自动运行
- 已有 130 测试全绿

## 自检记录

- 无 TBD、TODO 或占位符；所有阈值与权重已明确。
- 四个评分维度与 CNIPA 审查指南锚点对齐，LLM-Judge 评分标准与 golden-set 对比基线一致。
- 确定性评分（SAS + CCS）与 LLM-Judge 互补：前者零成本可持续跑，后者有成本但覆盖语义质量。
- 评测体系与生成管线解耦，只读消费，不引入新的污染路径。
- 文件清单与实现阶段可一一映射，E2 + E4 可合并实现。
