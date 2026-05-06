-- ============================================================
-- 01_setup_uc.sql
-- 在 Unity Catalog 中创建用于 Genie Demo 的 Catalog / Schema
-- 在 Databricks SQL Editor 中执行（选择一个 Pro/Serverless SQL Warehouse）
-- ============================================================

-- 如果你的 Workspace 还没启用 UC，请先在 Account Console 完成 Metastore 绑定。
-- 此脚本默认使用一个名为 `genie_demo` 的 Catalog。如已存在可跳过 CREATE。

CREATE CATALOG IF NOT EXISTS genie_demo
  COMMENT 'Azure Databricks Genie Demo - Life Sciences / Clinical Trials';

USE CATALOG genie_demo;

CREATE SCHEMA IF NOT EXISTS clinical
  COMMENT '临床试验维度建模 schema';

USE SCHEMA clinical;

-- 授权（按需调整为你的用户/组）
-- GRANT USE CATALOG ON CATALOG genie_demo TO `account users`;
-- GRANT USE SCHEMA, SELECT ON SCHEMA genie_demo.clinical TO `account users`;

SELECT current_catalog() AS catalog, current_schema() AS schema;
