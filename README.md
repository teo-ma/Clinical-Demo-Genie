# Azure Databricks Genie Demo —— 临床试验数据洞察

一个端到端的 **Azure Databricks AI/BI Genie** 演示项目，主题为 **临床试验数据洞察 (Clinical Trials Insights)**，已部署到 Azure Container Apps，体验者无需 Databricks 账号即可访问。

> 🌐 **公网体验地址（匿名访问）**：
> **https://genie-demo.politemushroom-324d037d.eastus2.azurecontainerapps.io**

---

## 🎯 本 Demo 体现的 Genie 核心特性

| # | 特性 | 体现方式 |
|---|------|---------|
| 1 | **自然语言 → SQL** | Streamlit 聊天框中文提问，后端调用 Genie Conversation API 返回生成的 SQL 与结果 |
| 2 | **Instructions（业务术语 / KPI 定义）** | [genie/instructions.md](genie/instructions.md)：把"在组""SAE""肝功能异常"等业务术语沉淀为单一事实来源 |
| 3 | **Sample Queries / Trusted Assets** | [sql/04_sample_queries.sql](sql/04_sample_queries.sql)：预置示例 SQL，提升复杂 JOIN 的准确率 |
| 4 | **多轮追问 / Conversation 上下文** | App 维护 `conversation_id`，可基于上一题继续追问 |
| 5 | **SQL 透明化** | 每次回答下方折叠面板可展开"查看生成的 SQL" |
| 6 | **Unity Catalog 行级权限（Row Filter）** | [sql/05_permissions_demo.sql](sql/05_permissions_demo.sql)：`Site Manager (CN)` 仅可见中国站点；`Safety Reviewer` 看到全球数据 |
| 7 | **Unity Catalog 列级脱敏（Column Mask）** | 同一文件：受试者 BMI / 是否吸烟 / 合并症对 Site Manager 脱敏，对 Safety Reviewer 明文 |
| 8 | **UC Metric Views（指标视图）** | [sql/06_metric_views.sql](sql/06_metric_views.sql)：3 个指标视图 `mv_safety` / `mv_enrollment` / `mv_dropout`，把 `sae_rate`、`dropout_rate` 等公式锁定在 UC，Genie 通过 `MEASURE()` 调用，确保口径一致 |
| 9 | **Persona 切换 / OAuth M2M** | App 顶部下拉切换两个 Service Principal 身份，同一问题不同身份返回不同结果，演示 Genie 完整继承 UC 治理 |
| 10 | **可视化建议** | App 内 Plotly 11 种图表自动选择（柱 / 折 / 饼 / 箱线 / 散点 / 热力 等），数字标签精度自适应 |
| 11 | **API 嵌入** | App 通过 REST API 调用 Genie，证明可嵌入门户 / CRM / EDC 等任意业务系统 |

---

## 📁 目录结构

```
databricks-genie/
├── README.md                        # 本文件
├── DEPLOYMENT.md                    # 部署清单（Databricks + ACA）
├── demo_script.md                   # 现场演示话术与脚本
├── databricks.yml                   # Databricks Asset Bundle 配置
├── sql/
│   ├── 01_setup_uc.sql              # 创建 Catalog / Schema
│   ├── 04_sample_queries.sql        # Genie Trusted Assets 示例
│   ├── 05_permissions_demo.sql      # 行级权限 + 列级脱敏（Persona 演示用）
│   └── 06_metric_views.sql          # UC Metric Views（3 个指标视图）
├── data/
│   └── 03_generate_mock_data.py     # PySpark mock 数据生成
├── genie/
│   ├── instructions.md              # Genie Space Instructions
│   └── setup_guide.md               # Genie Space UI 配置步骤
├── notebook/
│   └── genie_api_demo.py            # Genie Conversation API 调用示例
├── app/
│   ├── streamlit_app.py             # 自定义前端（多 Persona + Plotly）
│   ├── requirements.txt
│   ├── Dockerfile                   # ACA 容器镜像
│   ├── .dockerignore
│   └── app.yaml                     # Databricks Apps 配置（备选部署）
└── scripts/
    ├── deploy_aca.sh                # 一键部署到 Azure Container Apps
    ├── ask_genie.sh                 # 命令行调用示例
    └── run_sql.py
```

---

## 🚀 快速体验

### 方式 A：直接访问公网 URL（推荐给业务体验者）

打开 **https://genie-demo.politemushroom-324d037d.eastus2.azurecontainerapps.io**，无需登录。

体验路径：
1. 顶部 **身份切换** —— 在 `Site Manager (CN)` 与 `Safety Reviewer` 之间切换
2. 左侧侧边栏分为三组样例问题（点击直接发送）：
   - 🔐 **行级权限 / 列级脱敏**：切换身份后再问，对比差异
   - 📊 **指标视图（Metric Views）**：直接命中 `mv_safety` / `mv_enrollment` / `mv_dropout`
   - 💬 **自然语言基础能力**：Text-to-SQL、跨表 JOIN、多轮追问
3. 每个回答下方可展开"查看生成的 SQL"

### 方式 B：本地运行（开发者）

```zsh
cd app
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export DATABRICKS_HOST=https://adb-7405609281670145.5.azuredatabricks.net
export GENIE_SPACE_ID=<paste-your-space-id>
export GENIE_PERSONAS='[{"label":"...","space_id":"...","token":"..."}]'

streamlit run streamlit_app.py
```

### 方式 C：在自己的 Azure 订阅中重新部署到 ACA

参见 [DEPLOYMENT.md](DEPLOYMENT.md) 中"Azure Container Apps 部署"章节，或直接执行：

```zsh
./scripts/deploy_aca.sh
```

---

## ⚠️ 前置要求（如需自建）

- Azure Databricks **Premium** Workspace（Genie 仅 Premium 可用）
- 已启用 **Unity Catalog**
- 已创建 **Pro / Serverless SQL Warehouse**（Classic 不支持 Genie）
- Catalog 上 `USE CATALOG` + `CREATE SCHEMA` 权限
- 至少一个 **Service Principal** + OAuth M2M 凭据，用于 App 调用 Genie API

完整搭建步骤见 [DEPLOYMENT.md](DEPLOYMENT.md)。

---

## 📐 数据模型

10 张 Unity Catalog 表（`genie_demo.clinical`），按"维度（Dimension）+ 事实（Fact）"分层。所有表与列均带 `COMMENT`，Genie 自动读取作为元数据，是其高准确率的关键。

### 维度表（Dimension）—— "谁、在哪、用什么"

#### 🧪 `trials`（临床试验主数据） · 5 行
**业务含义**：每行 = 一项临床试验。是整个数据集的"试验维度根"，所有 enrollment 都归属到一个 trial。
**关键字段**：
- `trial_id` (PK)、`protocol_code`、`trial_name`
- `therapeutic_area`：治疗领域（Oncology / Cardiology / Neurology / Immunology / Rare Disease）
- `indication`：适应症（NSCLC / Breast Cancer / Heart Failure …）
- `phase`：试验阶段（Phase I-IV）
- `status`：Recruiting / Active / Completed / Terminated
- `start_date / end_date / target_enrollment / sponsor`

#### 🏥 `sites`（研究中心 / 站点） · 20 行
**业务含义**：执行试验的物理地点（医院、临床研究中心）。**行级权限的承载维度**：Site Manager (CN) 通过 `country = 'China'` 过滤可见行。
**关键字段**：`site_id` (PK)、`site_name`、`country`、`region`（APAC / EMEA / NA / LATAM）、`city`、`activation_date`

#### 👨‍⚕️ `investigators`（研究者） · 60 行
**业务含义**：站点上的医生/研究人员。每个站点配多名 PI 与 Sub-I。
**关键字段**：`investigator_id` (PK)、`full_name`、`site_id` (FK→sites)、`role`（Principal Investigator / Sub-Investigator / Coordinator）

#### 💊 `drugs`（研究药物字典） · 6 行
**业务含义**：试验中使用的药物或安慰剂。`is_placebo=TRUE` 用于区分 Treatment vs Control 组。
**关键字段**：`drug_id` (PK)、`drug_name`、`drug_class`、`is_placebo`

#### 🧑‍🤝‍🧑 `patients`（受试者去标识化档案） · 800 行
**业务含义**：参加试验的受试者人口学信息。已去标识（无姓名、住址）。**列级脱敏的承载维度**：`bmi / smoker / comorbidities` 对受限身份返回 NULL/`***`。
**关键字段**：`patient_id` (PK)、`age`、`sex`、`ethnicity`、`bmi`、`smoker`、`comorbidities`、`enrollment_date`

### 事实表（Fact）—— "发生了什么"

#### 📋 `enrollments`（入组事实表） · 800 行 · **核心枢纽**
**业务含义**：连接 patient × trial × site × investigator × drug × arm 的中心事实表。所有访视、AE、化验、给药都通过 `enrollment_id` 关联回来。
**关键字段**：
- `enrollment_id` (PK)、`patient_id` (FK)、`trial_id` (FK)、`site_id` (FK)、`investigator_id` (FK)、`drug_id` (FK)
- `arm`：**治疗组**（Treatment / Control / Placebo）—— SAE 发生率对比的核心维度
- `enrollment_date`：入组日期（用于按月趋势分析）
- `withdrawal_date`：**退出日期**（NULL 表示"在组"）—— "活跃受试者"的判定字段
- `withdrawal_reason`：Adverse Event / Lack of Efficacy / Patient Decision / Lost to Follow-up / Completed

#### 📅 `visits`（访视记录） · 3,845 行
**业务含义**：受试者按方案规定的访问医院的每次记录。一个 enrollment 通常有 5-10 次 visits（Screening → Baseline → Treatment ×N → Follow-up → End of Study）。
**关键字段**：`visit_id` (PK)、`enrollment_id` (FK)、`visit_number`、`visit_type`、`visit_date`、`is_completed`

#### ⚠️ `adverse_events`（不良事件 / AE & SAE） · 1,033 行
**业务含义**：受试者在试验期间发生的任何身体不良反应。**安全性分析的核心**。`is_serious=TRUE` 即 SAE（Serious Adverse Event），需立即上报监管。
**关键字段**：
- `ae_id` (PK)、`enrollment_id` (FK)
- `event_term`：MedDRA 术语（Headache, Nausea, Neutropenia …）
- `system_organ_class`：SOC 系统器官分类
- `severity`：Mild / Moderate / Severe
- `ctcae_grade`：1-5 等级，越高越严重
- `is_serious`：是否为 **SAE**
- `related_to_drug`：与药物相关性（Unrelated / Possible / Probable / Definite）
- `onset_date / resolved_date / outcome`（Recovered / Fatal …）

#### 🧪 `lab_results`（实验室检验） · 21,414 行 · 最大表
**业务含义**：访视中采集的血液/生化检验值。**疗效与安全性双重指标**：肝功能（ALT/AST）异常预示药物肝毒性；血液学（WBC/Hgb）异常预示骨髓抑制。
**关键字段**：
- `lab_id` (PK)、`enrollment_id` (FK)、`visit_id` (FK)
- `test_name`：检验项目（ALT / AST / Hemoglobin / Creatinine / WBC / Glucose）
- `test_value`、`unit`
- `reference_low / reference_high`：参考范围
- `is_abnormal`：是否超出参考范围（**"肝功能异常" = test_name in ('ALT','AST') AND is_abnormal=TRUE**，已写入 Instructions）
- `collected_date`

#### 💉 `dosing`（给药记录） · 22,187 行
**业务含义**：每次实际给药的剂量与日期。`is_skipped=TRUE` 表示漏服，是依从性 (compliance) 分析的来源。
**关键字段**：`dose_id` (PK)、`enrollment_id` (FK)、`drug_id` (FK)、`dose_amount_mg`、`dose_date`、`is_skipped`

### 实体关系图（ER）

```
              ┌──────────┐
              │  trials  │ 5
              └────┬─────┘
                   │ trial_id
                   ▼
┌──────────┐  ┌────────────────┐  ┌──────────┐  ┌──────────┐
│ patients │──│  enrollments   │──│  sites   │  │  drugs   │
│   800    │  │  (中心事实)     │  │   20     │  │    6     │
└──────────┘  │      800       │  └────┬─────┘  └──────────┘
              └────┬───────────┘       │ site_id
                   │ enrollment_id     ▼
        ┌──────────┼──────────┬──────────┐  ┌────────────────┐
        ▼          ▼          ▼          ▼  │ investigators  │
   ┌────────┐ ┌─────────┐ ┌──────────┐ ┌────────┐  60
   │ visits │ │   AE    │ │   labs   │ │ dosing │
   │ 3,845  │ │  1,033  │ │  21,414  │ │ 22,187 │
   └────────┘ └─────────┘ └──────────┘ └────────┘
```

### 3 个 UC Metric Views（指标视图）

把核心业务公式锁定在 UC 中，Genie 通过 `MEASURE()` 调用，确保口径一致：

| 视图 | 来源 | 维度 | 关键度量 | 业务含义 |
|------|------|------|---------|----------|
| `mv_enrollment` | enrollments + sites + trials | trial / region / country / site / month | `enrolled_count`, `withdrawn_count`, `active_count` | 入组进度（含按月趋势 + 区域切片） |
| `mv_safety` | adverse_events + enrollments | trial / arm / severity | `ae_count`, `serious_ae_count`, `sae_rate` | SAE 发生率 = SAE 数 / 入组数 |
| `mv_dropout` | enrollments | trial / region | `withdrawn_count`, `enrolled_count`, `dropout_rate` | 退出率 = 已退出数 / 入组数 |

> 这些公式一次审核、永久锁定，Genie 调用时不会"现编"算法。

---

## 🎤 演示流程

按 [demo_script.md](demo_script.md) 走脚本（约 15-25 分钟），覆盖：自然语言→SQL → 业务术语 → 多轮追问 → 行级权限 → 列级脱敏 → Metric Views。

---

## 🧹 清理

```zsh
# 删除 Container App + ACA env + ACR
az containerapp delete -n genie-demo -g rg-databricks --yes
az containerapp env delete -n cae-genie-demo -g rg-databricks --yes
az acr delete -n acrgeniedemo7f3f82 --yes

# 删除 Databricks 侧资源
databricks warehouses delete 282ad4ef9b70fab2
# 在 SQL editor: DROP CATALOG genie_demo CASCADE;
```

> ⚠️ **演示结束后请吊销** App 中嵌入的 Service Principal 凭据（明文写入 ACA 环境变量）。
