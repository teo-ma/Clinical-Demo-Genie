# 🎤 Clinical Genie Demo —— 现场演示话术与脚本

> 时长：15–25 分钟。**最佳演示路径**：先 Genie Space 直问 → 再 Streamlit App 嵌入 → 再 Notebook 看代码集成。

---

## 0. 开场（1 分钟）

> "今天给大家演示 **Azure Databricks AI/BI Genie**：让业务用户、医学事务团队、PI 不用写一行 SQL，就能直接用中文向临床试验数据库提问，秒级拿到结果。这正是 Databricks 提的 **'Compound AI System on the Lakehouse'** 在生命科学行业的落地。
>
> 数据是我们模拟的临床试验数据集，包含 5 个试验、800 个受试者、20 个研究中心，覆盖入组、访视、不良事件、实验室、给药 10 张表。"

切到 Genie Space 主界面。

---

## 1. Genie Space 直问（8 分钟）—— 演示**自然语言→SQL→可视化**全自动

### 题 1：基础聚合
**问**："当前在组的受试者总数是多少？按试验分组列出。"

**看点**：
- Genie 自动识别"在组"= `withdrawal_date IS NULL`（这是 **Instructions** 教会它的术语）
- 点击 **Show generated SQL** —— 给 IT/数据团队看 SQL 的透明性

### 题 2：业务术语
**问**："Treatment 组和 Control 组的 SAE 发生率对比。"

**看点**：
- Genie 自动把 `Placebo` 与 `Control` 合并 —— 因为 Instructions 里这样定义了
- SAE 自动映射到 `is_serious = TRUE` —— 来自 Instructions 中的术语表
- **强调点**：业务定义的"单一事实来源"在 Instructions 里，所有人问同一个问题得到一致答案

### 题 3：排行榜
**问**："Top 10 入组数最多的研究中心。"

**看点**：
- Genie 默认 LIMIT 10 + 降序（来自 Instructions 的"默认排序约定"）
- 自动渲染条形图

### 题 4：时间趋势 + 多轮追问
**问**："各区域每月的入组人数趋势。"

→ 显示折线图后追问：
**问**："其中 APAC 区域为什么 4 月份下滑？"

**看点**：
- **Conversation 上下文** —— Genie 知道"APAC"指上一题的区域
- Genie 会承认"无法判断业务原因，但可以告诉你 APAC 4 月各站点入组数和退出数"——演示**诚实的边界感知**

### 题 5：故意越界（演示安全边界）
**问**："给我看一下患者 PT-00123 的姓名和家庭住址。"

**看点**：
- Genie 拒绝（Instructions 明确禁止 PII）
- 强调：**Genie 继承 Unity Catalog 的 RBAC + 行列级安全**，不是"另一个绕过权限的 LLM"

### 题 6：复杂 join（演示 Trusted Assets 价值）
**问**："肝功能异常的受试者数量按试验分组排序。"

**看点**：
- 涉及 `lab_results` ↔ `enrollments` ↔ `trials` 三表 join + 业务规则（"肝功能异常"= ALT/AST 超出参考范围）
- 这条复杂 join 之所以一次正确，是因为我们提前在 Sample Queries 里加了类似模板

---

## 2. Feature 切换演示（3 分钟）

回到 **Genie Space → Settings**，依次展示：

1. **Instructions** —— 打开 [genie/instructions.md](genie/instructions.md)，强调"业务术语在这里集中管理"
2. **Example SQL queries** —— 展示已添加的 Trusted Assets，强调**改进闭环**："用户给某个回答点踩 → 我们在这里加一条修正样例 → 下次更准"
3. **Data** —— 展开某张表，显示每列都有 COMMENT —— "**列级 metadata 是 Genie 准确率的根基**"
4. **Benchmarks**（如果租户已开启）—— 强调可量化评估

---

## 3. Streamlit / Databricks Apps 嵌入演示（4 分钟）

切换到 [app/streamlit_app.py](app/streamlit_app.py) 的运行实例。

> "刚才是 Databricks 内置的 Genie UI。但 Genie **本质是一个 API**，所以可以嵌入到客户自己的门户、CRM、医学事务系统。这是我用 200 行 Streamlit + Genie API 写的最终用户前端。"

输入同样的问题"Treatment 组和 Control 组的 SAE 发生率对比"：

**看点**：
- 同样的回答（**API 与 UI 行为一致**）
- 自动可视化为条形图
- 展开 "查看生成的 SQL" —— 给开发者看 API 返回的 metadata 完整可控
- 点击侧边栏 "新建会话" —— 演示 conversation_id 隔离

> "这意味着：把 Genie 嵌入医院的门户、临床运营仪表板、电子数据采集系统 (EDC)，让医生/CRA/项目经理在自己熟悉的系统里直接问数据。"

---

## 4. Notebook —— 给开发者看代码（3 分钟）

打开 [notebook/genie_api_demo.py](notebook/genie_api_demo.py)。

逐 cell 走一遍：

1. `start-conversation` POST 一个问题
2. 轮询 `messages/{id}` 直到 `COMPLETED`
3. 拉 `query-result` 拿到 SQL + 数据
4. 后续追问只需带上 `conversation_id`

> "API 完全 RESTful，可以从 .NET / Java / 任何语言调用，也可以挂在 LangChain / Semantic Kernel 的 Tool 调用链路里 —— 让多 Agent 系统能复用 Genie 的 Text-to-SQL 能力。"

---

## 5. 收尾（1 分钟）

| 客户角色 | 价值 |
|---------|------|
| 业务用户 / 医学事务 | 不写 SQL 就能拿到数据洞察，10 秒出结果 |
| 数据团队 | Instructions 是业务术语的"单一事实来源"，避免反复对口径 |
| 安全 / 合规 | 完全继承 Unity Catalog 权限、审计、Lineage |
| 开发者 | 一个 REST API 就能把 Text-to-SQL 嵌入任何系统 |
| 业务负责人 | 不依赖"BI 团队排期"，自助分析 = 快速决策 |

> "**Genie 不是 ChatGPT 接数据库** —— 它是构建在 Unity Catalog 治理之上、与你已有的 Lakehouse 数据资产、权限、Lineage 完全打通的企业级 AI/BI 接口。"

---

## ⚙️ 演示前检查清单

- [ ] SQL Warehouse 已运行（避免冷启动等 1 分钟）
- [ ] Genie Space 已配置 Instructions + ≥5 条 Sample Queries
- [ ] 已用上面 6 个问题预先跑过一遍（避免现场首次响应慢）
- [ ] Streamlit App 已启动，左侧已填好 Token 与 Space ID
- [ ] 浏览器登录的是**演示账号**（仅 SELECT 权限），方便顺带演示安全
- [ ] 网络通畅（Genie 依赖底层 LLM 推理）

## 🆘 常见现场翻车与应对

| 现象 | 原因 | 现场说辞 |
|------|------|---------|
| 第一题响应 30s+ | Warehouse 冷启动 | "我们用的是 Pro Warehouse，第一次唤醒需 30 秒；后续问题都是秒级" |
| 答案不对 | Instructions/Sample 不够 | 现场给 Genie 点踩，加一条 Sample Query，说："这就是 Genie 的迭代闭环" |
| API 401 | Token 过期 | 切回 Genie Space UI 演示 |
