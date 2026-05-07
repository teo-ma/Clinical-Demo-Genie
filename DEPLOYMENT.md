# Deployment Manifest — Azure Databricks Genie Demo

> 最近更新：2026-05-07
> 双层部署：**Databricks 端**（数据 + Genie Space）+ **Azure Container Apps 端**（Streamlit 前端公网访问）

---

## 🌐 公网访问地址

**https://genie-demo.politemushroom-324d037d.eastus2.azurecontainerapps.io** （匿名公开，无需登录）

---

## 1️⃣ Databricks 端

| 资源 | 标识 |
|------|------|
| Workspace URL | https://adb-7405609281670145.5.azuredatabricks.net |
| Workspace ID | `7405609281670145` |
| Region | eastus2 |
| Tier | Premium |
| Metastore | `metastore_azure_eastus2` |
| **SQL Warehouse** | `genie-demo-wh` (Serverless Pro 2X-Small) · ID = `282ad4ef9b70fab2` |
| **Catalog / Schema** | `genie_demo.clinical` |
| **表（10）** | trials(5), sites(20), investigators(60), drugs(6), patients(800), enrollments(800), visits(3845), adverse_events(1033), lab_results(21414), dosing(22187) |
| **Metric Views（3）** | `mv_enrollment`, `mv_safety`, `mv_dropout` |
| **Genie Space** | `Clinical Trials Insights` |
| **Service Principals（2）** | `Site Manager (CN)`：仅可见 APAC/中国站点 + 列脱敏<br>`Safety Reviewer`：全球数据 + 明文 |

资源直达：
- [SQL Warehouse 控制台](https://adb-7405609281670145.5.azuredatabricks.net/sql/warehouses/282ad4ef9b70fab2)
- [Catalog Explorer · genie_demo.clinical](https://adb-7405609281670145.5.azuredatabricks.net/explore/data/genie_demo/clinical)

### 创建步骤（如重新搭建）

1. 创建 Pro / Serverless SQL Warehouse
2. 在 SQL Editor 依次执行：
   - [sql/01_setup_uc.sql](sql/01_setup_uc.sql)
   - [data/03_generate_mock_data.py](data/03_generate_mock_data.py)（作为 Notebook 运行）
   - [sql/04_sample_queries.sql](sql/04_sample_queries.sql)
   - [sql/05_permissions_demo.sql](sql/05_permissions_demo.sql)（**注意**：先创建 SP 与组）
   - [sql/06_metric_views.sql](sql/06_metric_views.sql)
3. 按 [genie/setup_guide.md](genie/setup_guide.md) 创建 Genie Space，绑定 10 张表 + 3 个 Metric Views，粘贴 [genie/instructions.md](genie/instructions.md)
4. 给两个 Service Principal 在 Genie Space 上授予 `CAN RUN`，加到对应 group（`clinical_site_cn` / `clinical_safety_reviewer`）

---

## 2️⃣ Azure Container Apps 端（Streamlit 前端）

| 资源 | 值 |
|------|---|
| Subscription | `6e286c59-6eb0-4a8c-90e8-663ab5be468b` (MCAPS-Hybrid-REQ-103067-2024-tema) |
| Resource Group | `rg-databricks` |
| Region | eastus2 |
| ACR | `acrgeniedemo7f3f82.azurecr.io` (Basic, admin enabled) |
| 镜像 | `acrgeniedemo7f3f82.azurecr.io/genie-demo:<tag>` |
| ACA Environment | `cae-genie-demo` (Consumption profile) |
| Container App | `genie-demo` (1 vCPU / 2 GiB / 1-2 replicas) |
| Ingress | External, anonymous, 端口 8000 |
| FQDN | https://genie-demo.politemushroom-324d037d.eastus2.azurecontainerapps.io |

### 注入的环境变量

| 变量 | 用途 |
|------|------|
| `DATABRICKS_HOST` | Workspace URL |
| `GENIE_SPACE_ID` | 默认 Space ID |
| `GENIE_PERSONAS` | JSON 数组，每个元素含 `label / space_id / client_id / client_secret`，App 启动时换取 OAuth token |

### 一键部署

```zsh
./scripts/deploy_aca.sh
```

脚本是幂等的：首次执行创建全部资源，后续执行只更新镜像。

### 单独重新构建并发布镜像

```zsh
TAG=$(date +%Y%m%d%H%M)
az acr build -r acrgeniedemo7f3f82 -t genie-demo:$TAG -f app/Dockerfile app/
az containerapp update -n genie-demo -g rg-databricks \
  --image acrgeniedemo7f3f82.azurecr.io/genie-demo:$TAG
```

### 健康检查

```zsh
curl -sI https://genie-demo.politemushroom-324d037d.eastus2.azurecontainerapps.io | head -3
# 期望：HTTP/2 200
```

```zsh
az containerapp revision list -n genie-demo -g rg-databricks \
  --query "[].{name:name, active:properties.active, healthState:properties.healthState, replicas:properties.replicas}" -o table
```

### 查看日志

```zsh
az containerapp logs show -n genie-demo -g rg-databricks --tail 100 --follow
```

---

## 🔒 安全注意事项

当前为**演示态**，存在以下需在生产化时加固的点：

1. **OAuth Client Secret 明文写入 ACA 环境变量**
   - 生产应改用 ACA Secrets + Key Vault references
2. **匿名公开访问**
   - 生产应启用 Microsoft Entra Easy Auth，限制为指定租户/用户
3. **未启用自定义域名 + TLS 证书**
   - 生产建议绑定企业域名 + ACA Managed Cert
4. **Service Principal 权限范围**
   - 当前 SP 仅授予 `CAN RUN` Genie Space + Schema 级 SELECT；行级权限通过 Row Filter 落地，列级通过 Column Mask 落地

---

## 🧹 清理

```zsh
# 拆 ACA
az containerapp delete -n genie-demo -g rg-databricks --yes
az containerapp env delete -n cae-genie-demo -g rg-databricks --yes
az acr delete -n acrgeniedemo7f3f82 --yes

# 拆 Databricks
databricks warehouses delete 282ad4ef9b70fab2 \
  --host https://adb-7405609281670145.5.azuredatabricks.net
# 在 SQL editor 执行：DROP CATALOG genie_demo CASCADE;
# Genie Space 在 UI 中移到 Trash
```

> ⚠️ 演示结束后**务必吊销**两个 Service Principal 的 Client Secret。

---

## 🆘 排错

| 现象 | 检查 |
|------|------|
| App 打开后切换 persona 报 401 | OAuth secret 失效 → 重新生成并 `az containerapp update --set-env-vars` |
| 提问无响应 / 超时 | SQL Warehouse 是否冷启动；Genie Space 是否绑定了对应 SP 的 `CAN RUN` |
| Site Manager 看到全球数据 | 该 SP 是否被加入 `clinical_site_cn` 组；Row Filter 函数是否引用该组 |
| Metric View 命中率低 | 在 Genie Space → Sample Queries 里加几条 `MEASURE(mv_xxx.xxx)` 示例 |
| ACA 镜像更新后未生效 | `az containerapp revision list` 看是否新 revision Healthy；必要时 `--revision-suffix` 强制新 revision |
