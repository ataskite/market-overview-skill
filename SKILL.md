---
name: daily-market-overview
description: 自动生成每日市场概览笔记。触发词："市场怎么样"、"今天市场"、"市场表现"、"收评速览"、"行情怎么样"、"市场概览"。保存到 "06 市场观察/YYYY年市场记录/" 目录。
---

## 工作流程

> 1. **时间检查** → 确定交易日/假日模式
> 2. **实时数据获取** → playwright-cli 并行 + MCP 工具获取最新数据
> 3. **文件生成** → 按模板组装 Markdown
> 4. **输出确认** → wikilink 格式

---

## Step 1: 时间与模式检查

首先获取当前时间并判断模式：

```bash
TZ='Asia/Shanghai' date '+%Y-%m-%d %H:%M:%S %Z %u'
```

检查节假日缓存：

```bash
python3 scripts/update_holidays.py
```

如果提示节假日缓存缺失，使用 MCP 搜索工具查找官方放假安排。

**判断优先级**（从高到低）：

| 条件 | 模式 |
|:-----|:-----|
| 日期在 `holidays` 范围内 | 假日 |
| 日期在 `workday_overrides` 中 | 交易日（调休上班） |
| 周六/周日 | 假日 |
| 工作日 | 交易日 |

确定模式后读取对应模板：
- **交易日** → `references/template-trading-day.md`
- **假日** → `references/template-holiday.md`

---

## Step 2: 实时数据获取（无缓存，每次独立获取）

### 数据获取与并发执行

使用 `playwright-cli -s=<session>` 多会话并行获取数据（~15秒），辅以 MCP 工具获取新闻（~5秒）。

```bash
# === Playwright 并行获取（5个会话同时打开） ===
playwright-cli -s=a股 open "https://gu.sina.cn/m?type=hq#/index/index" &
playwright-cli -s=行情 open "https://www.cls.cn/quotation" &
playwright-cli -s=全球 open "https://gu.sina.cn/m?type=global#/world" &
playwright-cli -s=商品 open "https://wallstreetcn.com/markets/commodities" &
playwright-cli -s=收评 open "https://www.cls.cn/searchPage?keyword=收评&type=telegram" &
sleep 8

# 并行提取数据
A股数据=$(playwright-cli -s=a股 eval 'document.body.innerText') &
行情数据=$(playwright-cli -s=行情 eval 'document.body.innerText') &
全球数据=$(playwright-cli -s=全球 eval 'document.body.innerText') &
商品数据=$(playwright-cli -s=商品 eval 'document.body.innerText') &
收评数据=$(playwright-cli -s=收评 eval 'document.body.innerText') &
wait
```

MCP 工具并行获取新闻（与 playwright 同时发起）：
- `mcp__fetcher__fetch_url` → `https://finance.eastmoney.com/a/cywjh.html`（东方财富要闻）
- `mcp__local-web-reader__fetch_url` → `https://wallstreetcn.com/news/global`（华尔街见闻全球新闻）

**总预计耗时**：~20-25秒

---

### 数据提取任务

从各页面中提取以下数据（用自然语言理解页面结构，灵活提取）：

#### A股数据（从新浪财经页面 + 财联社行情页面，仅交易日）

**新浪财经 A股页面**：
- **A股指数**（5个）：上证指数、深证成指、创业板指、北证50、科创50（各含点位、涨跌、涨跌幅）
- **涨跌分布**：上涨家数、平盘家数、下跌家数
- **涨跌停统计**：涨停家数、跌停家数、昨涨停表现（连板溢价）
- **成交数据**：成交额、较上日变化、买卖对比（亿元）

**财联社行情页面**（`cls.cn/quotation`）：
- **涨跌中位数**
- **热门概念板块**（前6个）：板块名称、涨跌幅、每个板块前2个领涨股（股票名称、涨跌幅）
- **主力净流入 TOP5**：股票名称、净流入金额、涨跌幅

#### 财联社收评（从搜索页，仅交易日）

- 找到当日 **主板收评**（标题格式 `【收评：...】`，跳过 `【科创板收评：...】`）
- 提取标题和完整内容
- 如当日无主板收评，使用最近一个交易日的

#### 全球数据（从新浪财经全球页面，交易日+假日）

- **全球指数**：道琼斯、纳斯达克、标普500、恒生指数、日经225、首尔综合、台湾加权、富时100、德国DAX、法国CAC40
- **汇率**：美元指数、美元/离岸人民币、欧元/美元、英镑/美元
- **债券**：中国10年期国债收益率、美国10年期国债收益率

#### 大宗商品（从华尔街见闻页面，6个品种）

- 现货黄金(XAUUSD)、现货白银(XAGUSD)、布伦特原油(UKOIL)、WTI原油(USCL)、伦敦期铜(UKCA)、伦敦期铝(UKAH)
- 各含价格、涨跌额、涨跌幅

#### 市场要闻（从东方财富 + 华尔街见闻，每日执行）

从两个新闻源识别文章列表，提取标题、URL、发布时间、摘要。

**筛选原则**（国内10条 + 海外10条）：
- 🔴 最高：重大政策/监管变化、黑天鹅/突发事件、美联储货币政策、AI前沿突破
- 🟠 高：市场重大异动、重要经济数据、美股七姐妹动态、华尔街/彭博重要观点
- 🟡 中：行业拐点/主线切换、地缘重大事件（中美/关税/制裁）、全球重要公司
- 🟢 低：常规跟踪

**排除**：收评类新闻不选入（已单独展示）；主题多样性 > 时效优先 > 去噪 > 投资参考价值

---

## Step 3: 文件生成

### 命名规则

- 目录：`06 市场观察/YYYY年市场记录/`（首次运行 `mkdir -p`）
- 格式：`YYYY-MM-DD [15-30字核心内容].md`（中文标点，无英文标点）

### 涨跌配色

- 上涨：`<font color=#fb4b4b>+X.XX%</font>`（红色）
- 下跌：`<font color=#1fe059>-X.XX%</font>`（绿色）

### 模板填充

根据交易日/假日模式，将提取的数据填充到对应模板中。

### 极简速览生成

**规则**：用200字以内自然语言提炼当日要点
- **优先级**：重大政策/事件 > 市场异动 > 主线板块
- **顺序**：先国内再全球
- **格式**：直接写内容，使用引用格式

---

## Step 4: 投研分析（可选）

### 触发条件

满足**任一**时才添加此部分：
- 用户明确要求
- 重大政策/黑天鹅事件
- 市场主线明显切换
- 成交量异常变化

### 分析内容

搜索用户近1个月的投研笔记（假日模式扩展到2个月），按关键词匹配相关性，最多引用3篇。

详细框架见：`references/market-analysis-guide.md`

**如果未触发，请勿在笔记中包含此部分！**

---

## Step 5: 输出确认

### 文件保存

将生成的 Markdown 内容保存到 Obsidian vault：

```bash
/Users/jiangkun/Documents/同步空间/江琨的笔记/06 市场观察/YYYY年市场记录/YYYY-MM-DD [核心内容].md
```

### 清理临时数据

```bash
# 清理所有 playwright 会话
playwright-cli -s=a股 close &
playwright-cli -s=行情 close &
playwright-cli -s=全球 close &
playwright-cli -s=商品 close &
playwright-cli -s=收评 close &
```

### 输出确认

```
✅ 市场概览已生成：[[06 市场观察/YYYY年市场记录/FILENAME]]
```

---

## 容错机制

### 数据源失败

- **单源失败**：该数据项标注"数据暂缺"，继续处理其他数据
- **全部失败**：在对应部分标注"⚠️ 数据源异常"
- **部分失败**：正常展示已获取的数据

### 页面结构变化

- 用自然语言理解页面，找到相关内容
- 如果无法理解数据结构，标注"页面结构已变化，请手动检查"
- 不要崩溃或停止执行

### 工具降级

- **playwright-cli 并行失败**：可降级为单次串行获取，或尝试使用 agent-browser
- **MCP 工具失败**：标注"数据暂缺"，继续执行

---

## 参考文档

按需读取，不纳入每次调用上下文：

- `references/template-trading-day.md` — 交易日模板
- `references/template-holiday.md` — 假日模板
- `references/market-analysis-guide.md` — 投研分析框架

---

## 关键提醒

1. **每次执行都是独立的**：不使用缓存，每次都获取最新数据
2. **理解优于匹配**：用 AI 理解能力适应页面变化，不要硬编码正则
3. **容错优先**：部分数据缺失不影响整体生成
4. **用户可读**：生成的笔记应该是人类可读、有价值的
5. **工具选择**：playwright-cli 并行为主，MCP 工具为辅
6. **大宗商品**：只关注6个主要品种（黄金、白银、布伦特原油、WTI原油、铜、铝）
7. **并行执行**：使用 `-s=<session>` 参数实现多会话并行，预计总耗时 20-25秒
