# Current Kernel

## 当前仓库的核心目标

ClawLab 当前不是一个网页产品，也不是一个复杂多 Agent 系统。

它当前的核心目标是：

> 作为一个 Python-first CLI 研究工作仓库，稳定跑通从研究者画像、项目上下文、任务草稿到修订学习的最小闭环。

这个目标强调两件事：

- 默认本地可运行，不依赖 API
- 所有关键状态都要落在本地仓库里，便于继续维护和演化

## 当前最小闭环

当前主流程是：

`init -> ingest-cv -> project create -> task run -> learn -> status`

对应含义如下：

1. `init`
   - 初始化 `workspace/`
   - 生成默认配置
2. `ingest-cv`
   - 读取 CV 文本或 PDF
   - 生成 `ResearcherProfile`
3. `project create`
   - 从项目说明、论文摘要、memo 或路径输入中生成 `ProjectCard`
4. `task run`
   - 读取材料
   - 生成 `MaterialSummary`
   - 检索资产
   - 生成 `TaskPlan`
   - 产出 markdown 草稿与 `TaskCard`
5. `learn`
   - 比较生成稿与修订稿
   - 产出 `ReusableAsset`
6. `status`
   - 展示当前 profile、project、recent task、material summary、task plan、assets

## 当前数据对象

### ResearcherProfile

表示当前研究者是谁。

当前承载：

- 基本身份与学科背景
- 常用方法与工具
- 常见任务
- 写作与协作偏好
- 原始 CV 文本

它是整个内核里的长期身份上下文。

### ProjectCard

表示当前最活跃、最需要推进的项目。

当前承载：

- 项目标题
- 研究问题
- 当前目标
- 当前阶段
- blockers
- 材料线索
- 下一步

它是任务生成和材料判断的主上下文。

### TaskCard

表示一次具体工作请求。

当前承载：

- task type
- 输入摘要
- 输入材料路径与类型
- material summary 引用
- 检索到的 asset 引用
- task plan 引用
- 生成稿路径
- 修订稿路径
- feedback summary

它是一次具体工作的记录对象。

### ReusableAsset

表示从任务中学到的、下次可复用的经验。

当前承载：

- `writing_rule`
- `structure_template`
- `project_note`

并通过 `scope` 区分：

- `global`
- `project`
- `task`

它是当前内核里的经验沉淀层。

### MaterialSummary

表示系统对输入材料的压缩理解。

当前承载：

- 来源路径与类型
- 标题
- 短摘要
- key topics
- methods or entities
- useful snippets
- relevance to project
- raw text excerpt

它是 `task run` 之前的材料理解中间层。

### TaskPlan

表示草稿生成前的轻量规划对象。

当前承载：

- task goal
- output strategy
- key points to cover
- recommended structure
- project considerations
- selected assets

它让系统不再是“材料直接出草稿”。

## 当前 CLI 主命令

- `clawlab init`
- `clawlab ingest-cv <path>`
- `clawlab project create`
- `clawlab task run <task_type> --project <project_id> --input <path>`
- `clawlab learn --task <task_id> --revised <path>`
- `clawlab status`
- `clawlab config show`

## 当前系统边界

当前明确不支持：

- 多项目并行管理
- 多用户协作
- 真正的多 Agent 运行时
- 联网检索
- OCR
- embedding 检索
- 数据库
- 自动代码执行
- 复杂插件系统

也就是说，当前内核是：

> 一个稳定、可解释、可本地运行的研究工作流内核，而不是一个完整的“虚拟公司系统”。
