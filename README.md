# Azure Databricks Genie Demo —— 生命科学 / 临床试验场景

一个端到端的 Azure Databricks AI/BI **Genie** 演示项目，主题为 **临床试验数据洞察 (Clinical Trials Insights)**。覆盖：

- ✅ Unity Catalog + Schema + SQL Warehouse 一键配置
- ✅ 临床试验维度建模（受试者 / 试验 / 站点 / 访视 / 不良事件 / 实验室结果 / 用药）
- ✅ Mock 数据生成脚本（PySpark）
- ✅ Genie Space 配置指南（Instructions、Sample Queries / Trusted Assets）
- ✅ Notebook：Genie Conversation API 调用全流程
- ✅ Streamlit Web 前端：自然语言问答 + 图表
- ✅ Databricks Apps 托管部署清单
- ✅ 中文演示话术 / 问题脚本

> 适用于向客户演示"业务用户用自然语言获取数据洞察"，以及给开发者展示 Genie 的代码集成能力。

---

## 📁 目录结构

```
databricks-genie/
├── README.md                       # 本文件
├── demo_script.md                  # 现场演示话术 + 问题清单
├── sql/
│   ├── 01_setup_uc.sql             # 创建 Catalog / Schema
│   ├── 02_create_tables.sql        # 临床数据模型 DDL
│   └── 04_sample_queries.sql       # 给 Genie 使用的示例 SQL（Trusted Assets）
├── data/
│   └── 03_generate_mock_data.py    # PySpark mock 数据生成（在 Databricks Notebook 中运行）
├── genie/
│   ├── instructions.md             # Genie Space 业务指令（直接复制粘贴）
│   └── setup_guide.md              # 创建 Genie Space 的 UI 操作步骤
├── notebook/
│   └── genie_api_demo.py           # Databricks Notebook：API 调用演示
└── app/
    ├── streamlit_app.py            # 自定义前端
    ├── requirements.txt
    └── app.yaml                    # Databricks Apps 配置
```

## 🚀 快速开始

| 步骤 | 操作 | 文件 |
|------|------|------|
| 1 | 在 Databricks 创建 Pro 或 Serverless **SQL Warehouse**（必需，Genie 依赖） | — |
| 2 | 在 Workspace 启用 **Unity Catalog**（如未启用） | — |
| 3 | 在 SQL Editor 中执行建库建表 | [sql/01_setup_uc.sql](sql/01_setup_uc.sql), [sql/02_create_tables.sql](sql/02_create_tables.sql) |
| 4 | 上传 [data/03_generate_mock_data.py](data/03_generate_mock_data.py) 为 Notebook 并运行 | — |
| 5 | 按 [genie/setup_guide.md](genie/setup_guide.md) 创建 Genie Space，绑定表，粘贴 Instructions 与 Sample Queries | — |
| 6 | （可选）运行 [notebook/genie_api_demo.py](notebook/genie_api_demo.py) 演示 API | — |
| 7 | （可选）按 [app/](app/) 部署 Streamlit / Databricks App | — |
| 8 | 跟随 [demo_script.md](demo_script.md) 现场演示 | — |

## 🎯 演示亮点（Genie Feature Map）

| 功能 | 演示位置 |
|------|----------|
| 自然语言 → SQL 自动生成 | Genie Space 直接对话 |
| Instructions（业务术语 / KPI 定义） | [genie/instructions.md](genie/instructions.md) |
| Sample Queries / Trusted Assets | [sql/04_sample_queries.sql](sql/04_sample_queries.sql) |
| Follow-up 多轮追问 | demo_script 第 4-5 题 |
| SQL 透明化（点击查看生成的 SQL） | Genie UI 内 |
| Conversation API 后端集成 | [notebook/genie_api_demo.py](notebook/genie_api_demo.py) |
| 嵌入到自定义应用 | [app/streamlit_app.py](app/streamlit_app.py) |
| 数据安全（UC + RBAC + 行列级权限） | UC 层面，无需额外配置 |

## ⚠️ 前置要求

- Azure Databricks **Premium** Workspace（Genie 仅 Premium 可用）
- 已启用 **Unity Catalog**
- 已创建 **Pro / Serverless SQL Warehouse**（Classic 不支持 Genie）
- 当前用户在目标 Catalog 拥有 `USE CATALOG` + `CREATE SCHEMA` 权限
- （API/App）需要一个 Personal Access Token 或 Service Principal
