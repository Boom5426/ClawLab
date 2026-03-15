# Company Mapping

## 为什么要先做映射，而不是直接改名

ClawLab 当前已经有一套稳定的底层对象和主流程。

如果下一阶段要把它演化成“虚拟研究公司”模式，正确做法不是立刻把所有对象重命名成公司术语，而是先明确：

- 什么是稳定内核
- 什么是上层产品隐喻
- 什么是未来多 Agent 协作层

原因很简单：

> 当前底层模型解决的是状态管理和工作流问题，而不是品牌叙事问题。

如果太早把底层直接替换成公司术语，反而会让数据模型变得漂移、模糊和难维护。

## 当前内核对象到公司模式的映射

| 当前内核对象 | 未来公司模式中的上层隐喻 | 说明 |
| --- | --- | --- |
| `ResearcherProfile` | `FounderProfile` / `BossContext` | 表示老板是谁、擅长什么、偏好什么 |
| `ProjectCard` | `ActiveMission` / `ActiveBusiness` | 表示当前公司最重要的任务线 |
| `TaskCard` | `WorkOrder` / `Job` | 表示某次具体派单或工作请求 |
| `ReusableAsset` | `HandbookEntry` / `SOP` / `TrainingMemory` | 表示公司内部沉淀下来的规则、模板和操作记忆 |
| `MaterialSummary` | `ResearchBrief` / `MaterialBrief` | 表示员工开始干活前看到的材料摘要 |
| `TaskPlan` | `ExecutionPlan` / `ManagerPlan` | 表示 COO/PM 在任务开工前形成的执行计划 |

## 哪些底层对象应该保留不动

下面这些对象应当尽量保持稳定：

- `ResearcherProfile`
- `ProjectCard`
- `TaskCard`
- `ReusableAsset`
- `MaterialSummary`
- `TaskPlan`

原因：

1. 它们当前已经支撑了完整闭环
2. 它们是落盘 JSON 契约
3. 它们已经被 CLI、服务层、测试和 workspace 结构共同依赖
4. 未来上层换隐喻，不代表底层状态模型也要一起换

换句话说：

> 这些对象更像“内核对象”，不是“产品文案对象”。

## 哪些是上层隐喻，而不是底层模型

下面这些更适合放在未来的产品层、Agent 层、叙事层：

- 老板 / 创始人
- 虚拟员工
- COO / Project Manager
- 公司 handbook
- 训练记忆
- 派单 / 部门 / 岗位

这些词有助于构建交互体验，但不适合在当前阶段直接替换底层数据结构。

## 为什么不能一开始就彻底换掉底层模型

主要有 4 个原因：

1. **当前底层对象已经足够通用**
   - `ProjectCard` 和 `TaskCard` 本身就可以承接“公司任务”语义
2. **当前持久化结构已经稳定**
   - workspace 目录、JSON 契约、索引文件都围绕当前模型设计
3. **未来公司模式本质上是编排层**
   - 它更像“谁来读这些对象、谁来消费这些对象”，而不是“把对象全部换名”
4. **过早替换会让演化失控**
   - 现在需要的是上层映射，而不是底层重写

## 推荐的演化方式

推荐采用三层结构：

1. **Kernel Layer**
   - 继续保留当前对象和主流程
2. **Company Layer**
   - 给当前对象增加老板、经理、员工的叙事解释
3. **Future Multi-Agent Layer**
   - 让不同 Agent 读取同一个 kernel state，并在其上协作

## 一个具体例子

当前：

- `ResearcherProfile` = 研究者画像
- `ProjectCard` = 当前项目
- `TaskCard` = 一次 outline 任务

未来公司模式下：

- `ResearcherProfile` 可以被上层解释为老板上下文
- `ProjectCard` 可以被上层解释为公司当前主任务
- `TaskCard` 可以被解释为 PM 发给虚拟员工的一张工单

但是：

- 底层 JSON 字段可以不变
- CLI 主流程可以不变
- workspace 结构可以基本不变

真正变化的是：

- 谁在使用这些对象
- 谁在解释这些对象
- 谁在这些对象上做协作分工

这才是更稳的演化路径。
