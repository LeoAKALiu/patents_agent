# 一种基于项目状态锁定的工作流保护方法

## 前置材料摘要
一种运行中项目切换保护方法，旨在当用户在发明点提炼过程中切换项目时，防止运行结果误写入非目标项目，保障项目数据一致性。


> **检索置信度**：🔴 低
>
> 低置信度表示未检索到可引用的公开现有技术文献；交底书不隐含高专利性判断。

## 材料覆盖
仅提供一句发明名称式描述，未给出具体实施例、流程图、技术步骤、模块组成、数据流或任何实现细节，材料覆盖严重不足。

## 候选专利点
- p1 一种基于项目状态锁定的工作流保护方法：通过为每个项目维护动态状态锁，在接收到项目切换指令时，对当前项目的运行过程执行原子化的挂起与禁止写入标记，待切换完成后由新项目的状态锁控制写入方向，实现零误写率的项目切换保护。
  证据状态：model_generated
  来源：model
  可行依据：未填写
  支撑缺口：无显式缺口
  护城河评分：0.0
- p2 一种基于智能工作区的事务性切换保护装置：引入项目工作区隔离容器与事务性操作，在切换时自动创建/恢复工作区快照，所有运行结果写入限制在当前工作区内，切换动作作为一个事务提交，实现项目间完全隔离和回滚能力。
  证据状态：model_generated
  来源：model
  可行依据：未填写
  支撑缺口：无显式缺口
  护城河评分：0.0
- p3 一种基于上下文令牌的跨项目写入拦截方法：采用项目上下文令牌（Token）机制，每个运行任务在发起时被分配加密签名令牌，令牌内绑定项目ID、发起时间与任务指纹；在结果提交时，必须验证令牌有效性与项目ID一致性，任何不匹配的提交被即时拦截并告警。
  证据状态：model_generated
  来源：model
  可行依据：未填写
  支撑缺口：无显式缺口
  护城河评分：0.0
- p4 一种多项目动态路由的矩阵式写入保护方法：构建项目-运行实例映射矩阵，为每个运行实例分配网格坐标，通过部署写入路由表，根据实例坐标动态选择目标项目存储路径，并在切换时即时更新路由表，实现无锁化并发多目标安全写入。
  证据状态：model_generated
  来源：model
  可行依据：未填写
  支撑缺口：无显式缺口
  护城河评分：0.0
- p5 一种上下文感知的自适应写入重定向与恢复方法：在项目切换时，不立即拦截结果，而是根据任务上下文（如输入数据来源、用户意图推测）和结果内容相似度自适应决定将结果回写到原项目、新项目或提示用户选择，并支持被误写的快速恢复迁移。
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
| cnipa | patent | 项目 状态 锁 | ⏭️ skipped | 0 | 0 | CNIPA EPUB helper is not configured; set CNIPA_EPUB_SEARCH_S |
| cnipa | patent | 工作流 保护 方法 | ⏭️ skipped | 0 | 0 | CNIPA EPUB helper is not configured; set CNIPA_EPUB_SEARCH_S |
| cnipa | patent | 原子 挂起 禁止写入 | ⏭️ skipped | 0 | 0 | CNIPA EPUB helper is not configured; set CNIPA_EPUB_SEARCH_S |
| cnipa | patent | 挂起 缓冲区 重定向 | ⏭️ skipped | 0 | 0 | CNIPA EPUB helper is not configured; set CNIPA_EPUB_SEARCH_S |
| cnipa | patent | 切换 控制 模块 | ⏭️ skipped | 0 | 0 | CNIPA EPUB helper is not configured; set CNIPA_EPUB_SEARCH_S |
| cnipa | patent | 运行 结果 误写 防止 | ⏭️ skipped | 0 | 0 | CNIPA EPUB helper is not configured; set CNIPA_EPUB_SEARCH_S |
| google_patents | patent | 项目 状态 锁 | ❌ failed | 0 | 0 | Google Patents fallback failed for term 项目 状态 锁: HTTP Error  |
| google_patents | patent | 工作流 保护 方法 | ❌ failed | 0 | 0 | Google Patents fallback failed for term 工作流 保护 方法: HTTP Erro |
| google_patents | patent | 原子 挂起 禁止写入 | ❌ failed | 0 | 0 | Google Patents fallback failed for term 原子 挂起 禁止写入: HTTP Err |
| google_patents | patent | 挂起 缓冲区 重定向 | ❌ failed | 0 | 0 | Google Patents fallback failed for term 挂起 缓冲区 重定向: HTTP Err |

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
  - google_patents failed: Google Patents fallback failed for term 项目 状态 锁: HTTP Error 503: Service Unavailable
  - google_patents failed: Google Patents fallback failed for term 工作流 保护 方法: HTTP Error 503: Service Unavailable
  - google_patents failed: Google Patents fallback failed for term 原子 挂起 禁止写入: HTTP Error 503: Service Unavailable
  - google_patents failed: Google Patents fallback failed for term 挂起 缓冲区 重定向: HTTP Error 503: Service Unavailable
  - cnipa skipped: CNIPA EPUB helper is not configured; set CNIPA_EPUB_SEARCH_SCRIPT to enable live CNIPA search.
  - cnipa skipped: CNIPA EPUB helper is not configured; set CNIPA_EPUB_SEARCH_SCRIPT to enable live CNIPA search.
  - cnipa skipped: CNIPA EPUB helper is not configured; set CNIPA_EPUB_SEARCH_SCRIPT to enable live CNIPA search.
  - cnipa skipped: CNIPA EPUB helper is not configured; set CNIPA_EPUB_SEARCH_SCRIPT to enable live CNIPA search.
  - cnipa skipped: CNIPA EPUB helper is not configured; set CNIPA_EPUB_SEARCH_SCRIPT to enable live CNIPA search.
  - cnipa skipped: CNIPA EPUB helper is not configured; set CNIPA_EPUB_SEARCH_SCRIPT to enable live CNIPA search.
  - google_patents failed: Google Patents fallback failed for term 项目 状态 锁: HTTP Error 503: Service Unavailable
  - google_patents failed: Google Patents fallback failed for term 工作流 保护 方法: HTTP Error 503: Service Unavailable
  - google_patents failed: Google Patents fallback failed for term 原子 挂起 禁止写入: HTTP Error 503: Service Unavailable
  - google_patents failed: Google Patents fallback failed for term 挂起 缓冲区 重定向: HTTP Error 503: Service Unavailable

## 技术交底书
# 中国发明专利技术交底书

## 注意事项

> **致代理人/律师：**
> 本文档为技术交底书初稿，旨在供您进行专利性评估和正式申请文件撰写。文中采用技术特征、模块、数据流等专业术语进行表达，避免商业宣传用语。请您特别关注以下事项：
> 1. 本文所述现有技术是基于发明人提供的材料，可能需补充正式的专利/文献检索以评估三性。
> 2. 技术方案的重点在于“状态锁”和“写入拦截”机制，建议构建多层次权利要求组合。
> 3. 由于原始材料未提供附图，建议结合本文描述补充系统架构图和核心方法流程图。
> 4. 请审查本方案是否满足《专利法》关于软件方法可专利客体的要求。

---

## 一、相关技术背景

### 1.1 最接近的现有技术和公开URL
根据发明人提供的材料，当前未检索到与本方案直接相关的公开专利或文献（公开URL：无）。本领域一般可获知的背景技术如下：

在多项目协作的软件平台（例如AI辅助发明点提炼系统）中，普遍采用“异步任务处理”架构。当用户触发一个耗时的AI推理或数据提炼运行过程后，该过程会在后台线程或进程中执行。在此期间，用户视线可能离开，但传统系统允许用户在任意时刻手动切换至另一项目工作区。此时，后台运行过程的结果在返回时，通常依赖于一个简单的全局“当前项目ID”变量来决定数据写入目标。然而，该全局变量可能在运行过程结束前被切换操作改变，导致结果数据最终写入错误的项目数据库。

### 1.2 现有技术缺点
在用户在多项目协作的AI辅助发明点提炼过程中，上述机制存在以下技术缺点：
*   **数据误写入风险高**：项目切换操作与异步运行结果写入之间存在时序不确定的竞态条件。运行结果提交时读取到的目标项目标识，可能已经是切换后的新项目，极易将当前运行过程产生的结果数据（例如提炼出的发明点）错误写入非原始目标项目，造成项目数据污染。
*   **数据一致性与可追溯性被破坏**：误写入行为破坏了源项目数据的完整性，并导致数据产生链路（哪个项目触发了哪次运算）断裂，无法追溯。
*   **缺乏运行中断保护**：现有系统不区分“用户选择新项目”与“旧项目运行过程结束”这两个事件，不存在对运行中过程的挂起、拦截或重定向机制，使得未完成的计算结果要么丢失，要么造成破坏。

---

## 二、要解决的技术问题
本发明旨在解决现有技术中，因项目切换操作与异步运行结果写入时序不确定，导致运行过程中产生的结果数据被错误写入非目标项目，破坏项目数据一致性与可追溯性的技术问题。

---

## 三、详细技术方案

本发明提出一种基于项目状态锁定的工作流保护方法，通过为每个项目实例维护一个动态的状态锁对象，在项目切换时执行原子化的状态切换，并对运行结果进行挂起拦截，以确保零误写率。

### 3.1 系统结构及模块功能
本系统运行于服务器端，包含以下核心模块：

*   **项目状态管理模块**：
    *   负责为每个实例化的项目分配一个唯一的项目标识（Project ID），并创建与之唯一绑定的、可读写的状态锁对象。
    *   状态锁至少包含两种状态：“活跃-允许写入”态和“挂起-禁止写入”态。
    *   提供原子化的状态更新接口，确保状态变更的不可分割性。
*   **切换控制模块**：
    *   专用于接收并处理用户发起的项目切换指令。
    *   在接收到指令后，驱动所述项目状态管理模块执行原子性状态切换。
    *   记录切换操作的关键事件，包括但不限于切换时间戳和用于追溯的过渡标识。
*   **运行结果拦截模块**：
    *   拦截所有运行线程在提交最终结果前的写入请求。
    *   根据运行线程携带的源项目标识，查询所述项目状态管理模块中对应的状态锁。
    *   根据状态锁的校验结果，决定结果数据的流向。
*   **挂起缓冲区**：
    *   一个临时、持久化的数据存储区域。
    *   用于接收并存储被所述运行结果拦截模块判定为“挂起-禁止写入”状态下的运行结果。
    *   提供结果数据的重定向或丢弃接口，供用户对暂存数据进行后续处置。

### 3.2 方法流程（参考图1）
本发明的方法包含以下详细步骤：

**S1、项目实例化与状态锁初始化**
在系统中启动一个新的项目（例如项目A、项目B）时，所述项目状态管理模块为其分配一个唯一的`ProjectID`，并将其状态锁初始化为“活跃-允许写入”态。

**S2、运行过程的状态携带**
当用户在特定项目（如项目A）中触发一次运行过程（如AI提炼运算）时，系统为该运行过程分配一个运行线程。该线程内部除携带运算所需上下文外，还必须携带并固化其源项目的`ProjectID_A`以及该运算的唯一`TaskID`。

**S3、项目切换的原子化操作**
当所述切换控制模块接收到来自用户界面、从项目A切换至项目B的指令时，执行以下原子性步骤：
1.  调用项目状态管理模块，在一个原子事务中将项目A的状态锁由“活跃-允许写入”修改为“挂起-禁止写入”。
2.  在同一原子事务中，将项目B的状态锁由其上一状态（可能为挂起）修改为“活跃-允许写入”。
3.  生成并记录本次切换的过渡标识和精确的时间戳，用于后续审计。

**S4、运行结果的挂起拦截与处置**
项目A在步骤S3执行前已触发的任何待提交运行结果，当其写入请求到达时：
1.  所述运行结果拦截模块获取其携带的`ProjectID_A`。
2.  查询所述项目状态管理模块，获取项目A的当前状态锁。
3.  **拦截动作**：若状态锁为“挂起-禁止写入”，则阻止该结果直接写入项目A的正式数据库。
4.  **缓冲动作**：将该运行结果及其元数据（`TaskID`, `ProjectID_A`, 生成时间等）暂存至所述挂起缓冲区。
5.  **提示动作**：在用户界面上生成一个通知，提示用户项目A存在被挂起的运行结果，并提供“重定向至项目B”或“丢弃”的可选操作。

**S5、新项目的正常运行**
在步骤S3完成后，用户在项目B中发起新的运行过程，其结果携带`ProjectID_B`。所述运行结果拦截模块查询项目B的状态锁为“活跃-允许写入”，校验通过，允许结果正常写入项目B的对应数据库。

### 3.3 关键参数与数据结构
*   **状态锁对象（StateLock）**：
    ```json
    {
      "ProjectID": "项目唯一标识，例如 proj_A_2490867258",
      "State": "枚举值，['ACTIVE_WRITABLE', 'SUSPENDED_WRITE_BLOCKED']",
      "LastModifiedTimestamp": "状态最后变更的Unix毫秒时间戳",
      "TransactionID": "导致此次状态变更的切换事务唯一标识"
    }
    ```
*   **运行结果提交请求（ResultSubmissionRequest）**：
    ```json
    {
      "SourceProjectID": "该运行过程发起时的项目ID，用于状态校验",
      "TaskID": "运行过程的唯一标识",
      "Payload": "待写入的结果数据",
      "CreatedTimestamp": "结果创建时的Unix毫秒时间戳"
    }
    ```
*   **挂起缓冲区记录（BufferedResultRecord）**：
    ```json
    {
      "BufferedID": "缓冲区内的唯一标识",
      "OriginalRequest": "完整的ResultSubmissionRequest对象",
      "InterceptedTimestamp": "被拦截并存入缓冲区的时间",
      "Status": "枚举值，['PENDING_USER_ACTION', 'REDIRECTED', 'DISCARDED']"
    }
    ```

### 3.4 数据流
用户切换指令 → **切换控制模块** → **项目状态管理模块**（原子更新项目A、B的状态锁） → **运行结果拦截模块**（在结果写入路径上监听） → [查询项目A状态锁为“挂起-禁止写入”] → 结果存入**挂起缓冲区**； [查询项目B状态锁为“活跃-允许写入”] → 结果正常写入**项目B数据库**。同时，挂起缓冲区通过查询接口提供列表给用户界面，用于数据处置。

---

## 四、相对于现有技术的有益效果
1.  **彻底杜绝数据误写入风险**：通过基于“源项目ID+动态状态锁”的提交前校验机制，从根本上解决了因时序错乱导致的结果写入错误项目的问题，将误写率降至零。
2.  **保障项目数据一致性与完整性**：项目切换与运行过程完全解耦，一个项目的挂起不会影响另一个项目的活跃写入，确保了多项目并行/串行工作场景下，每个项目数据库中的数据均由该项目的运行过程产生，数据关联关系清晰、可追溯。
3.  **提供可恢复的中间结果，避免数据丢失**：挂起缓冲区的设计，使得因切换而被拦截的运行结果不会丢失。用户可以选择性地将其重定向到新的目标项目，有效保护了已消耗的计算资源。
4.  **高并发环境下的状态一致性**：状态锁的原子切换操作保证了在高并发切换指令下的强一致性，不会出现中间状态导致校验逻辑失效的情况。

---

## 五、技术关键点和建议保护点
### 5.1 技术关键点
*   **项目粒度状态锁**：将写入控制权限从全局级别提升至项目实例级别。
*   **源项目ID固化**：运行过程在创建之初就固定携带其所属的项目ID，而非在结果提交时动态读取。
*   **原子化切换与拦截**：切换指令驱动状态锁的原子变更，与结果提交路径上的状态检查，构成一个闭环的同步保护机制。
*   **挂起缓冲与恢复**：并非简单丢弃，而是暂存并提供主动处置能力。

### 5.2 建议保护点（基于独立/从属权利要求构思）
*   **方法**：核心保护一种基于项目状态锁定的工作流安全写入方法，涵盖状态定义、切换原子操作、拦截与缓冲主要步骤。
*   **系统/设备**：保护由项目状态管理模块、切换控制模块、运行结果拦截模块、挂起缓冲区组成的服务器系统。
*   **从属项（可进一步丰富）**：
    *   所述原子化操作的具体实现方式（例如基于数据库事务或分布式锁）。
    *   所述挂起缓冲区的内容呈现方式与用户重定向交互流程。
    *   对项目切换操作的审计记录与回溯机制。
    *   状态锁的多种形态（例如增加“只读”、“锁定”等更细粒度的状态）。
*   **计算机可读存储介质**：其上存储有用于执行上述任一方法的计算机程序。

---

## 六、可选实施例、变形例和补充材料需求
### 6.1 可选实施例与变形例
1.  **非原子切换的软锁版本**：在无需强一致性场景下，可先将项目A状态置为“冻结中”，拒绝新写入并等待所有进行中的写入提交，超时后再强制挂起。
2.  **多项目实例下的锁屏蔽**：支持用户因特殊权限（如管理员）发起“无痕切换”，即切换项目B为活跃，但刻意不挂起项目A，允许结果继续写入，以满足特殊并行监控需求。
3.  **基于队列的异步提交**：为每个项目维护一个写入队列，切换操作只是切换了结果拦截模块上游的路由指向，队列的消费不受影响，实现更平滑的无锁切换（针对高吞吐场景的变形）。

### 6.2 补充材料需求
为增强交底书的完整性和代理人的理解，建议补充以下材料：
1.  **系统架构图**：一张展示用户端、切换控制、状态管理、拦截模块、挂起缓冲区及项目数据库之间连接关系的框图。
2.  **核心方法流程图**：一张详细描绘从“发起切换”到“结果被拦截/写入”再到“用户处置”的完整决策与数据流向的流程图。
3.  **时序图**：一张展示用户、项目A线程、项目B线程、状态锁和拦截模块之间交互消息时序的UML时序图。

## Mermaid 图
```mermaid
```mermaid
flowchart TD
    subgraph UserOperation[用户操作层]
        U1[用户在工作区A触发运行] --> |携带项目A ID| ThreadA[运行线程A]
        U2[用户发出切换指令: 从A切换到B]
    end

    subgraph ControlLayer[核心控制层]
        SwitchCtrl[切换控制模块]
        StateMgr[项目状态管理模块]
    end

    subgraph InterceptorLayer[拦截与缓冲层]
        Interceptor[运行结果拦截模块]
        Buffer[挂起缓冲区]
    end

    subgraph DB[项目数据库]
        DBA[(项目A数据库)]
        DBB[(项目B数据库)]
    end

    StateMgr -- 初始化时为项目A/B创建状态锁 --> StateLockA(项目A状态锁<br/>&lt;br/&gt;状态:活跃/挂起)
    StateMgr -- 更新状态锁 --> StateLockB(项目B状态锁)

    U2 --> SwitchCtrl
    SwitchCtrl -- 调用原子切换接口 --> StateMgr
    StateMgr -- 原子操作: A锁→挂起, B锁→活跃, 记录时间戳与过渡标识 --> StateMgr

    ThreadA -- 运行完成, 提交结果 --> Interceptor
    Interceptor -- 查询项目A状态锁 --> StateMgr
    StateMgr -- 返回 "挂起-禁止写入" --> Interceptor
    Interceptor -- 阻止写入, 暂存结果及元数据 --> Buffer
    Buffer -- 提示用户重定向或丢弃 --> UI[用户界面]

    ThreadB[运行线程B: 携带项目B ID] -- 提交结果 --> Interceptor
    Interceptor -- 查询项目B状态锁 --> StateMgr
    StateMgr -- 返回 "活跃-允许写入" --> Interceptor
    Interceptor -- 允许写入 --> DBB

    ThreadA -..- DBA
    ThreadB -..- DBB

    Buffer -. 用户选择重定向到B .-> DBB
    Buffer -. 用户选择丢弃 .-> Discard[丢弃]
```
```

## 绘图提示词
以下为适于中国发明专利摘要或说明书附图的黑白线框图绘图提示词，遵循黑白线稿、无装饰、模块与箭头清晰的要求，表达运行中项目切换的拦截与缓冲方案。

请按如下描述绘制：

整体布局：采用自上而下的分层结构，共分为四个区域，各区域可用细虚线矩形框标注层名（用户操作层、核心控制层、拦截与缓冲层、数据库层），但层名不是必须。所有图形元素使用黑色线条、白色背景，无底色填充，无阴影。

一、用户操作层（图上方）
1. 绘制第一动作框：“用户在工作区A触发运行（携带项目A ID）”，矩形框。从其右侧引出一条带箭头实线，指向第一处理模块矩形“运行线程A”。
2. 绘制第二动作框：“用户发出切换指令：从A切换到B”，矩形框。从其右侧引出一条带箭头实线，指向核心控制层中的“切换控制模块”矩形。
3. 在拦截与缓冲层的“挂起缓冲区”右侧，绘制“用户界面”矩形，从挂起缓冲区画一条带箭头实线指向该用户界面，箭头标注“提示重定向或丢弃”。

二、核心控制层（图中部偏上）
4. 绘制“切换控制模块”矩形，接收来自上述第二动作框的输入箭头。
5. 绘制“项目状态管理模块”矩形，位于切换控制模块下方或右侧。从切换控制模块引出一条带箭头实线指向项目状态管理模块，箭头旁标注“调用原子切换接口”。
6. 项目状态管理模块输出两个状态锁矩形，分别为“项目A状态锁”和“项目B状态锁”，每个矩形内部分两行标注，例如“项目A状态锁”下方写“状态：活跃/挂起”。状态锁可用矩形加单线内框表示。
7. 绘制项目状态管理模块到项目A状态锁的箭头（实线）和到项目B状态锁的箭头（实线），并可在中间以大括号或注释文字表明“原子操作：A锁→挂起，B锁→活跃，记录时间戳与过渡标识”。箭头方向为状态管理模块指向状态锁，表示更新。

三、拦截与缓冲层（图中部偏下）
8. 绘制“运行结果拦截模块”矩形，它有多个输入和输出：
   - 输入1：来自运行线程A的带箭头实线，箭头旁可标注“提交结果”。
   - 输入2：来自后续新增的“运行线程B”的带箭头实线，标注“提交结果”（线程B可置于用户操作层或另绘制）。
   - 从运行结果拦截模块向项目状态管理模块引出一条带箭头虚线，标注“查询项目A/B状态锁”。
   - 从项目状态管理模块向运行结果拦截模块引出一条返回带箭头虚线，可分支标注两条返回信息：“返回‘挂起-禁止写入’”（针对A）和“返回‘活跃-允许写入’”（针对B）。
9. 运行结果拦截模块的两个输出：
   - 对于线程A的结果，当收到“挂起-禁止写入”后，绘制一条带箭头实线指向“挂起缓冲区”矩形，旁注“阻止写入，暂存结果及元数据”。
   - 对于线程B的结果，当收到“活跃-允许写入”后，绘制一条带箭头实线指向数据库层的“项目B数据库”，旁注“允许写入”。
10. 挂起缓冲区矩形除了连接到用户界面外，还从该缓冲区引出两条带箭头虚线：
    - 一条虚线指向“项目B数据库”，虚线旁标注“用户选择重定向到B”。
    - 另一条虚线指向一个“丢弃”模块（可用垃圾桶简图或矩形内标“丢弃”），旁注“用户选择丢弃”。

四、数据库层（图底部）
11. 绘制两个圆柱体标识的数据库：“项目A数据库”和“项目B数据库”。
12. 连接关系：
    - 运行线程A与项目A数据库之间画一条带箭头虚线，可标注“常规直接存取路径（切换时被拦截）”以表示未拦截时的数据流向。该虚线不与拦截模块冲突，仅为背景示意。
    - 运行线程B与项目B数据库之间同样画一条带箭头虚线，可标注“常规直接存取路径”。
    - 如前所述，拦截模块的允许写入实线指向项目B数据库。
13. 若需示出线程B的产生，可在用户操作层绘制“运行线程B（携带项目B ID）”矩形，由切换切换成功后创建，其提交结果箭头指向拦截模块。可从项目状态管理模块引出虚线至线程B表示触发运行。

五、附图标注
- 所有模块使用矩形框（直角或小圆角），数据库使用标准圆柱体，箭头使用单线箭头，实线表示必要控制流/数据流，虚线表示可选路径/示意路径/用户选择路径。
- 文字说明使用宋体或等线体，清晰可读，字号适中。
- 可对关键步骤或模块加注编号①、②…，但非必需。若加注，建议流程编号沿控制流顺序标注。

技术特征强调：该图体现出原子切换接口、状态锁、运行结果拦截、挂起缓冲区以及重定向选择，表明在项目切换过程中，原运行线程的结果被临时挂起，切换后的新线程正常写入，避免脏数据，并给予用户灵活处置挂起结果的能力。

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
- warning: Google Patents fallback failed for term 项目 状态 锁: HTTP Error 503: Service Unavailable
- warning: Google Patents fallback failed for term 工作流 保护 方法: HTTP Error 503: Service Unavailable
- warning: Google Patents fallback failed for term 原子 挂起 禁止写入: HTTP Error 503: Service Unavailable
- warning: Google Patents fallback failed for term 挂起 缓冲区 重定向: HTTP Error 503: Service Unavailable
- low_research_confidence: 0 references collected (10 provider attempts); 交底书不隐含高专利性置信度。
