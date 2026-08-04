# SOUL.md 瘦身方法论（2026-08-04 实战：14KB → 6KB 路由器版）

## 触发信号

用户抱怨"平时也看到网安/数模/逆向内容"（无关内容常驻）或"该触发架构却没触发"（关键指令被淹没）。
根因：SOUL.md 每次会话必注入，把所有架构细节内联 = 无关内容全量常驻 + 路由指令被 14KB 噪声淹没。

## 执行步骤

1. **备份**：`cp SOUL.md SOUL.md.bak.<date>`（git-bash 下 cp 路径用**单引号**包裹，避免内嵌 `\"` 转义导致 eval 解析失败）
2. **删前验证覆盖**：逐项 grep 对应 skill/references 确认细节有兜底再删（关键词如 `browser_vision|prisma|executeRawUnsafe|截图`）。发现缺口**先补进 skill 再删 SOUL**，零信息丢失
3. **新结构**：SOUL.md 只保留 身份 + 任务路由表（触发词→skill 名）+ 全局铁律（进度汇报/编码前确认/验证闭环/Windows 环境坑）+ 沟通风格；架构细节全部交给 skill 按需加载
4. **双份同步**：全局 `$HERMES_HOME/SOUL.md` 与 `profiles/<name>/SOUL.md` 可能并存同源副本，都要同步（`diff` 验证 IDENTICAL）；子 Agent profile（kimi-coder/glm-review/kimi）若为 Hermes 默认模板则不动
5. **生效时机**：系统提示词在会话开始时固定，改完 SOUL.md 要 `/new` 或新会话才生效，必须明确告知用户
6. **同步规则改写**：架构/模型/Profile 变更 → 更新对应 skill（或 refs），不再改 SOUL 细节；SOUL 只维护路由表与全局铁律

## 路由表设计要点

- 每行：任务类型 + 典型触发词（含用户口语词，如"暴力思考"）+ 加载的 skill 名
- 覆盖用户全场景：编程 / 数模方案 / 数模解题 / 数模全流程 / 逆向取证 / 舆情采集 / 技术侦察 / LLM 桌面应用 / Prisma
- 路由表放 SOUL.md 最靠前位置，保证优先级

## Pitfall：skill_view 索引范围

- `skill_view`/`skills_list` 只索引 **profile 级** skills（`profiles\<name>\skills\`），**全局** `$HERMES_HOME\skills\` 下的架构类 skill（multi-agent-pipeline、brute-force-think、math-brainstorm、数模系列）对 skill_view **不可见**（报 not found，available_skills 只列部分）
- 定位方式：`search_files(target='files', pattern='SKILL.md', path=$HERMES_HOME)` 找实际路径 → `read_file` 直读
- skills 实际分两套：全局 `hermes\skills\`（架构类）+ profile 级 `profiles\<name>\skills\`（用户自建：微博/APK/本地AI应用等）
- 同一 skill 可能在不同位置重复存在（如 apk-forensics 在 forensics/、software-development/、data-science/ 三处）
