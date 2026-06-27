# 一种基于语义对比和增量聚类的发明点提炼方法及装置

## 前置材料摘要
一种面向企业专利撰写的本地化智能代理系统，通过材料解析、发明点提炼、权利要求会审和正式稿编译等处理环节，智能化地生成专利文件，以降低重复性撰写工作并保留全流程可追溯证据。


> **检索置信度**：🔴 低
>
> 低置信度表示未检索到可引用的公开现有技术文献；交底书不隐含高专利性判断。

## 材料覆盖
仅提供一段概括性说明，未包含补充材料；未描述系统架构、模块划分、数据处理流程及具体实现手段。

## 候选专利点
- p1 基于多级语义匹配的材料解析与发明构思提取方法：采用段落级意图分类与句级依存分析相结合的两级语义匹配方法，将非结构化的交底材料自动解析为技术领域、背景问题、技术方案、区别特征和有益效果等专利逻辑单元，并同步生成可追溯的解析溯源图。
  证据状态：model_generated
  来源：model
  可行依据：未填写
  支撑缺口：无显式缺口
  护城河评分：0.0
- p2 一种基于语义对比和增量聚类的发明点提炼方法及装置：融合预训练语言模型与专利知识图谱，通过将初步特征与已有专利文本进行语义对比，并采用增量聚类算法动态确定发明点，同时生成包含提炼依据、对比结果和特征权重的可解释提炼报告。
  证据状态：model_generated
  来源：model
  可行依据：未填写
  支撑缺口：无显式缺口
  护城河评分：0.0
- p3 融合人工反馈与自动比对的权利要求会审方法：构建一种人机协同的权利要求会审方法，将自动提取的发明点与代理人撰写的权利要求草案进行特征覆盖度比对，并结合版本控制模型实时记录人工修订、注释与批注，形成可回滚的会审流。
  证据状态：model_generated
  来源：model
  可行依据：未填写
  支撑缺口：无显式缺口
  护城河评分：0.0
- p4 基于版本化知识图谱的专利撰写全过程可追溯证据生成方法：以版本化知识图谱为核心，将材料解析、发明点提炼、权利要求会审和正式稿编译各阶段产生的数据、操作和决策作为节点关联起来，并通过哈希链保证不可篡改，实现从最终专利文本回溯至原始交底材料的全链路证据留存。
  证据状态：model_generated
  来源：model
  可行依据：未填写
  支撑缺口：无显式缺口
  护城河评分：0.0

## Claim Chart
暂无。

## 公开现有技术
暂无可用公开检索结果。

## 现有技术差异
未获得可用公开现有技术结果；交底书仅基于本地材料和授权专利语料生成。
## 检索来源台账

- 总命中数：0
- 总引用数：0

| 来源 | 类型 | 检索词 | 状态 | 命中 | 保留 | 失败原因 |
|------|------|--------|------|------|------|----------|
| cnipa | patent | 语义对比 发明点 提炼 | ⏭️ skipped | 0 | 0 | CNIPA EPUB helper is not configured; set CNIPA_EPUB_SEARCH_S |
| cnipa | patent | 增量聚类 技术特征 | ⏭️ skipped | 0 | 0 | CNIPA EPUB helper is not configured; set CNIPA_EPUB_SEARCH_S |
| cnipa | patent | 专利知识图谱 对比学习 | ⏭️ skipped | 0 | 0 | CNIPA EPUB helper is not configured; set CNIPA_EPUB_SEARCH_S |
| cnipa | patent | 新颖性得分 生成 | ⏭️ skipped | 0 | 0 | CNIPA EPUB helper is not configured; set CNIPA_EPUB_SEARCH_S |
| cnipa | patent | 可解释 提炼报告 | ⏭️ skipped | 0 | 0 | CNIPA EPUB helper is not configured; set CNIPA_EPUB_SEARCH_S |
| cnipa | patent | 可追溯 提炼卡片 | ⏭️ skipped | 0 | 0 | CNIPA EPUB helper is not configured; set CNIPA_EPUB_SEARCH_S |
| google_patents | patent | 语义对比 发明点 提炼 | ❌ failed | 0 | 0 | Google Patents fallback failed for term 语义对比 发明点 提炼: HTTP Er |
| google_patents | patent | 增量聚类 技术特征 | ❌ failed | 0 | 0 | Google Patents fallback failed for term 增量聚类 技术特征: HTTP Erro |
| google_patents | patent | 专利知识图谱 对比学习 | ❌ failed | 0 | 0 | Google Patents fallback failed for term 专利知识图谱 对比学习: HTTP Er |
| google_patents | patent | 新颖性得分 生成 | ❌ failed | 0 | 0 | Google Patents fallback failed for term 新颖性得分 生成: HTTP Error |

## 检索链路诊断

### 🔍 检索前

- 可用来源：google_patents、patent
- 跳过来源：
  - cnipa：CNIPA EPUB helper is not configured; set CNIPA_EPUB_SEARCH_SCRIPT to enable live CNIPA search.

### 📊 检索后

- 可用来源：无
- 跳过来源：
  - cnipa：CNIPA EPUB helper is not configured; set CNIPA_EPUB_SEARCH_SCRIPT to enable live CNIPA search.
  - cnipa：CNIPA EPUB helper is not configured; set CNIPA_EPUB_SEARCH_SCRIPT to enable live CNIPA search.
  - cnipa：CNIPA EPUB helper is not configured; set CNIPA_EPUB_SEARCH_SCRIPT to enable live CNIPA search.
  - cnipa：CNIPA EPUB helper is not configured; set CNIPA_EPUB_SEARCH_SCRIPT to enable live CNIPA search.
  - cnipa：CNIPA EPUB helper is not configured; set CNIPA_EPUB_SEARCH_SCRIPT to enable live CNIPA search.
  - cnipa：CNIPA EPUB helper is not configured; set CNIPA_EPUB_SEARCH_SCRIPT to enable live CNIPA search.
- 警告：
  - google_patents failed: Google Patents fallback failed for term 语义对比 发明点 提炼: HTTP Error 503: Service Unavailable
  - google_patents failed: Google Patents fallback failed for term 增量聚类 技术特征: HTTP Error 503: Service Unavailable
  - google_patents failed: Google Patents fallback failed for term 专利知识图谱 对比学习: HTTP Error 503: Service Unavailable
  - google_patents failed: Google Patents fallback failed for term 新颖性得分 生成: HTTP Error 503: Service Unavailable
  - cnipa skipped: CNIPA EPUB helper is not configured; set CNIPA_EPUB_SEARCH_SCRIPT to enable live CNIPA search.
  - cnipa skipped: CNIPA EPUB helper is not configured; set CNIPA_EPUB_SEARCH_SCRIPT to enable live CNIPA search.
  - cnipa skipped: CNIPA EPUB helper is not configured; set CNIPA_EPUB_SEARCH_SCRIPT to enable live CNIPA search.
  - cnipa skipped: CNIPA EPUB helper is not configured; set CNIPA_EPUB_SEARCH_SCRIPT to enable live CNIPA search.
  - cnipa skipped: CNIPA EPUB helper is not configured; set CNIPA_EPUB_SEARCH_SCRIPT to enable live CNIPA search.
  - cnipa skipped: CNIPA EPUB helper is not configured; set CNIPA_EPUB_SEARCH_SCRIPT to enable live CNIPA search.
  - google_patents failed: Google Patents fallback failed for term 语义对比 发明点 提炼: HTTP Error 503: Service Unavailable
  - google_patents failed: Google Patents fallback failed for term 增量聚类 技术特征: HTTP Error 503: Service Unavailable
  - google_patents failed: Google Patents fallback failed for term 专利知识图谱 对比学习: HTTP Error 503: Service Unavailable
  - google_patents failed: Google Patents fallback failed for term 新颖性得分 生成: HTTP Error 503: Service Unavailable

## 技术交底书
# 中国发明专利技术交底书

## 注意事项

1.  **文档性质声明**：本文档为技术交底书草案，旨在向专利代理人或律师充分披露发明的技术实质，以支持后续的专利申请文件撰写和审查。本文档不构成正式的法律意见，最终的专利保护范围以授权的权利要求书为准。
2.  **技术术语一致性**：本文档中使用的技术术语，如“技术特征”、“语义向量”、“增量聚类”、“提炼卡片”等，应在后续的正式申请文件中保持概念和用词的一致性，避免歧义。
3.  **发明点聚焦**：本交底书围绕“一种基于语义对比和增量聚类的发明点提炼方法及装置”这一核心发明点展开。应确保该点的描述具备突出的实质性特点和显著的进步，并与代理系统其他环节（如材料解析、权利要求会审）的描述清晰区分。
4.  **现有技术引用**：由于在交底准备阶段未获取到公开的现有技术文件，本交底书中指出的“最接近现有技术”是基于行业通用实践进行概括性描述的。申请前，建议进行补充检索，以更精确地界定现有技术，从而突出本发明的创新性。
5.  **补充信息义务**：请在审阅后，根据“六、可选实施例、变形例和补充材料需求”部分的提示，补充相关的实验数据、对比示例、具体参数和可选实施方式，以增强技术方案的完整性和授权可能性。

## 一、相关技术背景

### 1.1 最接近现有技术和公开URL
在当前的专利撰写实践中，特别是在企业内部处理大量、持续产出的技术交底材料时，发明点的提炼主要依赖人工处理流程。其技术实现手段通常为：
-   **基于规则和关键词的文档比对系统**：利用正则表达式或关键词匹配技术，从交底书中提取技术术语，并与内部专利数据库进行字面比对，以标记已知技术词汇。
-   **人工协作与版本管理工具**：利用通用的办公软件（如文字处理器和表格工具）或简单的版本管理系统，由多名专利工程师协作，通过批注、高亮和手动分类来梳理和确定发明点。

最接近现有技术实质上是一种 **“基于人工经验和浅层特征匹配的发明点识别方法”**。
由于此为行业通用实践，不属于公开专利文献，故无特定公开URL。但其技术表现可参考各种通用的文档比对软件和协作平台的基础功能。

### 1.2 现有技术缺点
上述基于人工经验和浅层匹配的方法，在实际应用中存在以下显著技术缺点：

1.  **提炼过程主观性强，一致性差**：不同的专利工程师基于其知识背景和经验，对同一份材料可能提炼出截然不同的发明点。缺乏客观、可量化的技术评判标准，导致发明点的确定存在个体偏差，影响专利组合的质量和稳定性。
2.  **处理效率低下，无法适应动态输入**：人工阅读、理解并比对一个技术方案，耗时巨大。特别是在“边撰写边补充”的企业场景中，每轮新材料或修改稿的加入，都要求工程师全局性地重新审视和调整发明点，形成循环往复的低效工作流。系统无法支持增量式的动态输入与实时更新。
3.  **提炼逻辑不可追溯，证据链缺失**：最终确定的一个或多个发明点，其形成过程（例如，为何某个特征被认定为关键，为何某几个特征被归为一个发明点）仅存在于工程师的思维中，没有系统化的记录。这导致在后续的权利要求会审、正式稿编译乃至专利无效或诉讼程序中，缺乏支撑“提炼合理性”的可追溯证据。
4.  **深层次语义理解能力不足**：基于关键词或规则的方法只能捕捉字面上的相似性，无法理解技术特征的深层语义和上下文关联。例如，无法识别“利用卷积神经网络提取图像特征”和“基于CNN模型获取视觉信息”在语义上实质相同，从而导致新颖性判断失准。

## 二、要解决的技术问题
本发明旨在解决现有技术中，因依赖人工经验和浅层特征匹配而导致的专利发明点提炼过程中存在主观性强、效率低下、无法适应动态增量输入，以及提炼逻辑不可追溯的技术问题。

具体地，本发明要提供一种自动、客观、可解释的发明点提炼方法及装置，能够：
1.  从技术交底材料中精准抽取技术特征，并基于语义层面对其进行新颖性评估。
2.  支持增量式的特征输入，并动态地聚类生成发明点，无需因材料更新而全局重算。
3.  为提炼出的每一个发明点，生成包含来源、对比依据和量化贡献度的可追溯证据报告。

## 三、详细技术方案

### 3.1 系统结构
本发明提供一种基于语义对比和增量聚类的发明点提炼装置，该装置可作为一个独立模块部署在本地化智能代理系统中。其内部结构包括：

*   **101：特征获取模块**：用于从输入的技术交底材料中抽取候选技术特征集合。
*   **102：语义对比模块**：内部集成一个基于Transformer的预训练语言模型和一个专利知识图谱。用于计算每一个候选技术特征与专利知识图谱中相关专利文献文本的语义相似度，并生成新颖性得分。
*   **103：增量聚类模块**：用于以新颖性得分作为初始化权重，对候选技术特征序列执行增量聚类算法，动态确定一个或多个发明点聚类。
*   **104：结果生成模块**：用于针对每个确定的发明点聚类，生成一个结构化的可追溯提炼卡片。

**数据流**：原始交底材料 -> **101** -> 候选技术特征集 -> **102** -> 带新颖性得分的特征序列 -> **103** -> 发明点聚类结果 -> **104** -> 可追溯提炼卡片清单。

### 3.2 模块功能与方法流程
本发明方法的具体步骤如下：

**步骤S1：获取技术特征集合**
特征获取模块（101）接收输入的技术交底材料（可以是初次输入或后续补充的材料片段），通过自然语言处理技术，如依存句法分析、命名实体识别和预定义的专利特征模板，从中抽取出结构化的候选技术特征序列 **F = {f1, f2, ..., fn}**。
*例如，从文本“采用了一种基于Transformer的对比学习模型，计算语义相似度，输出新颖性得分”中，可能抽取出特征 `f1 = (手段：对比学习模型；作用对象：语义特征；效果：生成新颖性得分)`。*

**步骤S2：计算语义相似度与新颖性得分**
语义对比模块（102）对序列 **F** 中的每个特征 **fi**，执行以下子步骤：
1.  **查询构建**：利用所述预训练语言模型将 **fi** 编码为语义向量 **Vi**。同时，根据 **fi** 的关键词和技术领域，在专利知识图谱中进行检索，获取一组相关的现有专利文献片段集合 **D = {d1, d2, ..., dm}**，并将它们编码为语义向量集合 **{Vd1, Vd2, ..., Vdm}**。
2.  **语义对比**：在一个共享的语义向量空间中，计算 **Vi** 与 **Vdj** (j=1..m) 之间的余弦相似度 `Similarity(Vi, Vdj)`。
3.  **生成新颖性得分**：取所有相似度中的最大值作为特征 **fi** 的“最相关现有技术相似度”，然后通过一个单调递减函数生成新颖性得分 **S(fi)**。
    *公式示例：`S(fi) = 1 - Max(Similarity(Vi, Vdj) for dj in D)`。* 该得分越高，表明该特征相对于现有技术的语义差异越大，新颖性潜力越高。

**步骤S3：增量聚类动态确定发明点**
增量聚类模块（103）负责处理带权重的特征序列。其输入为按步骤S1顺序获取的、经步骤S2计算过的特征元组 `<f, S(f)>`。该模块采用增量聚类算法，具体过程为：
1.  **初始化**：设定聚类中心紧凑度阈值 **δ** 和聚类间分离度阈值 **ε**。
2.  **逐个处理**：对于每个新到达的特征 **f_new** 及其得分 **S(f_new)**：
    a. **权重映射**：将 **S(f_new)** 映射为该特征在聚类中的初始权重 **w_new**。新颖性得分越高，权重越大，对聚类中心的影响力越强。
    b. **寻找最近聚类**：计算 **f_new** 的语义向量与当前所有活跃聚类中心点 **C_k** 的语义距离。
    c. **决策与更新**：
        *   **情况一（归属）**：若与最近聚类中心的距离小于 **δ**，则将 **f_new** 分配到该聚类。并以加权方式动态更新该聚类的中心点：`C_new = C_old * (1 - α*w_new) + V_new * (α*w_new)`，其中 `α` 为学习率。
        *   **情况二（新建）**：若与所有聚类中心的距离均大于 **δ**，则以其语义向量 **V_new** 为初始中心，创建一个新的聚类。
3.  **发明点判定**：在所有特征处理完毕后，对各个聚类进行评定。一个聚类被判定为一个有效“发明点”，需满足：聚类内部紧凑度（成员间平均相似度）高于预设阈值，并且其中心点到其他任何聚类中心的距离（簇间分离度）大于 **ε**。未能满足条件的聚类可被视为噪声或被合并。

**步骤S4：生成可追溯提炼卡片**
结果生成模块（104）为通过步骤S3判定的每个发明点聚类，生成一个结构化的可追溯提炼卡片。该卡片是一个包含以下元数据的数据结构：
*   **发明点标识**：一个用于区分不同发明的唯一ID。
*   **核心特征描述**：基于聚类中心点生成的自然语言摘要。
*   **原始特征来源清单**：组成该聚类的所有特征 **f_i** 在原始交底材料中的位置引用（如段落、句子索引）。
*   **最相似专利片段**：引用自步骤S2中，与聚类中心点或核心特征相似度最高的现有专利文献片段，作为新颖性对比的客观证据。
*   **特征贡献度列表**：列出聚类内每个特征 **f_i**，并附上其新颖性得分 **S(f_i)** 和它对更新聚类中心的相对贡献值，以量化展示每个特征的重要性，解决了“为何这些特征被归为一个发明点”的可解释性问题。

### 3.3 关键参数与数据结构

*   **关键参数**：
    *   `δ` (聚类中心紧凑度阈值)：控制聚类内部主题的聚合程度，直接影响发明点划分的粒度。
    *   `ε` (簇间分离度阈值)：确保不同发明点之间具有足够的技术区别。
    *   `α` (聚类中心更新学习率)：控制新旧特征对发明点概念漂移的影响程度。
    *   `S(f)` (新颖性得分) 的计算函数：决定特征权重的初始化方式。

*   **关键数据结构——可追溯提炼卡片**:
```
{
  "invention_point_id": "IP-2024-001-03",
  "core_description": "一种基于语义向量对比和加权增量聚类，动态生成可解释发明点的方法。",
  "source_features": [
    {"feature_id": "f5", "snippet": "计算语义相似度...", "position_in_doc": "段落[0032]"},
    {"feature_id": "f8", "snippet": "以新颖性得分为初始化权重...", "position_in_doc": "段落[0034]"}
  ],
  "most_similar_prior_art": {
    "patent_id": "CNXXXXXXA",
    "relevant_snippet": "通过计算向量空间距离评价技术方案相似度。",
    "similarity_score": 0.82
  },
  "feature_contributions": [
    {"feature_id": "f5", "novelty_score": 0.35, "cluster_contribution": 0.22},
    {"feature_id": "f8", "novelty_score": 0.91, "cluster_contribution": 0.78}
  ],
  "generation_timestamp": "2024-05-20T10:30:00Z"
}
```

## 四、相对于现有技术的有益效果

1.  **自动化与客观性**：通过基于语义向量和新颖性得分的量化计算，替代了传统的人工主观判断。发明的提炼过程由数据驱动，结果不再依赖于个别工程师的经验或认知偏差，确保了提炼标准的一致性和客观性。
2.  **动态增量处理能力**：本方案中的增量聚类算法，允许系统逐个或逐批次地处理新补充的技术特征。它无需在每次新增材料时都对全量数据进行重新聚类，而是动态调整聚类中心和成员，完美匹配了企业专利撰写中“边讨论、边补充、边提炼”的真实工作流，显著提升了处理效率。
3.  **强可解释性与可追溯性**：最终输出的“可追溯提炼卡片”构成了一个完整的证据闭环。卡片中明确记录了发明点来源于哪些原始语句、其新颖性如何通过与特定现有专利片段对比得出，以及各个技术特征对发明点的量化贡献度。这一数据结构为后续的权利要求会审和正式稿编译提供了坚实、可审计的技术证据基础。
4.  **深层语义理解**：利用预训练语言模型（Transformer）进行特征表示和相似度计算，能够捕捉技术特征在更高维度上的语义关联，而非字面匹配。这使得新颖性判断和特征聚类更加精准，能有效发现实质相同的现有技术，规避保护范围不当的风险。

## 五、技术关键点和建议保护点

**技术关键点：**
1.  **“语义对比-增量聚类”的耦合机制**：关键点不在于单独使用语义模型或聚类算法，而在于将语义对比输出的**新颖性得分**，作为增量聚类过程的**动态初始化加权依据**，将“创新性评估”与“技术点聚合”两个环节在算法层面进行了有机融合。
2.  **带权重的增量聚类中心更新公式**：`C_new = C_old * (1 - α*w_new) + V_new * (α*w_new)`。此公式实现了特征的新颖性程度与其对发明点中心影响力的正相关，确保了高新颖性特征在提炼过程中的主导地位。
3.  **可追溯提炼卡片的数据结构**：该数据结构将发明点的“构成（来源特征）-依据（对比文件）-程度（量化贡献度）”三者合一，是实现全流程可追溯证据链的核心技术载体。

**建议保护点：**
1.  **方法权利要求**：一套完整的步骤流程（S1-S4），保护“一种基于语义对比和增量聚类的发明点提炼方法”。
2.  **装置权利要求**：与方法权利要求一一对应的模块化装置，保护一种包含特征获取模块、语义对比模块、增量聚类模块和结果生成模块的“发明点提炼装置”。
3.  **关键子步骤**：针对增量聚类步骤（S3）中“带新颖性权重的动态更新机制”进行单独保护，限定其具体实现方案。
4.  **计算机可读存储介质**：其上存储有执行上述方法的计算机程序的存储介质。
5.  **数据产物**：在合适的法条下，尝试保护“可追溯提炼卡片”这种具有特定结构和功能的信息实体。

## 六、可选实施例、变形例和补充材料需求

**1. 可选实施例/变形例：**
*   **实施例二（基于阈值的动态调整）**：聚类参数（如紧凑度阈值δ）不是固定不变的，而是可以根据用户反馈或最终确定的发明点数量进行在线自适应调整，以优化提炼粒度。
*   **实施例三（替代聚类算法）**：增量聚类模块可采用DBSCAN的在线变种算法替换，用于发现非球形的、任意形状的发明点特征簇。
*   **变形例（提炼卡片与后续环节交互）**：可追溯提炼卡片的结构可以扩展一个“会审状态”字段，在进入权利要求会审环节后，该卡片的状态会实时更新，并与版本的修改日志相关联。

**2. 补充材料需求：**
*   **现有技术对比示例**：建议提供一个具体的、对比性的实验案例，示出同一份测试交底材料，在人工提炼（或基于关键词的软件）与本发明方法下，所得出发明点在清晰度、客观性和可追溯性上的差别。
*   **专利知识图谱样本**：提供一个构建好的专利知识图谱的局部示例，展示其如何组织IPC分类号、技术术语、功效短语间的关联关系，以支持检索。
*   **性能评价指标实验数据**：建议补充使用标准数据集进行量化评价的实验结果。例如，在包含N份标好发明点的交底材料上，测试本方法的**ARI（调整兰德系数）** 和**同质性、完整性、V-Measure** 等聚类指标；并通过人工评分来评价**可解释性**（如提炼卡片的有用性评分）。
*   **用户交互界面**：可提供生成“可追溯提炼卡片”用户界面的示意图，展示专利工程师如何查看、理解和使用这些卡片进行后续工作。

## Mermaid 图
```mermaid
```mermaid
flowchart TD
    A[输入技术交底材料（初始或增量补充）] --> B[步骤S1：特征获取模块<br/>通过依存句法分析、命名实体识别抽取<br/>候选技术特征集合 F={f1,...,fn}]
    B --> C[步骤S2：语义对比模块<br/>将特征编码为语义向量 Vi<br/>在专利知识图谱中检索相关文献片段<br/>计算余弦相似度并生成新颖性得分 S(fi)]
    C --> D[步骤S3：增量聚类模块<br/>以新颖性得分作为初始权重<br/>每新增特征动态调整聚类中心<br/>基于簇内紧凑度和簇间分离度<br/>输出发明点聚类]
    D --> E[步骤S4：结果生成模块<br/>为每个发明点生成可追溯提炼卡片<br/>卡片含：原始特征来源、相似专利片段、聚类贡献度]
    E --> F[输出发明点提炼结果清单]
```
```

## 绘图提示词
根据您提供的Mermaid流程，以下是为中国发明专利准备的黑白线稿流程图的绘图提示词，可直接用于AI绘图工具或交绘图人员绘制摘要附图。

---

**绘图提示词：**
```
黑白线稿专利流程图，无任何阴影和填充色，白色背景，纯黑线条。图面采用自上而下的纵向布局，由6个矩形模块和竖直向下的箭头组成。所有矩形边框使用黑色实线，粗细均匀，无圆角，内部文字统一用黑色宋体，字号清晰可读。箭头为黑色实心三角箭头，线宽与框线一致。

各模块内容和顺序（从上到下）：
1. 顶部矩形框，内书“输入技术交底材料（初始或增量补充）”。
2. 向下的黑色箭头。
3. 矩形框，内分两行，第一行“步骤S1：特征获取模块”，第二行小字“依存句法分析、NER抽取候选特征集合F={f1,…,fn}”。
4. 向下的黑色箭头。
5. 矩形框，内分两行，第一行“步骤S2：语义对比模块”，第二行小字“语义向量编码、知识图谱检索、余弦相似度计算，生成新颖性得分S(fi)”。
6. 向下的黑色箭头。
7. 矩形框，内分两行，第一行“步骤S3：增量聚类模块”，第二行小字“以新颖性得分初始权重，动态调整聚类中心，基于簇内紧凑度与簇间分离度输出发明点聚类”。
8. 向下的黑色箭头。
9. 矩形框，内分两行，第一行“步骤S4：结果生成模块”，第二行小字“生成可追溯提炼卡片，含特征来源、相似专利片段、聚类贡献度”。
10. 向下的黑色箭头。
11. 底部矩形框，内书“输出发明点提炼结果清单”。

画面整洁，无任何装饰元素，适合黑白打印并用作中国发明专利摘要附图。
```

---

该提示词严格遵循了“黑白线稿、无装饰、模块和箭头清晰”的要求，并完整保留了技术交底材料中的关键步骤、模块及数据流。使用此提示词生成的线图可直接作为专利说明书摘要附图。

## 自检结果
暂无。

## 生成日志
- project_scan: summarized draft and uploaded materials
- patent_points: generated candidates and selected recommended point
- prior_art_terms: generated semantic search chunks
- prior_art_search: collected 0 public references
- prior_art_relevance: summarized differences against public references
- disclosure_body: generated technical disclosure markdown
- disclosure_mermaid: generated Mermaid diagrams
- disclosure_image_prompt: generated patent drawing prompt
- disclosure_self_check: checked disclosure consistency and support
- warning: CNIPA EPUB helper is not configured; set CNIPA_EPUB_SEARCH_SCRIPT to enable live CNIPA search.
- warning: CNIPA EPUB helper is not configured; set CNIPA_EPUB_SEARCH_SCRIPT to enable live CNIPA search.
- warning: CNIPA EPUB helper is not configured; set CNIPA_EPUB_SEARCH_SCRIPT to enable live CNIPA search.
- warning: CNIPA EPUB helper is not configured; set CNIPA_EPUB_SEARCH_SCRIPT to enable live CNIPA search.
- warning: CNIPA EPUB helper is not configured; set CNIPA_EPUB_SEARCH_SCRIPT to enable live CNIPA search.
- warning: CNIPA EPUB helper is not configured; set CNIPA_EPUB_SEARCH_SCRIPT to enable live CNIPA search.
- warning: Google Patents fallback failed for term 语义对比 发明点 提炼: HTTP Error 503: Service Unavailable
- warning: Google Patents fallback failed for term 增量聚类 技术特征: HTTP Error 503: Service Unavailable
- warning: Google Patents fallback failed for term 专利知识图谱 对比学习: HTTP Error 503: Service Unavailable
- warning: Google Patents fallback failed for term 新颖性得分 生成: HTTP Error 503: Service Unavailable
- low_research_confidence: 0 references collected (10 provider attempts); 交底书不隐含高专利性置信度。
