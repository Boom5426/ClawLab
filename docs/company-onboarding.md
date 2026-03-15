# Company Onboarding

## 为什么这是上层体验，而不是底层推翻

ClawLab 当前已经有稳定的底层内核：

- `ResearcherProfile`
- `ProjectCard`
- `TaskCard`
- `ReusableAsset`
- `MaterialSummary`
- `TaskPlan`

以及其上的：

- 员工层
- 经理层

所以“开公司”这一步的正确做法不是替换这些对象，而是：

> 用 founder / company / team 的语义，把现有内核包装成更自然的第一次使用体验。

## founder / company / team 如何映射到底层内核

### FounderProfile

`FounderProfile` 不是对 `ResearcherProfile` 的重建。

它只是一个很薄的映射层，记录：

- 这个研究者作为创始人的身份
- 他想让公司帮他做什么

底层研究能力、方法、工具、写作偏好仍然来自 `ResearcherProfile`。

### CompanyProfile

`CompanyProfile` 是上层配置对象，描述：

- 公司名字
- 使命
- 聚焦方向
- 当前业务类型
- 对应 founder
- 当前 active project

它不替代 `ProjectCard`。

### TeamConfig

`TeamConfig` 描述：

- 当前启用哪些员工角色
- 这些角色如何被解释
- 是否启用 manager

它不替代员工 registry，也不替代 manager orchestration。

## 为什么这层现在就值得做

因为当前系统虽然已经有内核、员工、经理，但首次使用体验仍然偏技术化：

- 先 init
- 可选 ingest-cv
- 再 company init / project create

对用户来说，这更像在装配系统，而不像在启动自己的虚拟研究公司。

`company init` 的作用，就是把这层体验整理出来。

## 当前 onboarding 的目标

当前 `company init` 会引导老板回答这些问题：

- 你是谁
- 你想让这家公司帮你做什么
- 这家公司聚焦什么方向
- 它现在是什么类型
- 你希望启用哪些员工

同时系统会：

- 优先读取已有 `ResearcherProfile`
- 如果还没有 profile，就先用最小 founder intake 创建一个基础档案
- 连接已有 active project
- 推荐一个 starter team
- 落盘 founder / company / team 配置

## 为什么不直接做 UI

因为当前真正需要的不是界面，而是：

- 统一首次使用入口
- 统一公司语义
- 统一 founder / project / team 的关系

CLI 足够完成这件事。
