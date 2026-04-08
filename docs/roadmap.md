# 泛应急 Agent 开发路线图

> 状态标记：✅ 已完成 | 🔄 进行中 | ⬜ 待开始 | 🔑 需要外部凭证
>
> 每次完成一项，更新状态标记 + 填写完成日期。

---

## 基础版本（v1.0）— ✅ 已完成

| 状态 | 功能 | 完成日期 |
|------|------|----------|
| ✅ | 端到端 pipeline（collect → normalize → dedup → classify → score → enrich → screen → analyze → report） | 2026-03-28 |
| ✅ | MD + HTML 双格式周报输出 | 2026-03-28 |
| ✅ | 中间产物落盘（`data/enriched/`、`data/scored/`） | 2026-03-28 |
| ✅ | 规则评分（classify/rules.py + score/rules.py） | 2026-03-28 |
| ✅ | LLM 分析接入（DeepSeek，openai_compatible 抽象） | 2026-03-28 |
| ✅ | 运行日志 `docs/weekly_run_log.md` | 2026-03-28 |
| ✅ | 风险登记 `docs/risk_register.md` | 2026-03-28 |

---

## v2.0 Sprint 计划

### Sprint 1+2+5 — ✅ 已完成（2026-04-01）

目标：4 专栏结构 + 信源扩充，报告不再"硬凑应急"。

| 状态 | 任务 | 完成日期 |
|------|------|----------|
| ✅ | 4 专栏结构（AI / Communications / Aviation / DisasterTech） | 2026-04-01 |
| ✅ | `analyze/prompts.py` 按 domain 区分分析视角 | 2026-04-01 |
| ✅ | 信源扩充：33 → 43 个（SpaceNews、Via Satellite、ITU、Aviation Week、CISA 等） | 2026-04-01 |
| ✅ | `source_registry.json` 新增 `enabled` 字段，禁用 8 个不可达信源 | 2026-04-02 |

---

### Sprint 3 — ✅ 已完成（2026-04-02）

目标：HTML 报告卡片显示缩略图。

| 状态 | 任务 | 完成日期 |
|------|------|----------|
| ✅ | `models.py` ScoredItem 增加 `thumbnail_url` 字段 | 2026-04-02 |
| ✅ | `collect/adapters.py` 新增 `_extract_og_image()` | 2026-04-02 |
| ✅ | `enrich/service.py` 透传 thumbnail_url | 2026-04-02 |
| ✅ | `report/html_renderer.py` 卡片渲染图片，失败优雅降级 | 2026-04-02 |

---

### Sprint 4 — ✅ 已完成（2026-04-03）

目标：手动 Grok 输入管道（弥补 X API 空缺）。

| 状态 | 任务 | 完成日期 |
|------|------|----------|
| ✅ | `data/manual/template.md` 标准填写模板 | 2026-04-03 |
| ✅ | `collect/manual.py` 解析模板 → RawItem | 2026-04-03 |
| ✅ | `collect/service.py` 自动合并本周 `data/manual/*.md` | 2026-04-03 |
| ✅ | `score/service.py` "Grok精选" 来源加权 +1.0 | 2026-04-03 |

---

### Sprint 6 — ⬜ 待开始

目标：验证 LLM 动态评分是否优于规则评分（先收集数据，不替换现有逻辑）。

| 状态 | 任务 | 预估工时 |
|------|------|----------|
| ⬜ | `.env` 增加 `EI_LLM_SCORING=true` 开关 | 0.5h |
| ⬜ | 并行记录规则分 vs LLM 分（双轨日志） | 2h |
| ⬜ | 4-6 周后人工评估决定是否切换 | — |

**验收标准：** 运行后 `data/scored/` 包含两套分数，可对比。

---

## 新增功能计划（New Pipeline）

### P0 — Feedback Agent ✅ 已完成（2026-04-05）

目标：筛选质量随读者反馈渐进式自我优化。

| 状态 | 任务 | 涉及文件 |
|------|------|----------|
| ✅ | 创建 `data/preferences.json`（boost/penalize/few_shot 结构） | `data/preferences.json` |
| ✅ | `src/emergency_intel/feedback/agent.py` — 读取 preferences 注入 prompt | 新建 |
| ✅ | `src/emergency_intel/feedback/review_generator.py` — 生成审阅文件 | 新建 |
| ✅ | `score/service.py` 集成 boost/penalize 关键词加权 | 修改 |
| ✅ | `analyze/prompts.py` 新增 `build_screening_prompt(prefs)` 函数 | 修改 |
| ✅ | `analyze/service.py` 使用 preferences 构建 screening prompt | 修改 |
| ✅ | pipeline 末尾自动生成审阅文件 `data/feedback/YYYY-WXX-review.md` | 修改 |

**preferences.json 结构：**
```json
{
  "boost": ["卫星直连", "应急专网", "低轨道", "网络恢复"],
  "penalize": ["商业推广", "产品发布会"],
  "preferred_sources": ["工信部", "应急管理部"],
  "few_shot_good": [],
  "few_shot_bad": [],
  "reader_notes": ""
}
```

**验收标准：** 第二次运行时 preferences.json 的关键词对评分有可见影响。

---

### P1 — Tavily 搜索接入 ✅ 已完成（2026-04-05）

目标：用 Grok API 替代手动粘贴，实现 X 平台内容自动采集。

> **所需凭证：** xAI API Key — 前往 [console.x.ai](https://console.x.ai) 注册获取
> 新增环境变量：`EI_GROK_API_KEY`、`EI_GROK_API_BASE`（默认 `https://api.x.ai/v1`）、`EI_GROK_MODEL`（默认 `grok-2`）

| 状态 | 任务 | 涉及文件 |
|------|------|----------|
| ✅ | `config.py` 新增 `EI_TAVILY_API_KEY` 配置项 | 修改 |
| ✅ | `collect/tavily_adapter.py` — 调用 Tavily API，返回 RawItem | 新建 |
| ✅ | `data/tavily_queries.json` — 按 4 个领域的搜索查询词配置 | 新建 |
| ✅ | `collect/service.py` 集成 Tavily 采集 | 修改 |
| ✅ | `pipeline.py` 传入 `tavily_api_key` | 修改 |
| ✅ | `.env.example` 补充 Tavily 配置示例 | 修改 |

**验收标准：** `.env` 中填入 `EI_TAVILY_API_KEY` 后，pipeline 自动搜索 4 个领域的最新内容并注入 pipeline。

---

### P2 — Summarize Agent Skill ✅ 已完成（2026-04-05）

目标：提升报告摘要质量，减少口语化和冗余。

| 状态 | 任务 | 涉及文件 |
|------|------|----------|
| ✅ | `models.py` 新增 `key_facts` 字段 | 修改 |
| ✅ | `analyze/prompts.py` 输出 schema 加入 `key_facts`（数字/日期/金额/技术参数） | 修改 |
| ✅ | `analyze/service.py` 提取 `key_facts` | 修改 |
| ✅ | `html_renderer.py` 卡片渲染 key_facts 标签样式 | 修改 |

**效果：** 每张卡片事件概述下方显示蓝色标签，如「金额：$1.2B」「时间：2026-Q3」「标准：3GPP Rel.18」。

---

### P3 — 视频/播客转录 Agent ✅ 已完成（2026-04-06）

目标：YouTube 频道和播客自动转录，提取关键信息注入 pipeline。

> **所需凭证：**
> - Groq API Key（推荐，$0.0011/min）— 前往 console.groq.com 注册
>   或 OpenAI API Key（$0.006/min）— 已有则复用
> - YouTube Data API Key（免费，Google Cloud Console 开启 YouTube Data API v3）
>
> **推荐 Groq Whisper API 而非本地 Whisper**：GitHub Actions 无 GPU，本地跑慢且占用 Actions 分钟数；每周 3-10 集约花费 $0.07-$0.70。

| 状态 | 任务 | 涉及文件 |
|------|------|----------|
| ✅ | `pyproject.toml` 新增依赖：`yt-dlp`、`feedparser` | 修改 |
| ✅ | `transcribe/service.py` — Groq Whisper API 转录 | 新建 |
| ✅ | `transcribe/summarizer.py` — 转录文本 → LLM 摘要 → RawItem | 新建 |
| ✅ | `collect/media_adapter.py` — YouTube / 播客 RSS / 手动 URL 三路 | 新建 |
| ✅ | `pipeline.py` 集成媒体采集（collect 后、normalize 前） | 修改 |
| ✅ | `source_registry.json` 新增 ITU/APCO/Lex/TWIAI（默认 disabled） | 修改 |
| ✅ | `data/media/template-urls.txt` 手动 URL 输入模板 | 新建 |

**计划信源（分批接入）：**

| 优先级 | 频道/播客 | 领域 |
|--------|-----------|------|
| 高 | Lex Fridman Podcast | AI |
| 高 | This Week in AI | AI |
| 高 | ITU Webinars | 通信/灾害 |
| 高 | APCO International（年会演讲） | 应急通信 |
| 中 | Hard Fork (NYT) | AI |
| 中 | DJI Enterprise Channel | 航空 |
| 中 | Andrej Karpathy 视频讲座 | AI |

**验收标准：** pipeline 运行后，至少 1 条播客/视频摘要出现在报告中。

---

## 筛选质量反馈闭环（RLHF-lite）

> 前置条件：P0 Feedback Agent 完成后启用。分三个阶段推进，每积累 2-3 期反馈进入下一阶段。

| 状态 | 阶段 | 说明 |
|------|------|------|
| ⬜ | Phase 1 — 反馈采集 | pipeline 末尾自动生成 `data/feedback/YYYY-WXX-review.md`，用户标注 `[ok]`/`[wrong]`/`[should]` |
| ⬜ | Phase 2 — 反馈统计（积累 2-3 期） | `feedback/store.py` 统计误判类型、低质量信源、灰色地带分数段 |
| ⬜ | Phase 3 — 自适应优化（积累 5+ 期） | few-shot 自动注入 prompt、各领域独立阈值、信源质量权重自动调整 |

---

## 凭证准备清单

| 状态 | 凭证 | 用于 | 获取方式 | 估计月成本 |
|------|------|------|----------|-----------|
| ⬜ | xAI API Key | P1 Grok API | console.x.ai | ~$5-15 |
| ⬜ | Groq API Key | P3 Whisper 转录 | console.groq.com | ~$0.07-0.70 |
| ⬜ | YouTube Data API Key | P3 视频监控 | Google Cloud Console | 免费 |

---

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0 | 2026-03-28 | MVP 上线，端到端 pipeline 可运行 |
| v2.0-alpha | 2026-04-01 | 4 专栏结构 + 信源扩充（S1+S2+S5） |
| v2.0-beta | 2026-04-02 | 图片缩略图（S3） |
| v2.0-rc | 2026-04-03 | 手动 Grok 管道（S4） |
| v2.1 | — | P0 Feedback Agent |
| v2.2 | — | P1 Grok API 直接接入 |
| v2.3 | — | P2 Summarize Agent |
| v2.4 | — | P3 视频转录 |
