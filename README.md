# 📄🐣 PaperPulse

> **让 AI 读论文，也把证据一起带回来。**

论文总结并不难。真正困难的是：快速抓住论文的核心矛盾，分清贡献与包装，看懂关键方法，并让每个重要结论都能回到原文图表核验。

**PaperPulse** 是一个面向 CS / AI / LLM 论文的 Codex Skill。它把本地 PDF 转换为一篇有叙事、有证据、有判断的中文图文简报：自动提取正文，定位并裁剪关键 Figure / Table，围绕论文主线组织解读，最终生成可直接阅读和分享的 HTML 页面。

**不是把 Abstract 翻译一遍，而是交付一篇真正值得读的论文解读。**

[查看在线样例](https://w1ndz321.github.io/paperpulse-skill/a-mem-agentic-memory/report.html) · [快速开始](#-快速开始) · [了解工作原理](#-工作原理)

---

## ✨ 为什么是 PaperPulse

普通 AI 摘要往往只留下结论，却丢掉了最重要的依据。PaperPulse 把论文阅读拆成三个相互约束的环节：

- **先读懂**：提取论文正文并去除参考文献噪声，识别问题、方法、实验与限制。
- **再取证**：从原始 PDF 中裁出关键方法图、结果表、消融实验和失败案例，让结论可以核验。
- **最后成文**：用面向技术读者的中文写成完整简报，既讲清论文，也给出有依据的评价。

它尤其关注传统论文总结容易忽略的部分：

- 方法图到底解释了什么，而不只是“如图所示”；
- 实验提升是否来自公平比较，还是设置差异；
- 消融、成本、延迟和失败案例会不会改变结论；
- 论文真正解决了什么，还有哪些边界没有覆盖。

---

## 📦 最终会得到什么

每篇论文生成一个独立、可追溯的输出目录：

```text
outputs/<论文标题关键词>/
├── source_text.md   # 从 PDF 提取并清理后的正文
├── captions.json   # 图表标题、页码、上下文与论文链接
├── images/         # 从原始 PDF 裁出的候选图表
├── report.md       # 中文图文简报
└── report.html     # 可本地阅读、可托管分享的页面
```

`source_text.md` 和 `captions.json` 保留处理依据；`report.md` 便于继续编辑；`report.html` 适合直接阅读或部署到 GitHub Pages。

---

## 📖 在线样例

| 类型 | 论文解读 |
|---|---|
| Agent Memory | [别再把 Agent 的记忆当数据库了：A-MEM 让它学会整理、联想和更新经验](https://w1ndz321.github.io/paperpulse-skill/a-mem-agentic-memory/report.html) |
| Long Context | [8K 窗口硬闯 350 万 tokens：MemAgent 让模型学会边读边记](https://w1ndz321.github.io/paperpulse-skill/memagent-reshaping-long-context/report.html) |
| Context Engineering | [别再把 Prompt 越改越短了：ACE 让大模型把经验攒成一本会进化的攻略书](https://w1ndz321.github.io/paperpulse-skill/ace-agentic-context-engineering/report.html) |
| Coding Agent | [会写代码不等于会修仓库：SWE-bench 把大模型拉进真实 GitHub 现场](https://w1ndz321.github.io/paperpulse-skill/swe-bench-can-language-models-resolve/report.html) |
| Agent Training | [别再把 Agent 关在玩具环境里：Agent-World 想给它造一座会进化的训练城市](https://w1ndz321.github.io/paperpulse-skill/agent-world-scaling-real-world-environment/report.html) |
| Reinforcement Learning | [别再把奖励平均撒给每个 token：FIPO 想让大模型学会哪一步推理真有用](https://w1ndz321.github.io/paperpulse-skill/fipo-future-kl-policy-optimization/report.html) |

<details>
<summary>查看更多已生成的论文解读</summary>

- [AI 进入 HR，不只是自动筛简历：一张人才分析的全景地图](https://w1ndz321.github.io/paperpulse-skill/comprehensive-survey-artificial-intelligence-techniques/report.html)
- [招聘匹配的难点不是推荐，而是说清楚“为什么这个人适合这份工”](https://w1ndz321.github.io/paperpulse-skill/person-job-fit-adapting-right-talent/report.html)
- [让表格特征工程不再靠拍脑袋：MALMAS 给 LLM Agent 装上记忆后，开始会复盘了](https://w1ndz321.github.io/paperpulse-skill/memory-augmented-llm-based-multi-agent-system-automated/report.html)
- [别只训练模型了：让 Coding Agent 的操作系统自己进化起来](https://w1ndz321.github.io/paperpulse-skill/agentic-harness-engineering/report.html)
- [让 AI 团队不再群聊：RecursiveMAS 把多智能体协作搬进隐空间循环](https://w1ndz321.github.io/paperpulse-skill/recursive-multi-agent-systems/report.html)
- [别再只盯参数了：DeepSeek-V4 真正想回答的是百万 token 怎么跑得动](https://w1ndz321.github.io/paperpulse-skill/deepseek-v4-towards-highly-efficient-million-token/report.html)
- [别只让多模态模型看清楚：DeepSeek 让它边想边指](https://w1ndz321.github.io/paperpulse-skill/thinking-visual-primitives/report.html)

</details>

仓库样例覆盖新方法论文、综述、Benchmark 和系统论文。实际处理时间取决于论文长度、图表数量和排版复杂度；常规论文通常可在数分钟内完成。

---

## 🚀 快速开始

### 1. 安装依赖

需要 Python 3.9 或更高版本：

```bash
python -m pip install pymupdf pymupdf4llm markdown jinja2
```

其中 `pymupdf` 和 `pymupdf4llm` 用于 PDF 解析与裁图；`markdown` 和 `jinja2` 用于完整 HTML 渲染。

### 2. 安装 Skill

可以直接让 Codex 安装：

```text
请从 https://github.com/w1ndz321/paperpulse-skill 安装 paperpulse-skill
```

也可以手动克隆到 Codex Skills 目录：

```bash
git clone https://github.com/w1ndz321/paperpulse-skill ~/.codex/skills/paperpulse-skill
```

### 3. 阅读论文

在 Codex 中提供本地 PDF 路径：

```text
使用 $paperpulse-skill 阅读这篇论文：/path/to/paper.pdf
```

也可以补充你关心的方向，例如：

```text
使用 $paperpulse-skill 阅读 /path/to/paper.pdf，重点分析方法创新、实验可信度和落地成本。
```

结果默认写入当前工作目录下的 `outputs/<论文标题关键词>/`。

---

## ⚙️ 工作原理

```text
本地 PDF
   ↓
正文提取与参考文献清理
   ↓
Figure / Table 检测、裁剪与上下文记录
   ↓
基于论文主线选择关键证据
   ↓
中文解读、研究点评与后续方向
   ↓
Markdown + GitHub Pages-ready HTML
```

脚本负责可重复的文本提取、图表裁剪和页面渲染；Codex 负责需要研究判断的部分，包括证据选择、叙事组织、结论核对和局限分析。这种分工比纯脚本更灵活，也比只生成文字摘要更容易审查。

---

## 🛡️ 质量保障

PaperPulse 在工作流中保留了几项明确的质量约束：

- **原文优先**：默认只依据本地 PDF，不会为了补齐链接或结论擅自搜索网络。
- **截图完整**：入选图表需要保留图体、图例、坐标轴、表头、注释和原始 Caption。
- **结论可追溯**：正文、图表元数据和最终报告分别保存，便于回查生成依据。
- **结果可验证**：内置检查器会验证标题、TL;DR、论文元数据、图片引用和 HTML 文件。
- **人工式审校**：最终选中的截图和渲染页面需要经过视觉检查，避免裁剪缺失或版式错位。

可以手动运行验收：

```bash
python ~/.codex/skills/paperpulse-skill/scripts/validate_report.py \
  outputs/<论文标题关键词>/report.md \
  --html outputs/<论文标题关键词>/report.html
```

---

## 🎯 适合与不适合的场景

PaperPulse 适合：

- 快速判断一篇论文是否值得精读；
- 为组会、技术分享或公众号准备图文材料；
- 核对论文的关键实验结果、消融和限制；
- 将本地论文整理为可持续编辑和分享的知识资产。

它目前不以扫描版 OCR、批量文献综述或跨论文检索为主要目标。复杂双栏、跨页表格和特殊出版模板仍可能需要人工调整裁剪。生成的 HTML 使用公共 CDN 加载页面样式，离线环境下内容仍可打开，但视觉效果可能不完整。

---

## 🤝 关于项目

PaperPulse 的目标不是替代完整的论文精读，而是把最耗时的第一轮筛选和内容整理做得更快、更可靠：**用几分钟建立全局理解，用原始图表保留判断依据。**

项目由 [Codex](https://openai.com/codex) 与 [Claude](https://claude.ai)（Anthropic）辅助开发。
