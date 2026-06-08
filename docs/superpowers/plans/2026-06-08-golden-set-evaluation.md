# Golden-set 评测体系实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立 golden-set 驱动的评测体系——以 20 篇已授权 CNIPA 专利为真值，对每次生成做确定性评分（SAS + CCS + 门禁）+ LLM-as-Judge 双盲评分，并集成到 CI 门禁。

**Architecture:** `GoldenSetEvaluator` 消费 `golden_set/v1/` 中的标准 JSON → 构造 `InventionBrief` → 调用已有 `Generator.generate()` → 对产物运行 4 个评分器 → 产出 `GoldenEvalReport`。评测器与生成管线只读解耦，不修改生产数据。

**Tech Stack:** Python 3.11+, Pydantic v2, pytest, GitHub Actions, LLM-as-Judge 可选使用 Claude/GPT-4o API（独立 key `EVAL_LLM_API_KEY`）。

---

### Task 1: 新增评测报告数据模型

**Files:**
- Modify: `backend/app/schemas.py`

- [ ] **Step 1: 在 `schemas.py` 末尾追加 `EvalPatentResult`、`GoldenEvalSummary`、`GoldenEvalReport`**

```python
# --- Golden-set evaluation models (added below the last existing class) ---


class EvalPatentResult(BaseModel):
    """Single patent evaluation result within a golden-set run."""

    patent_id: str
    title: str
    technical_field: str
    gate_pass: bool
    gate_warnings: list[str] = Field(default_factory=list)
    sas: float  # 0-1
    sas_detail: dict[str, float] = Field(default_factory=dict)
    ccs: float  # 0-1
    ccs_detail: dict[str, float] = Field(default_factory=dict)
    llm_judge: dict[str, float | None] | None = None  # {"clarity": 4.0, ...} or None if judge not run


class GoldenEvalSummary(BaseModel):
    """Aggregated summary across all patents in a golden-set run."""

    sas_avg: float
    ccs_avg: float
    gate_pass_rate: float  # 0-1, fraction of patents that passed gate
    llm_judge_avg: dict[str, float] | None = None
    pass_: bool  # SAS ≥ 0.6 AND CCS ≥ 0.5 AND gate_pass_rate ≥ 0.9
    warnings: int


class GoldenEvalReport(BaseModel):
    """Full evaluation report for a golden-set run."""

    run_id: str
    commit: str
    golden_set_version: str
    timestamp: datetime = Field(default_factory=_utc_now_iso)
    summary: GoldenEvalSummary
    per_patent: list[EvalPatentResult] = Field(default_factory=list)
    diff_from_previous: dict[str, Any] | None = None
```

- [ ] **Step 2: 验证导入**

```bash
python3 -c "from backend.app.schemas import EvalPatentResult, GoldenEvalSummary, GoldenEvalReport; print('imports OK')"
```
Expected: `imports OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas.py
git commit -m "feat: add golden-set evaluation report models"
```

---

### Task 2: 创建 golden-set 数据（3 篇示例 + manifest）

**Files:**
- Create: `golden_set/v1/manifest.json`
- Create: `golden_set/v1/CN-ai-001.json`
- Create: `golden_set/v1/CN-mech-001.json`
- Create: `golden_set/v1/CN-elec-001.json`

> **Note:** E1 约定 20 篇完整采集由后续 `scripts/scrape_golden_set.py` 完成。本任务先创建 3 篇手工构造的示例专利，确保 E2 的评分器有可测数据。其余 17 篇在 Task 9 中通过抓取脚本补全。

- [ ] **Step 1: 创建 manifest**

`golden_set/v1/manifest.json`：

```json
{
  "version": "v1",
  "created": "2026-06-08",
  "entries": [
    {"id": "CN-ai-001", "title": "一种图像缺陷识别方法及系统", "technical_field": "ai_software", "claims_count": 6},
    {"id": "CN-mech-001", "title": "一种自适应夹持装置", "technical_field": "mechanical", "claims_count": 8},
    {"id": "CN-elec-001", "title": "一种低功耗电源管理电路", "technical_field": "electronics", "claims_count": 7}
  ]
}
```

- [ ] **Step 2: 创建 CN-ai-001.json（AI 软件方法示例）**

`golden_set/v1/CN-ai-001.json`：

```json
{
  "id": "CN-ai-001",
  "title": "一种图像缺陷识别方法及系统",
  "technical_field": "ai_software",
  "publication_date": "2023-06-15",
  "claims_count": 6,
  "input": {
    "description_full": "技术领域\n本发明涉及人工智能检测技术领域，具体涉及一种基于神经网络的图像缺陷识别方法及系统。\n背景技术\n现有技术中，工业产品表面缺陷检测主要依赖人工目视检查，效率低、一致性差，且难以适应大规模生产线的实时检测需求。部分自动化方案采用传统机器视觉算法（如边缘检测、模板匹配），但对复杂纹理和微小缺陷的识别准确率不足。\n发明内容\n本发明提供一种图像缺陷识别方法，包括：采集待检测产品的表面图像；通过预训练的卷积神经网络模型提取图像特征图；将特征图输入区域提议网络生成候选缺陷区域；对每个候选区域执行分类和边界框回归，输出缺陷类别和位置坐标。系统包括图像采集模块、特征提取模块、区域提议模块和分类回归模块。\n具体实施方式\n下面结合附图对本发明的具体实施方式进行描述。如图1所示，本实施例的图像缺陷识别方法包括以下步骤：S1，工业相机以固定帧率采集生产线上的产品表面图像，图像分辨率为2048×1536像素；S2，将采集到的图像输入经过ImageNet预训练的ResNet-50骨干网络，提取多层特征图；S3，特征金字塔网络融合不同尺度的特征图，生成统一的多尺度特征表示；S4，区域提议网络在特征图上滑动窗口，生成2000个候选缺陷区域；S5，对每个候选区域执行ROI Align操作，提取固定尺寸的区域特征；S6，分类分支输出该区域属于划痕、凹坑、色差、毛刺或正常五类的概率；S7，回归分支输出缺陷边界框的精确坐标偏移量；S8，非极大值抑制去除重叠检测框，输出最终缺陷检测结果。",
    "drawings_description": "图1为图像缺陷识别方法流程图。\n图2为图像缺陷识别系统结构图。\n图3为特征金字塔网络结构示意图。"
  },
  "ground_truth": {
    "claims": [
      {
        "number": 1,
        "kind": "independent",
        "category": "method",
        "depends_on": null,
        "preamble": "一种图像缺陷识别方法，其特征在于，包括：",
        "features": [
          "采集待检测产品的表面图像",
          "通过预训练的卷积神经网络模型提取图像特征图",
          "将特征图输入区域提议网络生成候选缺陷区域",
          "对每个候选区域执行分类和边界框回归，输出缺陷类别和位置坐标"
        ]
      },
      {
        "number": 2,
        "kind": "dependent",
        "category": "method",
        "depends_on": 1,
        "preamble": "根据权利要求1所述的方法，其特征在于：",
        "features": [
          "所述特征图通过特征金字塔网络融合不同尺度的特征图生成多尺度特征表示"
        ]
      },
      {
        "number": 3,
        "kind": "dependent",
        "category": "method",
        "depends_on": 1,
        "preamble": "根据权利要求1所述的方法，其特征在于：",
        "features": [
          "对所述候选缺陷区域执行ROI Align操作提取固定尺寸的区域特征后再执行分类和回归"
        ]
      },
      {
        "number": 4,
        "kind": "dependent",
        "category": "method",
        "depends_on": 1,
        "preamble": "根据权利要求1所述的方法，其特征在于：",
        "features": [
          "通过非极大值抑制去除重叠检测框后输出最终缺陷检测结果"
        ]
      },
      {
        "number": 5,
        "kind": "independent",
        "category": "system",
        "depends_on": null,
        "preamble": "一种图像缺陷识别系统，其特征在于，包括：",
        "features": [
          "图像采集模块，用于采集待检测产品的表面图像",
          "特征提取模块，用于通过预训练的卷积神经网络模型提取图像特征图",
          "区域提议模块，用于生成候选缺陷区域",
          "分类回归模块，用于对每个候选区域执行分类和边界框回归并输出缺陷类别和位置坐标"
        ]
      },
      {
        "number": 6,
        "kind": "dependent",
        "category": "system",
        "depends_on": 5,
        "preamble": "根据权利要求5所述的系统，其特征在于：",
        "features": [
          "所述特征提取模块包括特征金字塔网络，用于融合不同尺度的特征图"
        ]
      }
    ],
    "description_sections": {
      "technical_field": "本发明涉及人工智能检测技术领域，具体涉及一种基于神经网络的图像缺陷识别方法及系统。",
      "background": "现有技术中，工业产品表面缺陷检测主要依赖人工目视检查，效率低、一致性差，且难以适应大规模生产线的实时检测需求。部分自动化方案采用传统机器视觉算法，但对复杂纹理和微小缺陷的识别准确率不足。",
      "summary": "本发明提供一种图像缺陷识别方法，包括：采集待检测产品的表面图像；通过预训练的卷积神经网络模型提取图像特征图；将特征图输入区域提议网络生成候选缺陷区域；对每个候选区域执行分类和边界框回归，输出缺陷类别和位置坐标。系统包括图像采集模块、特征提取模块、区域提议模块和分类回归模块。",
      "embodiments": "下面结合附图对本发明的具体实施方式进行描述。如图1所示，本实施例的图像缺陷识别方法包括以下步骤：S1，工业相机以固定帧率采集生产线上的产品表面图像；S2，将采集到的图像输入经过ImageNet预训练的ResNet-50骨干网络，提取多层特征图；S3，特征金字塔网络融合不同尺度的特征图，生成统一的多尺度特征表示；S4，区域提议网络在特征图上滑动窗口，生成2000个候选缺陷区域；S5，对每个候选区域执行ROI Align操作，提取固定尺寸的区域特征；S6，分类分支输出该区域属于划痕、凹坑、色差、毛刺或正常五类的概率；S7，回归分支输出缺陷边界框的精确坐标偏移量；S8，非极大值抑制去除重叠检测框，输出最终缺陷检测结果。"
    },
    "figures": [
      {"figure_no": "图1", "title": "图像缺陷识别方法流程图"},
      {"figure_no": "图2", "title": "图像缺陷识别系统结构图"},
      {"figure_no": "图3", "title": "特征金字塔网络结构示意图"}
    ]
  }
}
```

- [ ] **Step 3: 创建 CN-mech-001.json（机械结构示例）**

`golden_set/v1/CN-mech-001.json`：

```json
{
  "id": "CN-mech-001",
  "title": "一种自适应夹持装置",
  "technical_field": "mechanical",
  "publication_date": "2022-03-10",
  "claims_count": 8,
  "input": {
    "description_full": "技术领域\n本发明涉及机械加工夹具技术领域，具体涉及一种自适应夹持装置。\n背景技术\n在机械加工过程中，工件夹持的稳定性和定位精度直接影响加工质量。传统夹持装置采用固定钳口结构，对于不规则形状工件的适应性较差，需要频繁更换专用夹具。部分方案引入弹性元件或可调节钳口，但调节范围有限且缺乏力反馈控制，容易造成工件变形或夹持力不足。\n发明内容\n本发明提供一种自适应夹持装置，包括基座、固定钳口、活动钳口、驱动机构和力传感器阵列。活动钳口表面布置有多个独立驱动的微型夹爪，每个微型夹爪通过力传感器实时检测与工件接触面的法向力；控制器接收力传感器信号，根据预设的力阈值独立调节每个微型夹爪的伸缩量，使各接触点的夹持力保持均匀，实现对不规则形状工件的自适应包络夹持。\n具体实施方式\n如图1所示，本实施例的自适应夹持装置包括基座1、固定钳口2和活动钳口总成3。活动钳口总成3包含一个6×8的微型夹爪阵列31，每个微型夹爪由微型步进电机驱动，最大行程15mm，定位精度0.02mm。微型夹爪前端安装有薄膜压力传感器32，量程0-500N，采样频率100Hz。控制器4为ARM Cortex-M7处理器，运行实时控制固件。夹持工作时，控制器先驱动所有微型夹爪以低速伸出直至各自压力传感器读数超过10N（表明已接触工件表面）；然后根据预设的目标夹持力曲线，独立调节每个微型夹爪的伸出量，使所有接触点的法向力保持在50±5N范围内。",
    "drawings_description": "图1为自适应夹持装置整体结构图。\n图2为活动钳口总成的微型夹爪阵列布局图。\n图3为力反馈控制流程图。"
  },
  "ground_truth": {
    "claims": [
      {
        "number": 1,
        "kind": "independent",
        "category": "device",
        "depends_on": null,
        "preamble": "一种自适应夹持装置，其特征在于，包括：",
        "features": [
          "基座",
          "固定钳口，固定在所述基座的一端",
          "活动钳口，可滑动地安装在所述基座上，其夹持面布置有多个独立驱动的微型夹爪",
          "每个微型夹爪的前端安装有力传感器，用于检测与工件接触面的法向力",
          "控制器，接收各力传感器的信号，根据预设力阈值独立调节每个微型夹爪的伸缩量，使各接触点的夹持力保持均匀"
        ]
      },
      {
        "number": 2,
        "kind": "dependent",
        "category": "device",
        "depends_on": 1,
        "preamble": "根据权利要求1所述的装置，其特征在于：",
        "features": [
          "所述微型夹爪由微型步进电机驱动，行程不小于10mm，定位精度不低于0.05mm"
        ]
      },
      {
        "number": 3,
        "kind": "dependent",
        "category": "device",
        "depends_on": 1,
        "preamble": "根据权利要求1所述的装置，其特征在于：",
        "features": [
          "所述力传感器为薄膜压力传感器，量程覆盖0-500N，采样频率不低于50Hz"
        ]
      },
      {
        "number": 4,
        "kind": "dependent",
        "category": "device",
        "depends_on": 1,
        "preamble": "根据权利要求1所述的装置，其特征在于：",
        "features": [
          "所述微型夹爪以m×n二维阵列方式排布，其中m≥4，n≥4"
        ]
      },
      {
        "number": 5,
        "kind": "dependent",
        "category": "device",
        "depends_on": 1,
        "preamble": "根据权利要求1所述的装置，其特征在于：",
        "features": [
          "所述控制器先以低速驱动所有微型夹爪伸出直至各传感器读数超过接触阈值，然后根据目标夹持力曲线独立调节每个微型夹爪的伸缩量"
        ]
      },
      {
        "number": 6,
        "kind": "independent",
        "category": "method",
        "depends_on": null,
        "preamble": "一种自适应夹持方法，其特征在于，包括：",
        "features": [
          "驱动活动钳口上的多个微型夹爪以第一速度伸出",
          "监测每个微型夹爪前端的力传感器读数",
          "当某微型夹爪的力传感器读数超过接触阈值时，将该微型夹爪切换为力控模式",
          "根据预设目标夹持力，独立调节处于力控模式的各微型夹爪的伸缩量，使各接触点法向力趋于均匀"
        ]
      },
      {
        "number": 7,
        "kind": "dependent",
        "category": "method",
        "depends_on": 6,
        "preamble": "根据权利要求6所述的方法，其特征在于：",
        "features": [
          "所述第一速度低于力控模式下的调节速度"
        ]
      },
      {
        "number": 8,
        "kind": "dependent",
        "category": "method",
        "depends_on": 6,
        "preamble": "根据权利要求6所述的方法，其特征在于：",
        "features": [
          "所述接触阈值设置为5-15N，所述目标夹持力设置为40-60N"
        ]
      }
    ],
    "description_sections": {
      "technical_field": "本发明涉及机械加工夹具技术领域，具体涉及一种自适应夹持装置。",
      "background": "在机械加工过程中，工件夹持的稳定性和定位精度直接影响加工质量。传统夹持装置采用固定钳口结构，对于不规则形状工件的适应性较差，需要频繁更换专用夹具。部分方案引入弹性元件或可调节钳口，但调节范围有限且缺乏力反馈控制。",
      "summary": "本发明提供一种自适应夹持装置，包括基座、固定钳口、活动钳口、驱动机构和力传感器阵列。活动钳口表面布置有多个独立驱动的微型夹爪，每个微型夹爪通过力传感器实时检测与工件接触面的法向力；控制器接收力传感器信号，根据预设力阈值独立调节每个微型夹爪的伸缩量，使各接触点的夹持力保持均匀。",
      "embodiments": "如图1所示，本实施例的自适应夹持装置包括基座1、固定钳口2和活动钳口总成3。活动钳口总成3包含一个6×8的微型夹爪阵列31，每个微型夹爪由微型步进电机驱动，最大行程15mm，定位精度0.02mm。微型夹爪前端安装有薄膜压力传感器32，量程0-500N，采样频率100Hz。控制器4为ARM Cortex-M7处理器，运行实时控制固件。夹持工作时，控制器先驱动所有微型夹爪以低速伸出直至各自压力传感器读数超过10N；然后根据预设的目标夹持力曲线，独立调节每个微型夹爪的伸出量，使所有接触点的法向力保持在50±5N范围内。"
    },
    "figures": [
      {"figure_no": "图1", "title": "自适应夹持装置整体结构图"},
      {"figure_no": "图2", "title": "活动钳口总成的微型夹爪阵列布局图"},
      {"figure_no": "图3", "title": "力反馈控制流程图"}
    ]
  }
}
```

- [ ] **Step 4: 创建 CN-elec-001.json（电学电路示例）**

`golden_set/v1/CN-elec-001.json`：

```json
{
  "id": "CN-elec-001",
  "title": "一种低功耗电源管理电路",
  "technical_field": "electronics",
  "publication_date": "2024-01-20",
  "claims_count": 7,
  "input": {
    "description_full": "技术领域\n本发明涉及电源管理技术领域，具体涉及一种低功耗电源管理电路。\n背景技术\n在电池供电的物联网终端设备中，电源管理电路的静态功耗直接影响设备的续航时间。传统线性稳压器在轻载条件下效率低下，而开关稳压器在待机模式下仍存在可观的开关损耗和控制电路功耗。部分方案采用间歇工作模式降低平均功耗，但输出电压纹波较大，不适用于对电源噪声敏感的模拟前端电路。\n发明内容\n本发明提供一种低功耗电源管理电路，包括输入级、自适应偏置电路、PWM/PFM双模式控制器和输出级。自适应偏置电路检测负载电流，当负载电流低于阈值时，将控制器切换至脉冲频率调制PFM模式并降低偏置电流至正常值的10-20%；当负载电流高于阈值时，恢复脉冲宽度调制PWM模式和全偏置电流。输出级采用分段功率管架构，轻载时仅启用小尺寸功率管以降低栅极驱动损耗。\n具体实施方式\n如图1所示，本实施例的低功耗电源管理电路100包括：输入电压端Vin 101、自适应偏置电路102、PWM/PFM双模式控制器103、分段输出级104和输出电压端Vout 105。自适应偏置电路102通过采样电阻Rsense 106检测流经电感L1的电流，当检测到平均负载电流小于10mA时，输出模式切换信号MODE_SEL=0，控制器103进入PFM模式，同时偏置电流源IBIAS从50μA降低至8μA；当负载电流回升至20mA以上时，MODE_SEL=1，恢复PWM模式和全偏置。分段输出级104包含大尺寸功率管M1(W/L=20000/0.18)和小尺寸功率管M2(W/L=2000/0.18)，在PFM模式下仅M2工作。",
    "drawings_description": "图1为低功耗电源管理电路的整体架构图。\n图2为自适应偏置电路的详细电路图。\n图3为PWM与PFM模式切换的时序图。"
  },
  "ground_truth": {
    "claims": [
      {
        "number": 1,
        "kind": "independent",
        "category": "device",
        "depends_on": null,
        "preamble": "一种低功耗电源管理电路，其特征在于，包括：",
        "features": [
          "输入级，用于接收输入电压",
          "自适应偏置电路，用于检测负载电流并将模式切换信号输出至控制器",
          "PWM/PFM双模式控制器，根据所述模式切换信号在脉冲宽度调制模式和脉冲频率调制模式之间切换",
          "输出级，采用分段功率管架构，在PFM模式下仅启用小尺寸功率管",
          "当负载电流低于第一阈值时切换到PFM模式并降低偏置电流，当负载电流高于第二阈值时切换到PWM模式并恢复全偏置电流"
        ]
      },
      {
        "number": 2,
        "kind": "dependent",
        "category": "device",
        "depends_on": 1,
        "preamble": "根据权利要求1所述的电路，其特征在于：",
        "features": [
          "PFM模式下偏置电流降低至PWM模式下偏置电流的10%-20%"
        ]
      },
      {
        "number": 3,
        "kind": "dependent",
        "category": "device",
        "depends_on": 1,
        "preamble": "根据权利要求1所述的电路，其特征在于：",
        "features": [
          "所述第一阈值小于所述第二阈值，形成迟滞窗口以避免模式频繁切换"
        ]
      },
      {
        "number": 4,
        "kind": "dependent",
        "category": "device",
        "depends_on": 1,
        "preamble": "根据权利要求1所述的电路，其特征在于：",
        "features": [
          "所述分段功率管架构包括大尺寸功率管和小尺寸功率管，小尺寸功率管的宽长比为大尺寸功率管的1/5至1/20"
        ]
      },
      {
        "number": 5,
        "kind": "dependent",
        "category": "device",
        "depends_on": 1,
        "preamble": "根据权利要求1所述的电路，其特征在于：",
        "features": [
          "所述自适应偏置电路通过采样电阻检测流经输出电感的电流来获取负载电流信息"
        ]
      },
      {
        "number": 6,
        "kind": "independent",
        "category": "method",
        "depends_on": null,
        "preamble": "一种电源管理方法，其特征在于，包括：",
        "features": [
          "检测负载电流",
          "当负载电流低于第一阈值时，将控制器切换至脉冲频率调制PFM模式并将偏置电流降低至全偏置的10%-20%",
          "当负载电流高于第二阈值时，将控制器切换至脉冲宽度调制PWM模式并恢复全偏置电流",
          "在PFM模式下仅启用分段输出级中的小尺寸功率管以降低栅极驱动损耗"
        ]
      },
      {
        "number": 7,
        "kind": "dependent",
        "category": "method",
        "depends_on": 6,
        "preamble": "根据权利要求6所述的方法，其特征在于：",
        "features": [
          "所述第一阈值设置为5-15mA，所述第二阈值设置为15-30mA，且第一阈值小于第二阈值"
        ]
      }
    ],
    "description_sections": {
      "technical_field": "本发明涉及电源管理技术领域，具体涉及一种低功耗电源管理电路。",
      "background": "在电池供电的物联网终端设备中，电源管理电路的静态功耗直接影响设备的续航时间。传统线性稳压器在轻载条件下效率低下，而开关稳压器在待机模式下仍存在可观的开关损耗和控制电路功耗。部分方案采用间歇工作模式但输出电压纹波较大。",
      "summary": "本发明提供一种低功耗电源管理电路，包括输入级、自适应偏置电路、PWM/PFM双模式控制器和输出级。自适应偏置电路检测负载电流，当负载电流低于阈值时将控制器切换至PFM模式并降低偏置电流；当负载电流高于阈值时恢复PWM模式和全偏置电流。输出级采用分段功率管架构，轻载时仅启用小尺寸功率管以降低栅极驱动损耗。",
      "embodiments": "如图1所示，本实施例的低功耗电源管理电路100包括：输入电压端Vin 101、自适应偏置电路102、PWM/PFM双模式控制器103、分段输出级104和输出电压端Vout 105。自适应偏置电路102通过采样电阻Rsense 106检测流经电感L1的电流，当检测到平均负载电流小于10mA时，输出模式切换信号MODE_SEL=0，控制器103进入PFM模式，同时偏置电流源IBIAS从50μA降低至8μA；当负载电流回升至20mA以上时，MODE_SEL=1，恢复PWM模式和全偏置。分段输出级104包含大尺寸功率管M1(W/L=20000/0.18)和小尺寸功率管M2(W/L=2000/0.18)，在PFM模式下仅M2工作。"
    },
    "figures": [
      {"figure_no": "图1", "title": "低功耗电源管理电路的整体架构图"},
      {"figure_no": "图2", "title": "自适应偏置电路的详细电路图"},
      {"figure_no": "图3", "title": "PWM与PFM模式切换的时序图"}
    ]
  }
}
```

- [ ] **Step 5: 验证 JSON 文件格式**

```bash
python3 -c "
import json
from pathlib import Path
d = Path('golden_set/v1')
manifest = json.loads((d / 'manifest.json').read_text())
assert manifest['version'] == 'v1'
for entry in manifest['entries']:
    patent = json.loads((d / f'{entry[\"id\"]}.json').read_text())
    assert 'input' in patent
    assert 'ground_truth' in patent
    assert len(patent['ground_truth']['claims']) == entry['claims_count']
    print(f'{entry[\"id\"]}: OK ({entry[\"claims_count\"]} claims)')
"
```
Expected: 3 lines of `CN-xxx-001: OK (N claims)`

- [ ] **Step 6: Commit**

```bash
git add golden_set/v1/
git commit -m "feat: add golden-set v1 with 3 example patents"
```

---

### Task 3: 实现评测引擎（GoldenSetEvaluator 骨架 + 门禁）

**Files:**
- Create: `backend/app/golden_eval.py`
- Create: `tests/test_golden_set_eval.py`

- [ ] **Step 1: 创建 `tests/test_golden_set_eval.py`，写门禁测试（先于实现）**

```python
from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.app.golden_eval import GoldenSetEvaluator, _construct_invention_brief, _gate_check
from backend.app.llm import FakeLLMClient
from backend.app.schemas import (
    AbstractOutput,
    ClaimItem,
    ClaimsOutput,
    DescriptionOutput,
    DraftPackage,
    DrawingsOutput,
    FigureItem,
    GoldenEvalReport,
    InventionBrief,
)


def _sample_golden_entry() -> dict:
    return {
        "id": "CN-test-001",
        "title": "一种测试方法",
        "technical_field": "ai_software",
        "input": {
            "description_full": (
                "技术领域\n本发明涉及测试领域。\n"
                "背景技术\n现有技术效率低。\n"
                "发明内容\n本发明提供一种测试方法，包括采集数据和输出结果。\n"
                "具体实施方式\n采集数据后进行预处理，然后输出结果。"
            ),
            "drawings_description": "图1为方法流程图。",
        },
        "ground_truth": {
            "claims": [
                {
                    "number": 1,
                    "kind": "independent",
                    "category": "method",
                    "depends_on": None,
                    "preamble": "一种测试方法，其特征在于，包括：",
                    "features": ["采集数据", "输出结果"],
                }
            ],
            "description_sections": {
                "technical_field": "本发明涉及测试领域。",
                "background": "现有技术效率低。",
                "summary": "本发明提供一种测试方法。",
                "embodiments": "采集数据后进行预处理。",
            },
            "figures": [{"figure_no": "图1", "title": "方法流程图"}],
        },
    }


def _make_package(claims_features=None, description_sections=None):
    """Build a valid DraftPackage with structured fields."""
    if claims_features is None:
        claims_features = [["采集数据", "输出结果"]]
    return DraftPackage(
        title="一种测试方法",
        abstract="本发明公开了一种测试方法。",
        claims="1. 一种测试方法，其特征在于，采集数据和输出结果。",
        description="技术领域\n本发明涉及测试领域。\n背景技术\n现有技术效率低。\n发明内容\n本发明提供一种测试方法。\n附图说明\n图1为方法流程图。\n具体实施方式\n采集数据并输出结果。",
        drawing_description="图1为方法流程图。",
        mermaid="",
        image_prompt="",
        claims_struct=ClaimsOutput(
            claims=[
                ClaimItem(
                    number=1,
                    kind="independent",
                    category="method",
                    preamble="一种测试方法，其特征在于，包括：",
                    features=claims_features[0],
                )
            ]
        ),
        description_struct=DescriptionOutput(
            technical_field="本发明涉及测试领域。",
            background="现有技术效率低。",
            summary="本发明提供一种测试方法。",
            embodiments="采集数据并输出结果。",
        ),
        drawings_struct=DrawingsOutput(figures=[FigureItem(figure_no="图1", title="方法流程图")]),
        abstract_struct=AbstractOutput(abstract="本发明公开了一种测试方法。"),
    )


# --- Gate check tests ---


def test_gate_pass_with_valid_package():
    package = _make_package()
    passed, warnings = _gate_check(package)
    assert passed is True
    assert len(warnings) == 0


def test_gate_fail_when_no_independent_claim():
    package = _make_package()
    package.claims_struct.claims[0].kind = "dependent"
    passed, warnings = _gate_check(package)
    assert passed is False
    assert any("independent" in w for w in warnings)


def test_gate_warn_when_independent_claim_has_fewer_than_two_features():
    package = _make_package(claims_features=[["仅一个步骤"]])
    passed, warnings = _gate_check(package)
    assert passed is True  # warning only
    assert any("特征不足" in w or "features" in w for w in warnings)


def test_gate_warn_when_description_section_too_short():
    package = _make_package()
    package.description_struct.background = "短。"
    passed, warnings = _gate_check(package)
    assert passed is True
    assert any("背景技术" in w or "过短" in w for w in warnings)
```

- [ ] **Step 2: 运行测试，确认全部失败**

```bash
python3 -m pytest tests/test_golden_set_eval.py -q
```
Expected: FAIL — `ModuleNotFoundError` for `backend.app.golden_eval`

- [ ] **Step 3: 创建 `backend/app/golden_eval.py`，实现门禁**

```python
from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any

from backend.app.generator import PatentDraftGenerator
from backend.app.llm import LLMClient
from backend.app.schemas import (
    DraftPackage,
    EvalPatentResult,
    GoldenEvalReport,
    GoldenEvalSummary,
    InventionBrief,
)

# --- Gate check ---

_MIN_SECTION_LENGTH = 20


def _gate_check(package: DraftPackage) -> tuple[bool, list[str]]:
    """① 结构化校验门禁：返回 (pass, warnings)。"""
    warnings: list[str] = []

    cs = package.claims_struct
    if cs is None:
        return False, ["claims_struct is None — generation did not produce structured claims"]

    indies = [c for c in cs.claims if c.kind == "independent"]
    if not indies:
        return False, ["no independent claim found"]

    for c in indies:
        if len(c.features) < 2:
            warnings.append(f"claim {c.number} (independent) has fewer than 2 features")

    ds = package.description_struct
    if ds is not None:
        for label, text in [
            ("技术领域", ds.technical_field),
            ("背景技术", ds.background),
            ("发明内容", ds.summary),
            ("具体实施方式", ds.embodiments),
        ]:
            if len((text or "").strip()) < _MIN_SECTION_LENGTH:
                warnings.append(f"{label} section too short (< {_MIN_SECTION_LENGTH} chars)")

    if package.abstract_struct is not None and len(package.abstract_struct.abstract) > 300:
        warnings.append("abstract exceeds 300 characters")

    return True, warnings


# --- InventionBrief construction ---

_TECH_FIELD_LABELS = {
    "ai_software": "人工智能软件方法",
    "mechanical": "机械结构",
    "electronics": "电学电路",
    "chemical": "化学工艺",
}

_STEP_VERBS = ["采集", "获取", "解析", "训练", "检索", "生成", "输出", "审核", "导出", "检测", "提取", "调节", "控制"]

_EFFECT_KEYWORDS = ["提高", "降低", "提升", "减少", "避免", "实现"]


def _find_section(text: str, pattern: str) -> str:
    """Extract the section body following a heading that matches `pattern`."""
    m = re.search(rf"({pattern})\s*\n", text)
    if not m:
        return ""
    start = m.end()
    # Find next section heading or end of text
    next_heading = re.search(r"\n(技术领域|背景技术|技术背景|发明内容|技术方案|附图说明|具体实施方式|权利要求)", text[start:])
    end = start + next_heading.start() if next_heading else len(text)
    return text[start:end].strip()


def _construct_invention_brief(entry: dict) -> InventionBrief:
    """Construct an InventionBrief from a golden-set patent entry."""
    inp = entry["input"]
    desc = inp.get("description_full", "")

    technical_field = _TECH_FIELD_LABELS.get(entry.get("technical_field", ""), "人工智能软件方法")

    # Extract technical_problem from background section
    bg = _find_section(desc, "背景技术|技术背景")
    technical_problem = bg[:80] if bg else "现有技术存在改进空间。"

    # Extract technical_solution from summary section
    summary = _find_section(desc, "发明内容|技术方案")
    technical_solution = summary[:500] if summary else desc[:500]

    # Extract beneficial_effects
    beneficial_effects: list[str] = []
    for line in desc.split("\n"):
        line = line.strip()
        if any(kw in line for kw in _EFFECT_KEYWORDS) and len(line) > 10:
            beneficial_effects.append(line[:200])
            if len(beneficial_effects) >= 3:
                break

    # Extract key_steps by verb keywords
    key_steps: list[str] = []
    for verb in _STEP_VERBS:
        if verb in desc:
            key_steps.append(verb)
        if len(key_steps) >= 5:
            break

    return InventionBrief(
        title=entry["title"],
        technical_field=technical_field,
        technical_problem=technical_problem,
        technical_solution=technical_solution,
        beneficial_effects=beneficial_effects or ["提升系统性能"],
        key_steps=key_steps or ["获取输入数据", "生成输出结果"],
    )
```

- [ ] **Step 4: 运行门禁测试**

```bash
python3 -m pytest tests/test_golden_set_eval.py -q
```
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/golden_eval.py tests/test_golden_set_eval.py
git commit -m "feat: add golden-set evaluator skeleton with gate check"
```

---

### Task 4: 实现 SAS 和 CCS 评分器

**Files:**
- Modify: `backend/app/golden_eval.py`（追加 SAS/CCS 函数）
- Modify: `tests/test_golden_set_eval.py`（追加 SAS/CCS 测试）

- [ ] **Step 1: 在 `test_golden_set_eval.py` 末尾追加 SAS/CCS 测试**

```python
# --- SAS tests ---

from backend.app.golden_eval import _sas, _ccs


def test_sas_perfect_match():
    package = _make_package()
    gold = _sample_golden_entry()
    score, detail = _sas(package, gold)
    assert score >= 0.8  # near-perfect match
    assert "claims_count_align" in detail


def test_sas_low_when_claims_count_mismatch():
    package = _make_package()
    gold = _sample_golden_entry()
    # Modify gold to have 10 claims vs 1 gen claim
    gold["ground_truth"]["claims"] = [
        {"number": i, "kind": "independent" if i == 1 else "dependent", "category": "method", "depends_on": 1 if i > 1 else None, "preamble": "...", "features": [f"步骤{i}"]}
        for i in range(1, 11)
    ]
    gold["claims_count"] = 10
    score, detail = _sas(package, gold)
    assert score < 0.6
    assert detail["claims_count_align"] < 0.3


def test_sas_category_coverage_partial():
    package = _make_package()  # only method
    gold = _sample_golden_entry()
    # Add a system claim to gold
    gold["ground_truth"]["claims"].append({
        "number": 2, "kind": "independent", "category": "system", "depends_on": None,
        "preamble": "一种测试系统", "features": ["模块A"]
    })
    gold["claims_count"] = 2
    score, detail = _sas(package, gold)
    assert detail["category_coverage"] < 1.0  # gen has no system claim


# --- CCS tests ---


def test_ccs_full_coverage():
    package = _make_package()
    gold = _sample_golden_entry()
    score, detail = _ccs(package, gold)
    assert score > 0.5  # content substantially matches


def test_ccs_low_when_key_nouns_missing():
    package = _make_package(claims_features=[["无关步骤"]])
    gold = _sample_golden_entry()
    score, detail = _ccs(package, gold)
    # "采集数据" and "输出结果" from gold not in gen
    assert score < 0.5


def test_ccs_topic_term_recall():
    package = _make_package()
    gold = _sample_golden_entry()
    _, detail = _ccs(package, gold)
    assert "topic_term_recall" in detail
    assert 0.0 <= detail["topic_term_recall"] <= 1.0
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
python3 -m pytest tests/test_golden_set_eval.py -q
```
Expected: FAIL — `ImportError` for `_sas` and `_ccs`

- [ ] **Step 3: 在 `golden_eval.py` 中追加 `_sas` 和 `_ccs`**

```python
# --- SAS (Structure Alignment Score) ---


def _sas(package: DraftPackage, gold: dict) -> tuple[float, dict[str, float]]:
    """② 结构对齐度评分，0-1，确定性计算。"""
    gen_claims = package.claims_struct.claims if package.claims_struct else []
    gold_claims = gold["ground_truth"]["claims"]

    gen_n = len(gen_claims)
    gold_n = len(gold_claims)
    claims_count_align = min(gen_n, gold_n) / max(gen_n, gold_n) if max(gen_n, gold_n) > 0 else 0.0

    gen_indies = [c for c in gen_claims if c.kind == "independent"]
    gold_indies = [c for c in gold_claims if c["kind"] == "independent"]
    gen_indie_ratio = len(gen_indies) / gen_n if gen_n > 0 else 0.0
    gold_indie_ratio = len(gold_indies) / gold_n if gold_n > 0 else 0.0
    independent_ratio_align = 1.0 - abs(gen_indie_ratio - gold_indie_ratio)

    gen_categories = {c.category for c in gen_claims if c.category}
    gold_categories = {c.get("category", "other") for c in gold_claims}
    category_coverage = len(gen_categories & gold_categories) / len(gold_categories) if gold_categories else 1.0

    ds = package.description_struct
    section_count = 0
    if ds is not None:
        for text in [ds.technical_field, ds.background, ds.summary, ds.embodiments]:
            if len((text or "").strip()) >= _MIN_SECTION_LENGTH:
                section_count += 1
    section_completeness = section_count / 4.0

    detail = {
        "claims_count_align": round(claims_count_align, 4),
        "independent_ratio_align": round(independent_ratio_align, 4),
        "category_coverage": round(category_coverage, 4),
        "section_completeness": round(section_completeness, 4),
    }
    score = (
        0.30 * claims_count_align
        + 0.25 * independent_ratio_align
        + 0.25 * category_coverage
        + 0.20 * section_completeness
    )
    return round(score, 4), detail


# --- CCS (Content Coverage Score) ---


def _extract_nouns(text: str, min_len: int = 2) -> set[str]:
    """Extract potential noun phrases (Chinese characters ≥ min_len) from text."""
    # Simple extraction: split on non-Chinese chars, collect substrings ≥ min_len
    cleaned = re.sub(r"[^一-鿿]", " ", text)
    words = [w.strip() for w in cleaned.split() if len(w.strip()) >= min_len]
    # Also extract bigrams and trigrams from longer segments
    result = set(words)
    for seg in re.findall(r"[一-鿿]{3,}", text):
        for i in range(len(seg) - min_len + 1):
            result.add(seg[i:i + min_len])
    # Remove very generic stopwords
    stopwords = {"所述", "包括", "用于", "以及", "其中", "一种", "涉及", "进行", "通过", "可以", "步骤", "模块"}
    return {w for w in result if w not in stopwords and len(w) >= min_len}


def _extract_topic_terms(text: str, top_n: int = 5) -> list[str]:
    """Extract top-N topic terms by frequency from text."""
    nouns = _extract_nouns(text, min_len=3)
    # Score by length-weighted frequency
    freq: dict[str, int] = {}
    for noun in nouns:
        freq[noun] = freq.get(noun, 0) + 1
    # Prioritize longer terms
    scored = sorted(freq.items(), key=lambda x: (len(x[0]), x[1]), reverse=True)
    return [term for term, _ in scored[:top_n]]


def _ccs(package: DraftPackage, gold: dict) -> tuple[float, dict[str, float]]:
    """③ 信息覆盖度评分，0-1，确定性计算。"""
    gold_claims = gold["ground_truth"]["claims"]
    gold_desc = gold["ground_truth"]["description_sections"]

    # Build gold noun set from claims features
    gold_nouns: set[str] = set()
    for c in gold_claims:
        for feat in c.get("features", []):
            gold_nouns |= _extract_nouns(feat)

    # Build gen text pool from claims features + description
    gen_text = ""
    if package.claims_struct:
        for c in package.claims_struct.claims:
            gen_text += " " + " ".join(c.features)
    if package.description:
        gen_text += " " + package.description

    gen_nouns = _extract_nouns(gen_text)

    # Key noun recall
    if gold_nouns:
        key_noun_recall = len(gold_nouns & gen_nouns) / len(gold_nouns)
    else:
        key_noun_recall = 1.0

    # Topic term recall
    gold_title = gold.get("title", "")
    gold_summary = gold_desc.get("summary", "")
    gold_topic = _extract_topic_terms(gold_title + " " + gold_summary)
    gen_desc = ""
    if package.description_struct:
        gen_desc = " ".join([
            package.description_struct.technical_field,
            package.description_struct.summary,
        ])
    gen_topic_terms = _extract_nouns(gen_desc, min_len=3)

    if gold_topic:
        topic_term_recall = len(set(gold_topic) & gen_topic_terms) / len(gold_topic)
    else:
        topic_term_recall = 1.0

    detail = {
        "key_noun_recall": round(key_noun_recall, 4),
        "topic_term_recall": round(topic_term_recall, 4),
    }
    score = 0.6 * key_noun_recall + 0.4 * topic_term_recall
    return round(score, 4), detail
```

- [ ] **Step 4: 运行 SAS/CCS 测试**

```bash
python3 -m pytest tests/test_golden_set_eval.py -q
```
Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/golden_eval.py tests/test_golden_set_eval.py
git commit -m "feat: add SAS and CCS scoring functions"
```

---

### Task 5: 实现 GoldenSetEvaluator 主类 + load/run/run_one

**Files:**
- Modify: `backend/app/golden_eval.py`（追加 `GoldenSetEvaluator` 类）
- Modify: `tests/test_golden_set_eval.py`（追加集成测试）

- [ ] **Step 1: 在 `test_golden_set_eval.py` 末尾追加集成测试**

```python
# --- GoldenSetEvaluator integration tests ---


def test_evaluator_loads_golden_set(tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps({
        "version": "v1", "created": "2026-06-08",
        "entries": [{"id": "CN-test-001", "title": "一种测试方法", "technical_field": "ai_software", "claims_count": 1}],
    }))
    (tmp_path / "CN-test-001.json").write_text(json.dumps(_sample_golden_entry()))

    evaluator = GoldenSetEvaluator(golden_set_dir=tmp_path)
    entries = evaluator.load_golden_set()
    assert len(entries) == 1
    assert entries[0]["id"] == "CN-test-001"


def test_evaluator_run_one_produces_eval_result(tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps({
        "version": "v1", "created": "2026-06-08",
        "entries": [{"id": "CN-test-001", "title": "一种测试方法", "technical_field": "ai_software", "claims_count": 1}],
    }))
    (tmp_path / "CN-test-001.json").write_text(json.dumps(_sample_golden_entry()))

    evaluator = GoldenSetEvaluator(golden_set_dir=tmp_path)
    entries = evaluator.load_golden_set()
    llm = FakeLLMClient({
        "claims": json.dumps({
            "claims": [
                {"number": 1, "kind": "independent", "category": "method", "depends_on": None,
                 "preamble": "一种测试方法，其特征在于，包括：", "features": ["采集数据", "输出结果"]}
            ]
        }),
        "description": json.dumps({
            "technical_field": "本发明涉及测试领域。",
            "background": "现有技术效率低。",
            "summary": "本发明提供一种测试方法。",
            "embodiments": "采集数据并输出结果。",
        }),
        "abstract": json.dumps({"abstract": "本发明公开了一种测试方法。"}),
        "drawings": json.dumps({"figures": [{"figure_no": "图1", "title": "方法流程图"}]}),
        "diagram": "flowchart TD\nA-->B",
        "image_prompt": "黑白线稿。",
    })
    generator = PatentDraftGenerator(llm)

    result = evaluator.run_one(entries[0], generator)
    assert isinstance(result, EvalPatentResult)
    assert result.gate_pass is True
    assert result.sas > 0.5
    assert result.ccs > 0.3


def test_evaluator_run_full(tmp_path):
    """End-to-end: load golden_set, run all, produce GoldenEvalReport."""
    entries_list = [_sample_golden_entry()]
    (tmp_path / "manifest.json").write_text(json.dumps({
        "version": "v1", "created": "2026-06-08",
        "entries": [{"id": e["id"], "title": e["title"], "technical_field": e["technical_field"], "claims_count": len(e["ground_truth"]["claims"])} for e in entries_list],
    }))
    for e in entries_list:
        (tmp_path / f"{e['id']}.json").write_text(json.dumps(e))

    evaluator = GoldenSetEvaluator(golden_set_dir=tmp_path)
    llm = FakeLLMClient({
        "claims": json.dumps({
            "claims": [
                {"number": 1, "kind": "independent", "category": "method", "depends_on": None,
                 "preamble": "一种测试方法，其特征在于，包括：", "features": ["采集数据", "输出结果"]}
            ]
        }),
        "description": json.dumps({
            "technical_field": "本发明涉及测试领域。",
            "background": "现有技术效率低。",
            "summary": "本发明提供一种测试方法。",
            "embodiments": "采集数据并输出结果。",
        }),
        "abstract": json.dumps({"abstract": "本发明公开了一种测试方法。"}),
        "drawings": json.dumps({"figures": [{"figure_no": "图1", "title": "方法流程图"}]}),
        "diagram": "flowchart TD\nA-->B",
        "image_prompt": "黑白线稿。",
    })
    generator = PatentDraftGenerator(llm)

    report = evaluator.run(generator)
    assert isinstance(report, GoldenEvalReport)
    assert len(report.per_patent) == 1
    assert report.summary.pass_ is True
    assert report.summary.warnings == 0
    assert report.golden_set_version == "v1"


def test_evaluator_handles_missing_golden_file(tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps({
        "version": "v1", "created": "2026-06-08",
        "entries": [{"id": "CN-missing", "title": "缺失", "technical_field": "ai_software", "claims_count": 1}],
    }))
    # Do not create CN-missing.json
    evaluator = GoldenSetEvaluator(golden_set_dir=tmp_path)
    entries = evaluator.load_golden_set()
    assert len(entries) == 0  # silently skipped


def test_evaluator_run_one_failure_does_not_stop_full_run(tmp_path):
    """If one patent fails gate, the rest still evaluate and report is produced."""
    good = _sample_golden_entry()
    (tmp_path / "manifest.json").write_text(json.dumps({
        "version": "v1", "created": "2026-06-08",
        "entries": [
            {"id": "CN-test-001", "title": "一种测试方法", "technical_field": "ai_software", "claims_count": 1},
            {"id": "CN-test-002", "title": "另一种测试", "technical_field": "ai_software", "claims_count": 1},
        ],
    }))
    (tmp_path / "CN-test-001.json").write_text(json.dumps(good))
    (tmp_path / "CN-test-002.json").write_text(json.dumps(good))

    evaluator = GoldenSetEvaluator(golden_set_dir=tmp_path)
    llm = FakeLLMClient({
        "claims": json.dumps({
            "claims": [
                {"number": 1, "kind": "independent", "category": "method", "depends_on": None,
                 "preamble": "一种测试方法，其特征在于，包括：", "features": ["采集数据", "输出结果"]}
            ]
        }),
        "description": json.dumps({
            "technical_field": "本发明涉及测试领域。",
            "background": "现有技术效率低。",
            "summary": "本发明提供一种测试方法。",
            "embodiments": "采集数据并输出结果。",
        }),
        "abstract": json.dumps({"abstract": "本发明公开了一种测试方法。"}),
        "drawings": json.dumps({"figures": [{"figure_no": "图1", "title": "方法流程图"}]}),
        "diagram": "flowchart TD\nA-->B",
        "image_prompt": "黑白线稿。",
    })
    generator = PatentDraftGenerator(llm)

    report = evaluator.run(generator)
    assert len(report.per_patent) == 2
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
python3 -m pytest tests/test_golden_set_eval.py -q
```
Expected: FAIL — `ImportError` for `GoldenSetEvaluator`

- [ ] **Step 3: 在 `golden_eval.py` 中追加 `GoldenSetEvaluator` 类**

```python
# --- GoldenSetEvaluator ---


class GoldenSetEvaluator:
    """Load a golden-set of authorized patents and evaluate a generator against them."""

    def __init__(self, golden_set_dir: Path) -> None:
        self.golden_set_dir = Path(golden_set_dir)

    # ---- loading ----

    def load_golden_set(self) -> list[dict]:
        """Load manifest and all referenced JSON files. Silently skips missing files."""
        manifest_path = self.golden_set_dir / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Golden-set manifest not found: {manifest_path}")

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        entries: list[dict] = []
        for entry in manifest.get("entries", []):
            patent_file = self.golden_set_dir / f"{entry['id']}.json"
            if not patent_file.exists():
                continue
            try:
                data = json.loads(patent_file.read_text(encoding="utf-8"))
                entries.append(data)
            except (json.JSONDecodeError, KeyError):
                continue
        return entries

    # ---- top-level ----

    def run(self, generator: PatentDraftGenerator) -> GoldenEvalReport:
        """Run evaluation on all golden-set entries and produce a report."""
        entries = self.load_golden_set()
        run_id = uuid.uuid4().hex[:12]
        per_patent: list[EvalPatentResult] = []

        for entry in entries:
            try:
                result = self.run_one(entry, generator)
            except Exception:
                result = EvalPatentResult(
                    patent_id=entry.get("id", "unknown"),
                    title=entry.get("title", "unknown"),
                    technical_field=entry.get("technical_field", "unknown"),
                    gate_pass=False,
                    gate_warnings=[f"unexpected error evaluating patent: {entry.get('id', 'unknown')}"],
                    sas=0.0,
                    ccs=0.0,
                )
            per_patent.append(result)

        n = len(per_patent)
        sas_avg = sum(r.sas for r in per_patent) / n if n > 0 else 0.0
        ccs_avg = sum(r.ccs for r in per_patent) / n if n > 0 else 0.0
        gate_pass_count = sum(1 for r in per_patent if r.gate_pass)
        gate_pass_rate = gate_pass_count / n if n > 0 else 0.0
        total_warnings = sum(len(r.gate_warnings) for r in per_patent)

        summary = GoldenEvalSummary(
            sas_avg=round(sas_avg, 4),
            ccs_avg=round(ccs_avg, 4),
            gate_pass_rate=round(gate_pass_rate, 4),
            pass_=sas_avg >= 0.6 and ccs_avg >= 0.5 and gate_pass_rate >= 0.9,
            warnings=total_warnings,
        )

        return GoldenEvalReport(
            run_id=run_id,
            commit="",
            golden_set_version="v1",
            summary=summary,
            per_patent=per_patent,
        )

    def run_one(self, entry: dict, generator: PatentDraftGenerator) -> EvalPatentResult:
        """Evaluate a single golden-set patent entry against the generator."""
        brief = _construct_invention_brief(entry)
        # Generate: pass empty context chunks (eval doesn't depend on RAG)
        package = generator.generate(brief, [])
        gate_pass, gate_warnings = _gate_check(package)
        sas_score, sas_detail = _sas(package, entry)
        ccs_score, ccs_detail = _ccs(package, entry)

        return EvalPatentResult(
            patent_id=entry["id"],
            title=entry["title"],
            technical_field=entry.get("technical_field", "unknown"),
            gate_pass=gate_pass,
            gate_warnings=gate_warnings,
            sas=sas_score,
            sas_detail=sas_detail,
            ccs=ccs_score,
            ccs_detail=ccs_detail,
            llm_judge=None,  # populated in Task 7
        )
```

- [ ] **Step 4: 运行全部 golden_eval 测试**

```bash
python3 -m pytest tests/test_golden_set_eval.py -q
```
Expected: 16 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/golden_eval.py tests/test_golden_set_eval.py
git commit -m "feat: add GoldenSetEvaluator main class with load/run/run_one"
```

---

### Task 6: 回归验证 + 全量测试

**Files:** （不改文件，仅运行验证）

- [ ] **Step 1: 跑全量后端测试，确保 130+golden_eval 全绿**

```bash
python3 -m pytest -q
```
Expected: all passing (130 existing + 16 golden_eval = 146+)

- [ ] **Step 2: 运行 imports 校验**

```bash
python3 -c "import backend.app.golden_eval; print('golden_eval imports OK')"
python3 -c "from backend.app.schemas import EvalPatentResult, GoldenEvalSummary, GoldenEvalReport; print('schemas imports OK')"
```
Expected: both `OK`

---

### Task 7: LLM-as-Judge 评分器

**Files:**
- Modify: `backend/app/golden_eval.py`（追加 `_llm_judge` 函数，在 `run_one` 中集成）
- Modify: `tests/test_golden_set_eval.py`（追加 judge 测试，用 `llm_judge` 标记）

- [ ] **Step 1: 在 `test_golden_set_eval.py` 末尾追加 LLM-Judge 测试**

```python
# --- LLM-Judge tests (marked llm_judge) ---


@pytest.mark.llm_judge
def test_llm_judge_produces_score_dict(tmp_path):
    """Integration test: run LLM judge against a real or fake judge LLM."""
    (tmp_path / "manifest.json").write_text(json.dumps({
        "version": "v1", "created": "2026-06-08",
        "entries": [{"id": "CN-test-001", "title": "一种测试方法", "technical_field": "ai_software", "claims_count": 1}],
    }))
    (tmp_path / "CN-test-001.json").write_text(json.dumps(_sample_golden_entry()))

    # Fake judge LLM returns plausible scores
    judge_llm = FakeLLMClient({
        "clarity": json.dumps({"score_a": 4, "score_b": 3, "reason_a": "清晰", "reason_b": "边界模糊"}),
        "support": json.dumps({"score_a": 4, "score_b": 3, "reason_a": "有支撑", "reason_b": "支撑不足"}),
        "effect": json.dumps({"score_a": 4, "score_b": 3, "reason_a": "效果明确", "reason_b": "效果笼统"}),
        "cleanliness": json.dumps({"score_a": 5, "score_b": 5, "reason_a": "无污染", "reason_b": "无污染"}),
    })

    evaluator = GoldenSetEvaluator(golden_set_dir=tmp_path, judge_llm=judge_llm)
    entries = evaluator.load_golden_set()
    llm = FakeLLMClient({
        "claims": json.dumps({
            "claims": [
                {"number": 1, "kind": "independent", "category": "method", "depends_on": None,
                 "preamble": "一种测试方法，其特征在于，包括：", "features": ["采集数据", "输出结果"]}
            ]
        }),
        "description": json.dumps({
            "technical_field": "本发明涉及测试领域。",
            "background": "现有技术效率低。",
            "summary": "本发明提供一种测试方法。",
            "embodiments": "采集数据并输出结果。",
        }),
        "abstract": json.dumps({"abstract": "本发明公开了一种测试方法。"}),
        "drawings": json.dumps({"figures": [{"figure_no": "图1", "title": "方法流程图"}]}),
        "diagram": "flowchart TD\nA-->B",
        "image_prompt": "黑白线稿。",
    })
    generator = PatentDraftGenerator(llm)

    report = evaluator.run(generator)
    result = report.per_patent[0]
    assert result.llm_judge is not None
    assert "clarity" in result.llm_judge
    # Each dimension produces a float score from gen side
    assert isinstance(result.llm_judge["clarity"], float)
    assert result.llm_judge["clarity"] >= 1.0
    assert result.llm_judge["cleanliness"] == 5.0
    assert report.summary.llm_judge_avg is not None


def test_llm_judge_skipped_when_judge_llm_is_none(tmp_path):
    """When judge_llm is None, _llm_judge returns None and run_one sets llm_judge=None."""
    (tmp_path / "manifest.json").write_text(json.dumps({
        "version": "v1", "created": "2026-06-08",
        "entries": [{"id": "CN-test-001", "title": "一种测试方法", "technical_field": "ai_software", "claims_count": 1}],
    }))
    (tmp_path / "CN-test-001.json").write_text(json.dumps(_sample_golden_entry()))

    evaluator = GoldenSetEvaluator(golden_set_dir=tmp_path, judge_llm=None)
    entries = evaluator.load_golden_set()
    llm = FakeLLMClient({
        "claims": json.dumps({"claims": [
            {"number": 1, "kind": "independent", "category": "method", "depends_on": None,
             "preamble": "一种测试方法，其特征在于，包括：", "features": ["采集数据", "输出结果"]}
        ]}),
        "description": json.dumps({"technical_field": "本发明涉及测试领域。", "background": "现有技术效率低。", "summary": "本发明提供一种测试方法。", "embodiments": "采集数据并输出结果。"}),
        "abstract": json.dumps({"abstract": "本发明公开了一种测试方法。"}),
        "drawings": json.dumps({"figures": [{"figure_no": "图1", "title": "方法流程图"}]}),
        "diagram": "flowchart TD\nA-->B",
        "image_prompt": "黑白线稿。",
    })
    generator = PatentDraftGenerator(llm)

    report = evaluator.run(generator)
    result = report.per_patent[0]
    assert result.llm_judge is None
    assert report.summary.llm_judge_avg is None
```

- [ ] **Step 2: 运行测试，确认 judge 测试失败**

```bash
python3 -m pytest tests/test_golden_set_eval.py -m "not llm_judge" -q
```
Expected: 16 passed (judge tests skipped with `-m "not llm_judge"`)

```bash
python3 -m pytest tests/test_golden_set_eval.py -m "llm_judge" -q
```
Expected: FAIL — `GoldenSetEvaluator.__init__` missing `judge_llm` parameter

- [ ] **Step 3: 修改 `golden_eval.py`——更新 `__init__` + 追加 `_llm_judge` + 修改 `run_one`**

在 `GoldenSetEvaluator.__init__` 中添加 `judge_llm` 参数：

```python
class GoldenSetEvaluator:
    def __init__(self, golden_set_dir: Path, judge_llm: LLMClient | None = None) -> None:
        self.golden_set_dir = Path(golden_set_dir)
        self.judge_llm = judge_llm
```

在文件末尾追加 `_llm_judge` 函数：

```python
# --- LLM-as-Judge (optional, requires EVAL_LLM_API_KEY) ---

_JUDGE_DIMENSIONS = {
    "clarity": ("清楚", "专利法第26条第4款：权利要求应当清楚地限定要求专利保护的范围。评分标准：5=权项边界清晰、特征无歧义、步骤顺序明确；1=功能性概括、缺少步骤顺序、输入输出不明确。"),
    "support": ("支持", "实施细则第20条第2款：独立权利要求应当从整体上反映发明或者实用新型的技术方案，记载解决技术问题的必要技术特征。说明书应当充分公开发明。评分标准：5=每个权项特征在说明书中有明确对应实施例；1=权项特征在说明书中无对应段落。"),
    "effect": ("技术效果", "审查指南第二部分第四章：发明或者实用新型的技术效果应当是技术方案必然产生的，或者由实验数据证明的。评分标准：5=有益效果具体、与区别特征明确关联；1=定性空洞、定量无据。"),
    "cleanliness": ("清洁度", "系统独有维度：生成文本应不含AI开场白、meta段落、样板签名或内部会审痕迹。评分标准：5=完全清洁，无任何污染；1=含大量AI痕迹或内部meta。"),
}

_JUDGE_SYSTEM_PROMPT = (
    "你是CNIPA发明专利实质审查员，熟悉审查指南。"
    "请对以下两段专利文本进行双盲对比评分，你不知道哪段是生成文本、哪段是授权文本。"
    "只输出JSON：{\"score_a\": N, \"score_b\": N, \"reason_a\": \"...\", \"reason_b\": \"...\"}"
)


def _llm_judge(
    gen_text: str,
    gold_text: str,
    dimension: str,
    domain_keywords: str,
    judge_llm: LLMClient,
) -> float | None:
    """④ Run a single-dimension LLM-as-Judge double-blind scoring. Returns the gen-side score (1-5)."""
    if dimension not in _JUDGE_DIMENSIONS:
        return None

    dim_label, guideline = _JUDGE_DIMENSIONS[dimension]

    # Shuffle: randomly assign gen/gold to A/B
    import random
    is_swapped = random.choice([True, False])
    text_a = gold_text if is_swapped else gen_text
    text_b = gen_text if is_swapped else gold_text

    user_prompt = (
        f"【评分维度】{dim_label}\n"
        f"【审查指南依据】{guideline}\n"
        f"【技术领域关键词】{domain_keywords}\n\n"
        f"【文本A】\n{text_a[:3000]}\n\n"
        f"【文本B】\n{text_b[:3000]}"
    )

    try:
        payload = judge_llm.complete_stage_json(dimension, _JUDGE_SYSTEM_PROMPT, user_prompt)
        score_a = float(payload.get("score_a", 0))
        score_b = float(payload.get("score_b", 0))
        # Return gen-side score (un-swap)
        return float(score_b if is_swapped else score_a)
    except Exception:
        return None
```

修改 `run_one` 方法，在 return 前追加 judge 调用：

```python
    def run_one(self, entry: dict, generator: PatentDraftGenerator) -> EvalPatentResult:
        # ... existing code ...

        # LLM-Judge (optional)
        llm_judge: dict[str, float | None] | None = None
        if self.judge_llm is not None:
            gen_claims = package.claims
            gold_claims_text = "\n".join(
                f"{c['number']}. {c.get('preamble', '')} {' '.join(c.get('features', []))}"
                for c in entry["ground_truth"]["claims"]
            )
            domain_keywords = ", ".join(_extract_topic_terms(
                entry.get("title", "") + " " + entry["ground_truth"]["description_sections"].get("technical_field", "")
            ))
            llm_judge = {}
            for dim in ["clarity", "support", "effect", "cleanliness"]:
                gold_text = gold_claims_text if dim in ("clarity", "cleanliness") else (
                    entry["ground_truth"]["description_sections"].get("summary", "")
                    + " " + entry["ground_truth"]["description_sections"].get("embodiments", "")
                )
                gen_text = gen_claims if dim in ("clarity", "cleanliness") else (
                    (package.description_struct.summary if package.description_struct else "")
                    + " " + (package.description_struct.embodiments if package.description_struct else "")
                )
                llm_judge[dim] = _llm_judge(gen_text, gold_text, dim, domain_keywords, self.judge_llm)

        return EvalPatentResult(
            # ... existing fields ...
            llm_judge=llm_judge,
        )
```

同时修改 `run` 方法，在 summary 中聚合 `llm_judge_avg`：

```python
    def run(self, generator: PatentDraftGenerator) -> GoldenEvalReport:
        # ... existing code above summary ...

        # Aggregate LLM-Judge averages
        llm_judge_avg: dict[str, float] | None = None
        if self.judge_llm is not None:
            dims = ["clarity", "support", "effect", "cleanliness"]
            llm_judge_avg = {}
            for dim in dims:
                scored = [r.llm_judge[dim] for r in per_patent if r.llm_judge and r.llm_judge.get(dim) is not None]
                llm_judge_avg[dim] = round(sum(scored) / len(scored), 2) if scored else 0.0

        summary = GoldenEvalSummary(
            # ... existing fields ...
            llm_judge_avg=llm_judge_avg,
        )
        # ...
```

- [ ] **Step 4: 运行 judge 测试**

```bash
python3 -m pytest tests/test_golden_set_eval.py -m "llm_judge" -q
```
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/golden_eval.py tests/test_golden_set_eval.py
git commit -m "feat: add LLM-as-Judge scoring with double-blind evaluation"
```

---

### Task 8: CI 集成 + pytest 标记

**Files:**
- Create: `.github/workflows/eval.yml`
- Modify: `pyproject.toml`

- [ ] **Step 1: 在 `pyproject.toml` 中添加 pytest 标记**

```ini
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
markers = [
    "golden_eval: golden-set evaluation tests",
    "llm_judge: LLM-as-Judge tests (require EVAL_LLM_API_KEY)",
]
```

- [ ] **Step 2: 创建 `.github/workflows/eval.yml`**

```yaml
name: Golden-set Evaluation

on:
  pull_request:
    paths:
      - 'backend/app/generator.py'
      - 'backend/app/llm.py'
      - 'backend/app/schemas.py'
      - 'golden_set/v1/**'
  workflow_dispatch:

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

- [ ] **Step 3: 验证 pytest 标记生效**

```bash
python3 -m pytest tests/test_golden_set_eval.py --collect-only -q
```
Expected: 18 tests collected (16 unmarked + 2 llm_judge)

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml .github/workflows/eval.yml
git commit -m "feat: add CI workflow for golden-set evaluation (fast + judge)"
```

---

### Task 9: Golden-set 抓取脚本（可选，E1 补充——17 篇补齐到 20 篇）

**Files:**
- Create: `scripts/scrape_golden_set.py`

> **Note:** 此任务为可选项。E2-E5 可在 3 篇示例数据上开发与验证。完整 20 篇 golden-set 的抓取由本脚本完成后补充。

- [ ] **Step 1: 创建抓取脚本骨架**

```python
#!/usr/bin/env python3
"""Scrape authorized CNIPA patents for golden-set construction.

Usage: python3 scripts/scrape_golden_set.py --count 17 --output golden_set/v1/

Currently implements manual entry: prompts the operator to search CNIPA
or Google Patents, paste the patent text, and the script formats it as
the standard golden-set JSON schema.
"""

import json
import re
import sys
from pathlib import Path


def prompt_patent(index: int) -> dict:
    """Interactive prompt for one patent."""
    print(f"\n{'='*60}")
    print(f"Patent #{index}")
    print(f"{'='*60}")

    patent_id = input("Patent ID (e.g. CN202310000001B): ").strip()
    title = input("Title: ").strip()
    tech = input("Technical field [ai_software/mechanical/electronics/chemical]: ").strip()

    print("\nPaste description_full (技术领域\\n背景技术\\n发明内容\\n具体实施方式). End with '###':")
    desc_lines = []
    while True:
        line = input()
        if line.strip() == "###":
            break
        desc_lines.append(line)
    description_full = "\n".join(desc_lines)

    print("\nPaste drawings_description. End with '###':")
    drawings_lines = []
    while True:
        line = input()
        if line.strip() == "###":
            break
        drawings_lines.append(line)
    drawings_description = "\n".join(drawings_lines)

    print("\nPaste claims (one per line, format: 'N|kind|category|depends_on|preamble|feature1;feature2'). End with '###':")
    claims = []
    while True:
        line = input()
        if line.strip() == "###":
            break
        parts = line.strip().split("|")
        if len(parts) >= 6:
            claims.append({
                "number": int(parts[0]),
                "kind": parts[1],
                "category": parts[2],
                "depends_on": int(parts[3]) if parts[3] and parts[3] != "null" else None,
                "preamble": parts[4],
                "features": [f.strip() for f in parts[5].split(";") if f.strip()],
            })

    print("\nPaste description_sections as JSON {technical_field, background, summary, embodiments}:")
    desc_sections = json.loads(input())

    print("\nPaste figures as JSON [{figure_no, title}, ...]:")
    figures = json.loads(input())

    return {
        "id": patent_id,
        "title": title,
        "technical_field": tech,
        "publication_date": "",
        "claims_count": len(claims),
        "input": {
            "description_full": description_full,
            "drawings_description": drawings_description,
        },
        "ground_truth": {
            "claims": claims,
            "description_sections": desc_sections,
            "figures": figures,
        },
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Scrape golden-set patents")
    parser.add_argument("--count", type=int, default=17)
    parser.add_argument("--output", type=str, default="golden_set/v1/")
    args = parser.parse_args()

    out_dir = Path(args.output)
    manifest_path = out_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {"version": "v1", "entries": []}

    for i in range(1, args.count + 1):
        patent = prompt_patent(i)
        patent_file = out_dir / f"{patent['id']}.json"
        patent_file.write_text(json.dumps(patent, ensure_ascii=False, indent=2), encoding="utf-8")
        manifest["entries"].append({
            "id": patent["id"],
            "title": patent["title"],
            "technical_field": patent["technical_field"],
            "claims_count": patent["claims_count"],
        })
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  → saved {patent_file}")

    print(f"\nDone. {len(manifest['entries'])} patents in {out_dir}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add scripts/scrape_golden_set.py
git commit -m "feat: add interactive golden-set patent scraper"
```

---

### Task 10: 最终回归验证

**Files:** （不改文件，仅运行验证）

- [ ] **Step 1: 全量后端测试**

```bash
python3 -m pytest -q
```
Expected: all tests pass (130 existing + 18 golden_eval = 148)

- [ ] **Step 2: 快速评测门禁**

```bash
python3 -m pytest tests/test_golden_set_eval.py -m "not llm_judge" -q
```
Expected: 16 passed

- [ ] **Step 3: 验证 CI workflow YAML 语法**

```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/eval.yml')); print('YAML OK')"
```
(Note: may need `pip install pyyaml` if not available)

- [ ] **Step 4: 跑已有 130 测试确保不受影响**

```bash
python3 -m pytest tests/ -q --ignore=tests/test_golden_set_eval.py
```
Expected: 130 passed

- [ ] **Step 5: Commit 并推送**

```bash
git add -A
git commit -m "chore: final verification — all tests pass with golden-eval suite"
git push
```
