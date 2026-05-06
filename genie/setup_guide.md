# Genie Space 创建与配置指南（UI 操作）

> 前置：已执行 `sql/01_setup_uc.sql`、`sql/02_create_tables.sql` 并运行 `data/03_generate_mock_data.py`，且当前用户对 `genie_demo.clinical` 有 SELECT 权限。

## 1. 进入 Genie

1. 在 Azure Databricks Workspace 左侧导航栏点击 **Genie**（如果没有，点击 **+ New** → **Genie space**）。
2. 顶部右侧 **New** → **Genie space**。

## 2. 基本信息

| 字段 | 填写 |
|------|------|
| Name | `Clinical Trials Insights` |
| Description | `生命科学临床试验数据 Genie Space — 受试者入组、不良事件、实验室与给药数据。` |
| SQL Warehouse | 选择一个 **Pro** 或 **Serverless** Warehouse（Classic 不支持） |

## 3. 选择数据

在 **Data** 步骤：

1. 选择 Catalog: `genie_demo`，Schema: `clinical`
2. 勾选全部 10 张表：
   - `trials`, `sites`, `investigators`, `patients`, `drugs`
   - `enrollments`, `visits`, `adverse_events`, `lab_results`, `dosing`
3. 保存。Genie 会自动读取每张表/列的 `COMMENT` 作为元数据 —— 这就是为什么我们的 DDL 给每列都写了中英文 COMMENT。

## 4. 粘贴 General Instructions

进入 Space → **Settings** → **Instructions** → **General instructions**，把 [instructions.md](instructions.md) 整段内容复制进去 → **Save**。

## 5. 添加 Sample Queries (Trusted Assets)

进入 **Settings** → **Example SQL queries** → **Add example**。
逐条把 [../sql/04_sample_queries.sql](../sql/04_sample_queries.sql) 中每段 `-- 提问：xxx` 注释当作"自然语言问题"，下面紧跟的 SQL 当作"对应查询"。建议至少添加前 5 条，演示效果即可大幅提升。

> 💡 提示：Sample Queries 不仅是"训练样本"，演示时还会显示在 Genie 主页作为"建议问题"，看起来很专业。

## 6. （可选）添加列级补充说明 / Synonym

进入 **Data** 标签 → 选中某个字段 → **Add description / synonym**：

| 表.列 | 中文同义词 |
|------|-----------|
| `enrollments.arm` | 治疗组、分组 |
| `adverse_events.is_serious` | SAE、严重不良事件 |
| `adverse_events.ctcae_grade` | CTCAE 等级、AE 严重程度等级 |
| `trials.phase` | 临床阶段、试验阶段 |
| `lab_results.is_abnormal` | 实验室异常、异常值 |

## 7. 测试

在 Genie 对话框中输入：
- **"目前在组的受试者总数？"** → 应返回 `enrollments` 中 `withdrawal_date IS NULL` 的行数
- **"Treatment 组和 Control 组的 SAE 发生率对比？"** → 应自动合并 `Placebo` 与 `Control`

如果回答错了，点击 **Show generated SQL** → **Provide feedback** → 添加修正后的 SQL 进 Sample Queries。**这是 Genie 的核心改进闭环**。

## 8. 分享 / 权限

**Share** → 添加用户/组（仅有 `genie_demo.clinical` SELECT 权限的用户能正常使用）。
对于演示场景：
- 给客户演示账号一个**只读**用户，加入到 `account users` 组并 `GRANT SELECT ON SCHEMA genie_demo.clinical`。
- Genie 会**继承底层 UC 权限** —— 列级 / 行级安全策略自动生效。

## 9. （可选）Publish / 嵌入

- 从 Genie Space 右上角 **Share** → **Embed** 获取 iframe 代码或 Space ID。
- Space ID 形如 `01ef...` —— 复制后用于 Notebook / Streamlit Demo。
