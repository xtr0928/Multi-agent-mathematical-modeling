#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""协同编码管线：反思评委 skill 不足
GLM 5.3 → 架构层分析（评委 skill 为什么系统性高估）
Kimi K3 → 内容层审查（题目原文逐句对照找论文缺失）
DeepSeek（本会话）→ 汇总 + 修订评委 skill
"""
import json, sys
sys.path.insert(0, '/tmp/solve_mcm2026C_v5/pipeline')
from llm_client import ask

BASE = '/tmp/solve_mcm2026C_v5'

# 外部评审全文（压缩后给模型）
EXTERNAL_REVIEW = """外部评审结论：66-70/100（H 奖，乐观 M 下沿），自评 86 → 系统性高估 16-20 分。
8 条问题（已验证属实的标注）：
1.【致命·属实】Q3 漏掉题目点名的职业舞者(different professional dancers)影响——只做了年龄+行业
2.【严重·属实】Q2 争议案例只给最早一周快照，整季反事实没做，自承 future work
3.【严重】核心份额估计自证接近噪声(L1 仅比随机好 4.7%)，但 Q2/Q3/Q4 全部继续用点估计做下游分析
4.【明显·属实】推荐理由自相矛盾：§4.2 说 percent 限制粉丝补偿，但论文自说 rank 才限制，且 rank 重放率 84.5% > percent 83.3%，却推荐 percent
5.【明显·属实】数字矛盾：Table 1 写 rank 14/save 52 周，实际是 10/56（已用 panel.json 验证）；"Section 4.4"引用不存在
6.【技术错误·属实】最大熵≠MAP：均匀先验+0/1 指示似然下后验在可行集均匀，MAP 不唯一
7.【属实】RDF 81.8% 低于旧规则未解释；"平台"实为 82.6%→78.8% 单调下降；公平性无量化
8. 回归无标准误；AI 修辞痕迹；页眉占位符"""

GLM_TASK = f"""你是管线架构评审专家。背景：
- 我方数模管线 V5：claims registry（数字声明注册+冲突检测）+ 四方核对脚本（34 项数字检查）+ 种子库回归（5 种子 100% 召回）+ 三模型独立评审 + 七维评分（摘要15/建模25/完整20/验证15/写作10/图表10/创新5）
- 自评 86 分 vs 外部真人评审 66-70 分，系统性高估 16-20 分

外部评审意见：
{EXTERNAL_REVIEW}

任务：分析「评委 skill + 门禁机制」为什么系统性高估。输出 JSON：
{{"root_causes": [每条一个根因，格式："缺陷名：机制为什么漏检+为什么给了高分"],
  "skill_gaps": [评委 skill 缺失的检查维度（具体到可在 skill 里落地的检查项）],
  "gate_gaps": [门禁脚本缺失的检查类型],
  "scoring_fix": "七维评分权重/锚点应如何调整"}}"""

KIMI_TASK = f"""你是数模竞赛评审。背景：我方提交了 2026 MCM C（DWTS）论文。
题目要求原文要点：Q1 估计粉丝票+一致性+确定性；Q2 对比两种投票方法+4 个争议名人案例（Jerry Rice/Billy Ray Cyrus/Bristol Palin/Bobby Bones）+底二裁决+推荐；Q3 分析舞者和名人特征（年龄、行业等）如何影响评委分和粉丝票+两者是否一致；Q4 新系统+Memo。

论文实际内容（我方自述）：双路线份额反演（最大熵/LP集合识别）、模拟恢复实验（L1 比随机好 4.7%）、反事实重放（percent 83.3%/rank 84.5%）、争议案例仅最早一周快照、Q3 只做年龄+行业（漏舞伴）、RDF 新系统（81.8% 重放）。

外部评审指出（已验证属实）：漏舞伴效应、争议案例没做整季、Table 1 数字 14/52 应为 10/56、推荐理由自相矛盾、最大熵≠MAP 表述错误。

任务：以最挑剔的评委视角，找出「题目要求 vs 论文实际」还有哪些遗漏或弱覆盖（外部评审已列的除外）。输出 JSON：
{{"additional_gaps": ["每条：题目要求什么 vs 论文给了什么"]}}"""

for provider, task, outfile in [('glm', GLM_TASK, 'glm_skill_analysis.json'),
                                ('kimi', KIMI_TASK, 'kimi_gap_check.json')]:
    print(f'[{provider}] 分析中...', flush=True)
    r = ask(provider, '你是数模管线评审专家，输出必须严格 JSON。', task,
            max_tokens=32000 if provider == 'kimi' else 16000)
    if 'error' in r or not r.get('content'):
        print(f'[{provider}] 错误: {r.get("error", "empty")[:100]}', flush=True)
        continue
    txt = r['content']
    if txt.startswith('```'):
        txt = txt.split('\n', 1)[1]
        txt = txt.rsplit('```', 1)[0] if txt.rstrip().endswith('```') else txt
    s, e = txt.find('{'), txt.rfind('}')
    try:
        parsed = json.loads(txt[s:e+1])
    except Exception:
        parsed = {'raw': txt[:2000]}
    json.dump({'content': txt, 'parsed': parsed}, open(f'{BASE}/{outfile}', 'w'),
              ensure_ascii=False, indent=1)
    print(f'[{provider}] 完成', flush=True)
print('ALL DONE')
