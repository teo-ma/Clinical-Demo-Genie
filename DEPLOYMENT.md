# Deployment Result — Azure Databricks Genie Demo

> 自动化部署完成时间：2026-05-06
> 目标 Workspace：`workspace-databricks` (rg-databricks, eastus2, **Premium**)

## ✅ 已自动完成

| 资源 | 标识 |
|------|------|
| Workspace URL | https://adb-7405609281670145.5.azuredatabricks.net |
| Workspace ID | `7405609281670145` |
| Metastore | `metastore_azure_eastus2` (eastus2) |
| **SQL Warehouse** | `genie-demo-wh` (Serverless Pro 2X-Small)<br>**ID = `282ad4ef9b70fab2`** |
| **Catalog / Schema** | `genie_demo.clinical` |
| **表** (10) | trials(5), sites(20), investigators(60), drugs(6), patients(800), enrollments(800), visits(3845), adverse_events(1033), lab_results(21414), dosing(22187) |
| Workspace Notebooks | `/Users/tema@microsoft.com/genie-demo/` |

资源直达：
- [SQL Warehouse 控制台](https://adb-7405609281670145.5.azuredatabricks.net/sql/warehouses/282ad4ef9b70fab2)
- [Catalog Explorer · genie_demo.clinical](https://adb-7405609281670145.5.azuredatabricks.net/explore/data/genie_demo/clinical)
- [Workspace 文件夹](https://adb-7405609281670145.5.azuredatabricks.net/#workspace/Users/tema@microsoft.com/genie-demo)

## 🔜 接下来手动完成（仅 1 步必做）

### 创建 Genie Space（Genie Space 创建需序列化 payload，建议用 UI 完成）

1. 打开 https://adb-7405609281670145.5.azuredatabricks.net → 左侧导航 **Genie**
2. 右上角 **+ New** → **Genie space**
3. 填写：
   - Title: `Clinical Trials Insights`
   - SQL Warehouse: 选 **`genie-demo-wh`**
   - Tables: 展开 `genie_demo` → `clinical` → **全选 10 张表**
4. 创建后进入 **Settings**：
   - **Instructions** → 打开 [genie/instructions.md](genie/instructions.md)（也已上传到 Workspace `/Users/.../genie-demo/instructions`），整段粘贴 → Save
   - **Example SQL queries** → 打开 [sql/04_sample_queries.sql](sql/04_sample_queries.sql) 或 Workspace 中 `sample_queries` notebook → 把每段 `-- 提问：xxx` 配对 SQL 添加为示例（建议至少前 5 条）
5. 在 Genie 主对话框试问：**"当前在组的受试者总数？按试验分组列出。"**

记下创建后的 Space ID（URL 中 `genie/rooms/<UUID>` 那段），用于 Streamlit / API 演示。

## 🧪 验证 Genie API（可选）

打开 Workspace 中已上传的 Notebook：[`/Users/tema@microsoft.com/genie-demo/genie_api_demo`](https://adb-7405609281670145.5.azuredatabricks.net/#workspace/Users/tema@microsoft.com/genie-demo/genie_api_demo)

把第 16 行的 `SPACE_ID = "PASTE-YOUR-GENIE-SPACE-ID"` 替换成上一步拿到的 Space ID，Run All 即可。

## 🌐 启动 Streamlit 前端（可选）

```zsh
cd /Users/tema/projects/databricks-genie/app
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export DATABRICKS_HOST=https://adb-7405609281670145.5.azuredatabricks.net
# 用当前 az 登录态生成临时 Databricks AAD token
export DATABRICKS_TOKEN=$(az account get-access-token --resource 2ff814a6-3304-4ab8-85cb-cd0e6f879c1d --query accessToken -o tsv)
export GENIE_SPACE_ID=<paste-genie-space-id>

streamlit run streamlit_app.py
```

> 注：AAD token 默认 1 小时过期；演示长会话建议在 Workspace **Settings → Developer → Access tokens** 生成 PAT。

## 🎤 演示流程

按 [demo_script.md](demo_script.md) 的 6 题脚本走（含话术与"故意越界"演示）。

## 🧹 清理

```zsh
export DATABRICKS_HOST=https://adb-7405609281670145.5.azuredatabricks.net
databricks warehouses delete 282ad4ef9b70fab2
# 在 SQL editor 中：DROP CATALOG genie_demo CASCADE;
databricks workspace delete /Users/tema@microsoft.com/genie-demo --recursive
# 通过 Genie UI 把 space 移到 Trash
```
