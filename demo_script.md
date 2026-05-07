# 🎤 Clinical Genie Demo —— 现场演示话术与脚本

> 时长：15–25 分钟。
>
> **公网体验地址**（无需登录）：
> **https://genie-demo.politemushroom-324d037d.eastus2.azurecontainerapps.io**
>
> **最佳演示路径**：先在 ACA 上的 Streamlit App 跑「Persona 切换 + 行级权限 + 列级脱敏 + Metric Views」 → 再切回 Databricks Genie Space UI 看 Instructions/Trusted Assets → 最后给开发者看 Notebook 中的 API 集成。

---

## 0. 开场（1 分钟）

> "今天给大家演示 **Azure Databricks AI/BI Genie**：让业务用户、医学事务团队、PI 不用写一行 SQL，就能直接用中文向临床试验数据库提问，秒级拿到结果。这正是 Databricks 提的 **'Compound AI System on the Lakehouse'** 在生命科学行业的落地。
>
> 数据是我们模拟的临床试验数据集，包含 5 个试验、800 个受试者、20 个研究中心，覆盖入组、访视、不良事件、实验室、给药 10 张表。"

切到 Genie Space 主界面。

---

## 1. Streamlit App 演示（10 分钟）—— Persona × 行级权限 × 列脱敏 × Metric Views

打开 https://genie-demo.politemushroom-324d037d.eastus2.azurecontainerapps.io ，左侧侧边栏分三组样例问题。

### A. 行级权限 / 列级脱敏对比（4 分钟）

保持身份为 **Safety Reviewer**：

- 点击 "列出所有研究站点和它们所在国家" → 看到全球 20 个站点（含美国、欧洲、亚洲）
- 点击 "显示前 5 名受试者的合并症、BMI、是否吸烟" → BMI / 合并症 / 是否吸烟 全部明文

切换到 **Site Manager (CN)**，点击同样两个问题：

- 站点列表：**只剩中国 4 个站点** ← Row Filter 起作用
- 受试者列表：BMI 显示为 `NULL` / 合并症显示为 `***` / 是否吸烟显示为 `***` ← Column Mask 起作用

**话术**：
> "看到了吗？同一个 Genie Space、同一个问题，**两个身份返回结果完全不同**。这不是 App 层的过滤——是 **Unity Catalog 把 Row Filter 和 Column Mask 钉在表上**，无论你从 Genie 问、从 SQL Editor 查、还是从 Power BI 连，结果都一样。这就是 Genie 继承企业级数据治理的真正含义。"

点击下方 "查看生成的 SQL"：SQL 看起来一样，但 UC 在执行时透明地附加了过滤与脱敏。

### B. Metric Views（指标视图）（3 分钟）

切回 **Safety Reviewer**：

- 点击 "按治疗组对比 SAE 发生率"
- 点击 "各试验的受试者退出率排名"
- 点击 "各区域每月的入组人数趋势"

展开生成的 SQL，给观众看核心是 `MEASURE(mv_safety.sae_rate)` 这种调用。

**话术**：
> "`sae_rate`、`dropout_rate` 这些公式我们**没让 Genie 现编**——它们是数据团队预先在 UC 里定义好的 Metric View，公式一次审核、永久锁定。Genie 只需要决定『从哪个维度切片』，公式本身不会算错。这就是 **AI/BI 的指标治理**：业务用户随便问，但口径绝不会被随便改。"

切回 **Site Manager (CN)** 再点 "各区域每月的入组人数趋势"：

- 只剩 APAC 一行 ← **Metric View 也继承了底表的 Row Filter**

### C. 自然语言基础能力（3 分钟）

点击 "当前在组的受试者总数？按试验分组列出。"：

- Genie 自动识别"在组" = `withdrawal_date IS NULL` ← 来自 Instructions 的术语表
- 展开 SQL 验证

点击 "肝功能异常受试者数量按试验分组排序"：

- 跨 `lab_results` / `enrollments` / `trials` 三表 JOIN
- 之所以一次正确，是因为 [sql/04_sample_queries.sql](sql/04_sample_queries.sql) 里有类似模板（Trusted Assets）

**追问演示多轮上下文**——在聊天框继续输入：
> "其中入组最多的那个试验，最常见的不良事件是什么？"

App 会带上 `conversation_id`，Genie 知道"那个试验"指上一题排名第一的 trial。

---

## 2. 切回 Databricks Genie Space（4 分钟）

回到 **Genie Space → Settings**，依次展示：

1. **Instructions** —— 打开 [genie/instructions.md](genie/instructions.md)，强调"业务术语在这里集中管理"
2. **Example SQL queries** —— 展示已添加的 Trusted Assets，强调**改进闭环**："用户给某个回答点踩 → 我们在这里加一条修正样例 → 下次更准"
3. **Data** —— 展开某张表，显示每列都有 COMMENT —— "**列级 metadata 是 Genie 准确率的根基**"
4. **Benchmarks**（如果租户已开启）—— 强调可量化评估

---

## 3. Notebook —— 给开发者看代码（3 分钟）

打开 [notebook/genie_api_demo.py](notebook/genie_api_demo.py)。

逐 cell 走一遍：

1. `start-conversation` POST 一个问题
2. 轮询 `messages/{id}` 直到 `COMPLETED`
3. 拉 `query-result` 拿到 SQL + 数据
4. 后续追问只需带上 `conversation_id`

> "API 完全 RESTful，可以从 .NET / Java / 任何语言调用，也可以挂在 LangChain / Semantic Kernel 的 Tool 调用链路里 —— 让多 Agent 系统能复用 Genie 的 Text-to-SQL 能力。"

---

## 4. 收尾（1 分钟）

| 客户角色 | 价值 |
|---------|------|
| 业务用户 / 医学事务 | 不写 SQL 就能拿到数据洞察，10 秒出结果 |
| 数据团队 | Instructions = 业务术语单一事实来源；Metric View = 公式锁定 |
| 安全 / 合规 | Row Filter / Column Mask 在 UC 落地，Genie 自动继承，无需 App 层兜底 |
| 开发者 | 一个 REST API 就能把 Text-to-SQL 嵌入任何系统（已部署 ACA 公网 demo） |
| 业务负责人 | 不依赖"BI 团队排期"，自助分析 = 快速决策 |

> "**Genie 不是 ChatGPT 接数据库** —— 它是构建在 Unity Catalog 治理之上、与你已有的 Lakehouse 数据资产、权限、Lineage、指标定义完全打通的企业级 AI/BI 接口。"

---

## ⚙️ 演示前检查清单

- [ ] 公网 URL 可访问（`curl -sI https://genie-demo.politemushroom-324d037d.eastus2.azurecontainerapps.io | head -1` 返回 `HTTP/2 200`）
- [ ] SQL Warehouse 已运行（避免冷启动等 1 分钟）
- [ ] Genie Space 已配置 Instructions + ≥5 条 Sample Queries + 3 个 Metric Views 已绑定
- [ ] 两个 Service Principal 都已加入对应 group，Row Filter / Column Mask 已生效（用 SP 在 SQL Editor 跑一遍 `SELECT * FROM clinical.sites` 验证）
- [ ] 已用样例问题预先跑过一遍（避免现场首次响应慢）
- [ ] 网络通畅

## 🆘 常见现场翻车与应对

| 现象 | 原因 | 现场说辞 |
|------|------|---------|
| 第一题响应 30s+ | Warehouse 冷启动 | "我们用的是 Pro Warehouse，第一次唤醒需 30 秒；后续问题都是秒级" |
| 答案不对 | Instructions/Sample 不够 | 现场给 Genie 点踩，加一条 Sample Query，说："这就是 Genie 的迭代闭环" |
| API 401 | Token 过期 | 切回 Genie Space UI 演示 |
