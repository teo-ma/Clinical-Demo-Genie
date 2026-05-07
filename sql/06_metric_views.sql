-- ============================================================
-- 06_metric_views.sql
-- Unity Catalog Metric Views（指标视图）
--
-- 核心概念：把"业务指标定义"做成 UC 一等公民对象。
--   * source:     底层事实表 + 必要的 JOIN
--   * dimensions: 可被 GROUP BY 的字段
--   * measures:   聚合表达式（公式锁定，所有人查一致）
--
-- 在 Genie Space 里把这些 Metric View 加为数据源后，
-- Genie 看到指标问句会直接调用 MEASURE(...)，而不是让 LLM 现写公式。
-- ============================================================

-- 注意：本脚本通过 scripts/run_sql.py 执行；运行器会按 `;` 切分语句。
-- YAML 体内的 SQL 不要写分号；不要写 `--` 风格注释（会被预处理移除）。

USE CATALOG genie_demo;
USE SCHEMA clinical;

-- ============================================================
-- ① mv_enrollment：入组进度指标
--    回答：进了多少人？退了多少人？目标完成率？按试验/区域/月份切片
-- ============================================================
CREATE OR REPLACE VIEW genie_demo.clinical.mv_enrollment
WITH METRICS
LANGUAGE YAML
COMMENT '入组进度指标视图：入组数、退出数、目标完成率，可按试验/治疗领域/区域/月份切片'
AS $$
version: 0.1

source: |-
  SELECT
    e.enrollment_id,
    e.patient_id,
    e.arm,
    e.enrollment_date,
    e.withdrawal_date,
    e.withdrawal_reason,
    t.trial_id,
    t.trial_name,
    t.therapeutic_area,
    t.phase,
    t.status AS trial_status,
    t.target_enrollment,
    s.site_id,
    s.site_name,
    s.country,
    s.region
  FROM genie_demo.clinical.enrollments e
  JOIN genie_demo.clinical.trials t ON e.trial_id = t.trial_id
  JOIN genie_demo.clinical.sites s  ON e.site_id  = s.site_id

dimensions:
  - name: trial_id
    expr: trial_id
  - name: trial_name
    expr: trial_name
  - name: therapeutic_area
    expr: therapeutic_area
  - name: phase
    expr: phase
  - name: trial_status
    expr: trial_status
  - name: arm
    expr: arm
  - name: country
    expr: country
  - name: region
    expr: region
  - name: site_id
    expr: site_id
  - name: enrollment_month
    expr: DATE_TRUNC('MONTH', enrollment_date)

measures:
  - name: enrolled_count
    expr: COUNT(DISTINCT enrollment_id)
  - name: withdrawn_count
    expr: COUNT(DISTINCT CASE WHEN withdrawal_date IS NOT NULL THEN enrollment_id END)
  - name: active_count
    expr: COUNT(DISTINCT CASE WHEN withdrawal_date IS NULL THEN enrollment_id END)
$$
;

-- ============================================================
-- ② mv_safety：安全性指标
--    回答：AE/SAE 发生率、按治疗组/系统器官分类切片
-- ============================================================
CREATE OR REPLACE VIEW genie_demo.clinical.mv_safety
WITH METRICS
LANGUAGE YAML
COMMENT '安全性指标视图：AE 总数、SAE 数、SAE 发生率、致死事件数，可按试验/治疗组/SOC/区域/月份切片'
AS $$
version: 0.1

source: |-
  SELECT
    ae.ae_id,
    ae.event_term,
    ae.system_organ_class,
    ae.severity,
    ae.ctcae_grade,
    ae.is_serious,
    ae.related_to_drug,
    ae.outcome,
    ae.onset_date,
    e.enrollment_id,
    e.arm,
    t.trial_id,
    t.therapeutic_area,
    t.phase,
    s.country,
    s.region
  FROM genie_demo.clinical.adverse_events ae
  JOIN genie_demo.clinical.enrollments e ON ae.enrollment_id = e.enrollment_id
  JOIN genie_demo.clinical.trials t      ON e.trial_id = t.trial_id
  JOIN genie_demo.clinical.sites  s      ON e.site_id  = s.site_id

dimensions:
  - name: trial_id
    expr: trial_id
  - name: therapeutic_area
    expr: therapeutic_area
  - name: phase
    expr: phase
  - name: arm
    expr: arm
  - name: system_organ_class
    expr: system_organ_class
  - name: severity
    expr: severity
  - name: ctcae_grade
    expr: ctcae_grade
  - name: country
    expr: country
  - name: region
    expr: region
  - name: onset_month
    expr: DATE_TRUNC('MONTH', onset_date)

measures:
  - name: ae_total
    expr: COUNT(*)
  - name: sae_count
    expr: SUM(CASE WHEN is_serious THEN 1 ELSE 0 END)
  - name: fatal_count
    expr: SUM(CASE WHEN ctcae_grade = 5 THEN 1 ELSE 0 END)
  - name: drug_related_count
    expr: SUM(CASE WHEN related_to_drug IN ('Probable','Definite') THEN 1 ELSE 0 END)
  - name: patients_with_ae
    expr: COUNT(DISTINCT enrollment_id)
  - name: patients_with_sae
    expr: COUNT(DISTINCT CASE WHEN is_serious THEN enrollment_id END)
  - name: sae_rate
    expr: SUM(CASE WHEN is_serious THEN 1 ELSE 0 END) * 1.0 / COUNT(DISTINCT enrollment_id)
$$
;

-- ============================================================
-- ③ mv_dropout：受试者退出/留存指标
--    回答：退出率、各退出原因构成、按试验/治疗组/区域切片
-- ============================================================
CREATE OR REPLACE VIEW genie_demo.clinical.mv_dropout
WITH METRICS
LANGUAGE YAML
COMMENT '受试者退出/留存指标视图：退出率、不同退出原因构成，可按试验/治疗组/区域切片'
AS $$
version: 0.1

source: |-
  SELECT
    e.enrollment_id,
    e.arm,
    e.enrollment_date,
    e.withdrawal_date,
    e.withdrawal_reason,
    t.trial_id,
    t.therapeutic_area,
    t.phase,
    s.country,
    s.region
  FROM genie_demo.clinical.enrollments e
  JOIN genie_demo.clinical.trials t ON e.trial_id = t.trial_id
  JOIN genie_demo.clinical.sites  s ON e.site_id  = s.site_id

dimensions:
  - name: trial_id
    expr: trial_id
  - name: therapeutic_area
    expr: therapeutic_area
  - name: phase
    expr: phase
  - name: arm
    expr: arm
  - name: withdrawal_reason
    expr: withdrawal_reason
  - name: country
    expr: country
  - name: region
    expr: region
  - name: enrollment_month
    expr: DATE_TRUNC('MONTH', enrollment_date)

measures:
  - name: enrolled_count
    expr: COUNT(DISTINCT enrollment_id)
  - name: withdrawn_count
    expr: COUNT(DISTINCT CASE WHEN withdrawal_date IS NOT NULL THEN enrollment_id END)
  - name: dropout_rate
    expr: COUNT(DISTINCT CASE WHEN withdrawal_date IS NOT NULL THEN enrollment_id END) * 1.0
          / COUNT(DISTINCT enrollment_id)
  - name: avg_days_on_study_before_withdrawal
    expr: AVG(CASE WHEN withdrawal_date IS NOT NULL
                   THEN DATEDIFF(withdrawal_date, enrollment_date) END)
$$
;

-- ============================================================
-- 授权说明：
-- 05_permissions_demo.sql 已经把 schema 级 SELECT 授给两个 persona 组：
--   clinical_site_managers_cn / clinical_safety_reviewers
-- 新建的指标视图自动继承 schema 级 SELECT 权限，无需重复 GRANT。
-- 如需显式细粒度授权，可取消下面注释：
-- GRANT SELECT ON VIEW genie_demo.clinical.mv_enrollment TO `clinical_site_managers_cn`, `clinical_safety_reviewers`;
-- GRANT SELECT ON VIEW genie_demo.clinical.mv_safety     TO `clinical_site_managers_cn`, `clinical_safety_reviewers`;
-- GRANT SELECT ON VIEW genie_demo.clinical.mv_dropout    TO `clinical_site_managers_cn`, `clinical_safety_reviewers`;
-- ============================================================

-- ============================================================
-- 自验证：用 MEASURE() 直接查（任意 SELECT 客户端都能跑）
-- ============================================================
SELECT
  arm,
  MEASURE(enrolled_count)  AS enrolled,
  MEASURE(withdrawn_count) AS withdrawn,
  MEASURE(active_count)    AS active
FROM genie_demo.clinical.mv_enrollment
GROUP BY arm
ORDER BY enrolled DESC;

SELECT
  arm,
  MEASURE(ae_total)        AS ae_total,
  MEASURE(sae_count)       AS sae,
  MEASURE(sae_rate)        AS sae_rate,
  MEASURE(patients_with_ae) AS pts_with_ae
FROM genie_demo.clinical.mv_safety
GROUP BY arm
ORDER BY sae_rate DESC;

SELECT
  trial_id,
  MEASURE(enrolled_count)  AS enrolled,
  MEASURE(withdrawn_count) AS withdrawn,
  MEASURE(dropout_rate)    AS dropout_rate
FROM genie_demo.clinical.mv_dropout
GROUP BY trial_id
ORDER BY dropout_rate DESC;
