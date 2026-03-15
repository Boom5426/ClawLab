# ClawLab

ClawLab 是一个面向研究生和博士生的 Python-first CLI 研究协作系统。

它的目标不是做一个花哨网页，也不是做泛化的“科研 Agent demo”，而是把你的本地仓库逐步变成一个真正可持续演进的研究工作仓库：

- 先理解你是谁
- 再理解你当前在做什么项目
- 然后围绕一个真实研究任务产出草稿
- 最后从你的修改中学习，沉淀规则、模板和项目笔记

一句话概括：

> ClawLab 想做的是一个会越来越懂你的本地研究协作工作台。

## 我们为什么做这个

研究人员在日常工作里有几个非常重复、但非常耗时间的问题：

- 每次都要重新解释自己的研究背景
- 每次都要重新说明当前项目在做什么
- 文献、笔记、草稿、项目想法散落在不同地方，难以复用
- AI 可以帮忙生成内容，但并不会真正记住你的项目脉络
- 你改了很多内容，但这些修改不会沉淀成以后可复用的规则

ClawLab 当前就是为了解决这一类问题。

它不追求“一键自动科研”，而是先把最小闭环做实：

1. 建立研究者档案
2. 建立当前项目卡片
3. 用真实材料生成任务草稿
4. 从修订中学习
5. 让这些学习结果留在你的本地仓库里
6. 让这些学习结果可以被研究人员直接打开、阅读和修改

## 当前如何沉淀学习结果

ClawLab 当前不会只把学习结果埋在 JSON 里。

`ReusableAsset` 会同时保存成：

- 机器可读的 JSON
- 人可读的 Markdown

当前会落到这些位置：

- `workspace/assets/writing-rules/*.md`
- `workspace/assets/templates/*.md`
- `workspace/assets/project-notes/*.md`
- `workspace/projects/<project_id>/notes/*.md`

当前 task 执行时还会额外生成：

- `workspace/projects/<project_id>/materials/*.json`
- `workspace/tasks/<task_id>/task_plan.json`

这样做的意义是：

- 系统后续仍然可以程序化读取这些资产
- 研究人员也可以直接把它们当作规则、模板、项目笔记继续维护

## 当前核心目标

当前版本只专注一件事：

> 跑通一个最小可闭环的本地研究协作流程。

也就是：

`init -> ingest-cv -> project create -> task run -> 手动修改 draft -> learn -> status`

只要这个闭环稳定成立，ClawLab 才有资格继续往更复杂的方向扩展。

## From research workflow kernel to virtual research company

下一阶段，ClawLab 可以在当前内核之上演化出“虚拟研究公司”模式：

- 用户作为老板 / 创始人
- 经理型 Agent 负责统筹
- 专项 Agent 负责执行具体工作

但这层变化应该首先发生在上层产品隐喻和协作编排层，而不是立刻推翻当前底层模型。

当前稳定对象例如 `ResearcherProfile`、`ProjectCard`、`TaskCard`、`ReusableAsset`、`MaterialSummary` 和 `TaskPlan`，更适合作为长期保留的 kernel state。

相关文档见：

- `docs/current-kernel.md`
- `docs/company-mapping.md`
- `docs/architecture-diagram.md`

## 第一版员工层

在不推翻当前 kernel 的前提下，ClawLab 现在已经增加了第一版员工层。

当前注册了 4 个角色：

- `literature_analyst`
- `project_manager`
- `draft_writer`
- `review_editor`

这些员工不是独立系统，而是对现有能力的岗位化包装：

- `literature_analyst` 复用材料摘要能力
- `project_manager` 复用资产检索与任务规划
- `draft_writer` 复用 draft generation
- `review_editor` 复用 revision learning

也就是说，未来如果继续往经理层演进，调度的将是这批已有真实能力的员工，而不是空角色。

详细说明见：

- `docs/employees.md`

## 当前最小闭环

当前 MVP 支持下面这条完整链路：

1. 用户初始化 workspace
2. 用户导入 CV
3. 用户创建当前研究项目
4. 用户读取研究材料
5. 用户运行一个任务
6. 系统生成 markdown 草稿
7. 用户手动修改草稿
8. 系统学习修订内容
9. 用户通过 `status` 查看系统记住了什么、项目状态是什么、系统学到了什么

## 这轮新增了哪些中间智能层

当前闭环已经不再只是“输入材料 -> 直接出草稿”。

这轮新增了 4 个中间层：

1. `MaterialSummary`
   - 把原始材料压缩成 task 可用上下文
2. `Asset Retrieval`
   - task run 前先检索已有规则、模板和项目笔记
3. `TaskPlan`
   - draft 前先形成结构化任务规划
4. `Learning Writeback`
   - learn 后把经验写回全局和项目资产

这让 ClawLab 从“最小 CLI 原型”升级成“具备第一版智能骨架的研究工作仓库”。

## 当前支持的输入类型

### CV 导入

- `.txt`
- `.md`
- `.rst`
- `.pdf`

### 任务材料输入

- `.txt`
- `.md`
- `.pdf`

说明：

- PDF 当前只做文本提取
- 不支持 OCR
- 如果 PDF 没有可提取文本，会明确报错
- PDF、txt、md 在进入任务前都会先经过“材料压缩层”
- `task run` 不再直接主要依赖原始全文，而是优先依赖结构化 `MaterialSummary`

## 当前支持的命令

### `clawlab init`

初始化本地工作区，创建：

- `workspace/profile/`
- `workspace/projects/`
- `workspace/assets/`
- `workspace/tasks/`

### `clawlab ingest-cv <path>`

读取 CV 文件，解析并生成 `ResearcherProfile`，保存到：

- `workspace/profile/profile.json`

### `clawlab project create`

交互式创建 `ProjectCard`，当前支持三种 intake 入口：

- 输入一个文件路径
- 直接输入一段项目说明
- 输入 `paste` 后粘贴多行内容

`project create` 会优先从论文摘要、项目 brief、网站说明或研究 memo 中归纳项目信息，
然后只额外追问一个核心目标。项目标题也可以手动覆盖，但不是必填。

### `clawlab task run <task_type> --project <project_id> --input <path>`

当前支持两类任务：

- `literature-outline`
- `paper-outline`

命令会：

- 读取输入材料
- 提取文本
- 对材料进行压缩与结构化理解
- 结合 profile + project + material summary 生成 markdown 草稿
- 创建 `TaskCard`

### `clawlab learn --task <task_id> --revised <path>`

读取生成稿和修订稿，对比后提炼：

- `writing_rule`
- `structure_template`
- `project_note`

并更新 task / assets / project。

### `clawlab status`

显示当前仓库状态，包括：

- 当前 profile 摘要
- 当前 active project
- 最近 task
- 最近 task 的输入材料路径和类型
- 最近材料摘要是否已生成
- 最近材料摘要标题和简短摘要
- 最近 task 是否检索到 assets
- 最近 task plan 的关键点
- 最近生成的 assets
- 当前 mode / provider / 哪些模块启用了 LLM

### `clawlab config show`

显示当前配置，包括：

- `mode`
- `provider`
- `model`
- `use_llm_for_materials`
- `use_llm_for_drafts`
- `use_llm_for_learning`

## 当前如何处理 PDF

ClawLab 当前不会把 PDF 原文直接整段塞给任务生成器。

它会先经过一个最小但明确的材料理解层：

1. 识别输入类型
2. 从 PDF 提取文本
3. 清洗文本噪音
4. 压缩为一个 `MaterialSummary`
5. 再把这个摘要对象交给 `task run`

当前 `MaterialSummary` 至少包含：

- `title`
- `short_summary`
- `key_topics`
- `methods_or_entities`
- `useful_snippets`
- `relevance_to_project`
- `raw_text_excerpt`

这意味着：

- 系统不再只是“读到了 PDF”
- 而是会显式保存“它如何理解这个材料”

## 当前材料层做了什么

当前材料层已经做了：

- txt / md / pdf 类型识别
- PDF 文本提取
- 基础文本清洗
- 标题识别
- 高频主题词抽取
- 方法/实体关键词抽取
- useful snippets 提取
- 基于项目上下文的简单相关性判断
- 将材料摘要落盘到项目目录

## 当前材料层还没做什么

当前还没有做：

- OCR
- 复杂版面恢复
- 学术论文章节级精确解析
- 图表理解
- 引文结构抽取
- LLM 级别的深层语义理解

也就是说，这一层现在是：

> 一个规则驱动、可解释、足够支撑最小任务闭环的材料压缩层。

## 当前借鉴了什么

这一步我们只吸收了一个对 ClawLab 当前阶段真正有用的原则：

> 学习结果必须是本地、可读、可编辑的资产文件。

所以现在的资产不会只留在 JSON 里，也会额外落成 Markdown。

我们没有引入额外的代理框架、训练系统或复杂运行时，因为这些都不服务于当前的最小闭环。

## 当前支持两种运行模式

### 1. Local base mode

默认模式。

特点：

- 不需要 API key
- 不需要联网
- 使用规则驱动 / 模板驱动逻辑
- 现有最小闭环完整可运行

### 2. LLM enhanced mode

可选增强模式。

只有在你显式配置了 provider，并且设置了 API key 后，系统才会在少数模块上启用增强：

- materials
- drafts
- learning

如果配置不完整，系统不会崩溃，而是自动回退到规则版。

## 当前配置方式

ClawLab 当前使用本地配置文件：

- `clawlab.json`

其中会保存：

- `mode: local | hybrid`
- `provider: none | openai`
- `model`
- `use_llm_for_materials`
- `use_llm_for_drafts`
- `use_llm_for_learning`

默认就是：

- `mode = local`
- `provider = none`

也就是默认完全不依赖 API。

## 如何启用 LLM 增强

第一步，设置环境变量：

```bash
export OPENAI_API_KEY=your_api_key_here
```

第二步，在 `clawlab.json` 里把配置改成类似：

```json
{
  "workspace_root": "workspace",
  "active_project_id": null,
  "llm": {
    "mode": "hybrid",
    "provider": "openai",
    "model": "gpt-4o-mini",
    "use_llm_for_materials": true,
    "use_llm_for_drafts": true,
    "use_llm_for_learning": true,
    "openai_base_url": "https://api.openai.com/v1"
  }
}
```

## 如果不配置 API，哪些能力仍然可用

全部最小闭环都仍然可用：

- `init`
- `ingest-cv`
- `project create`
- `task run`
- `learn`
- `status`

也就是说：

> API 不是必须的，只是质量增强选项。

## 当前 LLM 支持的范围和边界

当前只在 3 个模块上支持可选增强：

- 材料理解
- draft 生成
- learning 总结

当前不会把整个系统改成 LLM-first，也不会删除规则版逻辑。

## Fallback 机制

如果出现下面任一情况：

- `mode = local`
- `provider = none`
- 相关模块的 LLM 开关关闭
- `OPENAI_API_KEY` 缺失
- provider 调用失败

系统都会自动退回到当前的规则版逻辑。

CLI 会尽量给出明确提示，而不是直接崩溃。

## 你为什么会需要它

如果你符合下面这些情况，ClawLab 就是为你准备的：

- 你是研究生或博士生
- 你已经有明确研究方向和项目
- 你手头有 CV、文献、笔记、草稿、项目说明等材料
- 你不想每次都从头向 AI 解释背景
- 你希望系统能从你的修改中学习，而不是每次都失忆
- 你希望这些内容沉淀在本地仓库里，而不是散落在聊天记录中

## 快速开始

### 1. 安装

要求：

- Python 3.11+
- 系统中可用 `pdftotext`

安装方式：

```bash
python3 -m pip install --user -e . --no-build-isolation
```

如果你暂时不想安装命令，也可以直接运行：

```bash
python3 -m clawlab.cli.main --help
```

### 2. 初始化工作区

```bash
clawlab init
```

### 3. 导入 CV

文本 CV：

```bash
clawlab ingest-cv examples/cv.txt
```

PDF CV：

```bash
clawlab ingest-cv examples/cv_sample.pdf
```

### 4. 创建项目

```bash
clawlab project create
```

### 5. 运行任务

使用文本材料：

```bash
clawlab task run literature-outline --project <project_id> --input examples/task_input.txt
```

使用 PDF 材料：

```bash
clawlab task run paper-outline --project <project_id> --input examples/material_sample.pdf
```

### 6. 手动修改 draft 后学习

```bash
clawlab learn --task <task_id> --revised examples/revised_outline.md
```

### 7. 查看当前状态

```bash
clawlab status
```

## 一个完整示例

最短路径就是：

```bash
clawlab init
clawlab ingest-cv examples/cv.txt
clawlab project create
clawlab task run literature-outline --project <project_id> --input examples/task_input.txt
clawlab learn --task <task_id> --revised examples/revised_outline.md
clawlab status
```

如果你想直接测试 PDF 输入：

```bash
clawlab ingest-cv examples/cv_sample.pdf
clawlab task run paper-outline --project <project_id> --input examples/material_sample.pdf
```

## 仓库结构

```text
clawlab/
  cli/
  core/
  services/
  storage/
  prompts/
  templates/
  utils/
examples/
workspace/
tests/
pyproject.toml
README.md
```

### 结构说明

- `clawlab/`：核心代码
- `workspace/`：本地研究工作区
- `examples/`：最小样例输入输出
- `tests/`：标准库 `unittest`

## 当前会沉淀什么

ClawLab 当前会在本地仓库里沉淀这些核心对象：

- `ResearcherProfile`
- `ProjectCard`
- `TaskCard`
- `TaskPlan`
- `MaterialSummary`
- `ReusableAsset`

这些对象共同构成你的最小研究工作上下文和经验层。

## 当前不支持什么

当前版本明确不支持：

- OCR
- DOCX / HTML 解析
- 数据库
- 联网检索
- 多项目编排系统
- 复杂 agent runtime
- 自动执行代码或实验
- embedding 检索

因为当前优先级非常明确：

> 先把 Python CLI-first 的最小研究协作闭环做稳。

## 当前验证方式

运行：

```bash
python3 -m unittest discover -s tests
```

## 下一步最关键的缺口

当前最关键的缺口不是“再加更多命令”，而是：

> 继续增强材料摘要规则，让长 PDF 的结构识别、主题抽取和 snippet 选择更稳。

如果再往前走一步，才值得考虑在这个材料层之上接入 LLM 做更强的结构化理解。
