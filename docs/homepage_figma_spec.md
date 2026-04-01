# Homepage Figma Spec

## Purpose

This document is the homepage design spec for a future Figma file for the project `泛应急新闻 Agent`.

Homepage positioning:

- Internal operations dashboard, not a public marketing homepage
- Primary users: product manager, analyst, operator
- Primary goal: quickly understand this week's pipeline status, report output, and key signals

## Figma File Suggestion

- File name: `泛应急新闻Agent - Dashboard`
- Page name: `Homepage`
- Main frame name: `Dashboard / Home / Desktop`
- Desktop frame size: `1440 x 1600`
- Mobile frame size: `390 x 1200`

## Visual Direction

- Tone: calm, operational, trustworthy
- Style: intelligence dashboard + editorial report cockpit
- Layout: wide desktop, card-based, dense but readable
- Keywords: structured, analytical, stable, signal-first

## Design Tokens

### Colors

- `bg/page`: `#F3F6FB`
- `bg/panel`: `#FBFCFE`
- `bg/nav`: `#0F172A`
- `bg/card-dark`: `#162033`
- `text/primary`: `#111827`
- `text/secondary`: `#5B6475`
- `text/inverse`: `#F8FAFC`
- `line/subtle`: `#D7DFEA`
- `accent/blue`: `#2563EB`
- `accent/cyan`: `#0891B2`
- `accent/green`: `#0F766E`
- `accent/orange`: `#C2410C`
- `accent/red`: `#B91C1C`
- `status/success-bg`: `#DCFCE7`
- `status/warn-bg`: `#FEF3C7`
- `status/error-bg`: `#FEE2E2`

### Typography

- Chinese font: `Source Han Sans SC`
- English fallback: `IBM Plex Sans`
- Number font for KPI: `IBM Plex Mono`

### Type Scale

- Page title: `32 / 40 / Semibold`
- Section title: `20 / 28 / Semibold`
- Card title: `16 / 24 / Semibold`
- Body: `14 / 22 / Regular`
- Small meta: `12 / 18 / Regular`
- KPI number: `34 / 38 / Semibold`

### Spacing

- Page padding: `32`
- Section gap: `24`
- Card padding: `20`
- Grid columns: `12`
- Grid gutter: `20`
- Card radius: `18`

### Effects

- Card shadow: `0 10 30 0 rgba(15, 23, 42, 0.06)`
- Large hero shadow: `0 18 50 0 rgba(15, 23, 42, 0.10)`

## Information Architecture

Homepage modules from top to bottom:

1. Top navigation
2. Hero overview
3. KPI cards
4. This week signal focus
5. Pipeline run status
6. Latest weekly report summary
7. Source health and quick actions

## Frame Structure

```text
Dashboard / Home / Desktop
  Top Nav
  Hero Overview
  KPI Row
  Signals + Timeline Row
  Latest Report Section
  Source Health + Quick Actions Row
```

## Component Spec

### 1. Top Navigation

Purpose:

- Provide orientation and top-level entry points

Layout:

- Full width top bar
- Height: `72`
- Background: `bg/nav`
- Left: product title
- Right: nav items + environment badge

Content:

- Product title: `泛应急新闻 Agent`
- Subtitle: `Weekly Intelligence Operations`
- Nav items:
  - `首页`
  - `信源管理`
  - `运行记录`
  - `周报列表`
  - `规则设置`
- Environment badge: `MVP`

### 2. Hero Overview

Purpose:

- Give a fast summary of current system state

Layout:

- Two-column hero card
- Left column width: `8/12`
- Right column width: `4/12`
- Min height: `240`
- Background: dark gradient from `#162033` to `#0F3A5B`

Left content:

- Eyebrow: `本周概览`
- Main title: `每周稳定产出泛应急行业重点信号`
- Description:
  `从新闻、机构公告、论文与社区中提炼高价值事件，形成可追溯、可复盘的中文周报。`
- Primary button: `查看最新周报`
- Secondary button: `查看运行记录`

Right content:

- Small stat block 1:
  - Label: `最新周报`
  - Value: `2026.03.16 - 2026.03.22`
- Small stat block 2:
  - Label: `当前阶段`
  - Value: `MVP 已跑通`
- Small stat block 3:
  - Label: `工作重点`
  - Value: `内容质量 / 信源质量 / 稳定运营`

### 3. KPI Cards

Purpose:

- Highlight the most important operating metrics

Layout:

- 4 cards in one row
- Each card height: `132`

Cards:

1. `本周采集条数`
   - Value: `22`
   - Helper: `来自主信源注册表`
2. `本周入选条数`
   - Value: `1`
   - Helper: `进入 Top Report`
3. `测试通过`
   - Value: `9/9`
   - Helper: `最近执行日期 2026-03-26`
4. `主信源数量`
   - Value: `22`
   - Helper: `Quick 源 3 个`

Notes:

- These values reflect current repo evidence and should become dynamic later

### 4. This Week Signal Focus

Purpose:

- Make the homepage feel editorial, not only operational

Layout:

- Large feature card on left
- Width: `7/12`

Card title:

- `本周重点信号`

Featured item:

- Headline: `Agency launches drone and satellite pilot for disaster mapping`
- Source meta: `Mock Agency Release · official`
- Summary:
  `无人机部署与卫星通信结合，应用于洪灾场景中的搜索救援与灾害制图，是当前跨领域信号最清晰的代表事件。`
- Tags:
  - `AI`
  - `Drones`
  - `Communications`
  - `Emergency Response`
- Footer note:
  `建议持续跟踪后续验证、规模化部署与政策层面的跟进动作。`

### 5. Pipeline Run Status

Purpose:

- Visualize the workflow and latest execution status

Layout:

- Timeline card on right
- Width: `5/12`

Card title:

- `流水线运行状态`

Timeline items:

1. `Collect` - `完成`
2. `Normalize` - `完成`
3. `Dedup` - `完成`
4. `Classify` - `完成`
5. `Score` - `完成`
6. `Analyze` - `完成`
7. `Report` - `完成`

Footer:

- `最近验证：python3 -m unittest discover -s tests`

### 6. Latest Weekly Report Summary

Purpose:

- Surface the current report structure and reading entry

Layout:

- Full-width section
- Title left, action right

Section header:

- Title: `最新周报摘要`
- Action link: `打开 Markdown 周报`

Content layout:

- Left: summary card
- Right: report structure card

Left summary card:

- Label: `Executive Summary`
- Three bullets:
  - `短期应重点观察后续验证、规模化部署与政策跟进。`
  - `AI、通信与应急能力正在更紧密地耦合。`
  - `官方来源仍是高重要性线索的主要来源。`

Right structure card:

- Label: `报告结构`
- Items:
  - `核心观点`
  - `本周核心主线`
  - `重点事件与解读`
  - `分领域深度观察`
  - `跨领域趋势`
  - `趋势判断与前瞻`
  - `下周建议关注`

### 7. Source Health

Purpose:

- Let operators quickly see source configuration quality

Layout:

- Left card in final row
- Width: `7/12`

Card title:

- `信源健康度`

Rows:

1. `主信源注册表` / `22 个来源` / `状态：已配置`
2. `轻量 Quick 注册表` / `3 个来源` / `状态：已配置`
3. `X API` / `按环境变量启用` / `状态：可选`
4. `模型 Provider` / `mock / openai_compatible` / `状态：可切换`

### 8. Quick Actions

Purpose:

- Turn the homepage into a useful control panel

Layout:

- Right card in final row
- Width: `5/12`

Card title:

- `快捷操作`

Buttons:

- `运行单次采集`
- `生成周报`
- `查看需求文档`
- `查看项目管理文档`

Helper text:

- `建议默认先查看运行记录，再执行人工复核。`

## Desktop Wireframe

```text
+--------------------------------------------------------------------------------------------------+
| Top Nav                                                                                          |
+--------------------------------------------------------------------------------------------------+
| Hero Overview                                               | Latest week / Stage / Focus        |
+--------------------------------------------------------------------------------------------------+
| KPI 1              | KPI 2              | KPI 3              | KPI 4                              |
+--------------------------------------------------------------------------------------------------+
| This Week Signal Focus                                      | Pipeline Run Status                 |
| featured item, tags, summary                                | vertical timeline                   |
+--------------------------------------------------------------------------------------------------+
| Latest Weekly Report Summary                                                                        |
| Executive Summary Card                                  | Report Structure Card               |
+--------------------------------------------------------------------------------------------------+
| Source Health                                            | Quick Actions                        |
+--------------------------------------------------------------------------------------------------+
```

## Mobile Adaptation

- Use a single-column layout
- Order:
  1. Top nav
  2. Hero overview
  3. KPI cards as 2 x 2 grid
  4. This week signal focus
  5. Pipeline run status
  6. Latest weekly report summary
  7. Source health
  8. Quick actions
- Sticky bottom action:
  - `查看最新周报`

## Suggested Figma Layers

```text
Homepage
  Frame/Desktop
    Nav
    Hero
    KPI/Collected
    KPI/Selected
    KPI/Tests
    KPI/Sources
    Card/SignalFocus
    Card/PipelineStatus
    Section/LatestReport
    Card/SourceHealth
    Card/QuickActions
  Frame/Mobile
```

## Copy Deck

### Page Title

- `泛应急新闻 Agent`

### Homepage Header Copy

- `每周稳定产出泛应急行业重点信号`

### Supporting Copy

- `把分散在新闻、机构公告、论文与社区中的公开信息，转化为面向决策者的结构化周报。`

### CTA Copy

- `查看最新周报`
- `查看运行记录`
- `管理信源`

## Prototype Behavior

- Clicking `查看最新周报` goes to report detail page
- Clicking `信源管理` goes to source registry page
- Clicking `运行记录` goes to pipeline run log page
- Clicking `生成周报` opens a confirmation modal in prototype

## Future Dynamic Data Mapping

When implemented, map homepage cards to these repo concepts:

- `本周采集条数` -> pipeline result `items_collected`
- `本周入选条数` -> pipeline result `items_selected` or `items_screened_in`
- `测试通过` -> local test run summary
- `主信源数量` -> count of `data/source_registry.json`
- `最新周报` -> newest file under `outputs/weekly/`

## Handoff Notes

- This is a management dashboard homepage, not a consumer news portal
- Preserve the report-like seriousness of the project
- Avoid over-decorative charts in the first version
- Prefer strong typography and clear hierarchy over excessive widgets
