-- ============================================================
-- 04_sample_queries.sql
-- 提供给 Genie Space 作为 "Sample Queries" / "Trusted Assets"
-- 在 Genie UI: 进入 Space → 设置 → Example Queries → Add，
-- 把每段 SQL 与对应的"自然语言提问"成对添加。Genie 会用这些示例
-- 学习业务术语与 join 模式，显著提高复杂查询的准确率。
-- ============================================================

-- 提问：当前在组（未退出）的受试者总数
SELECT COUNT(*) AS active_patients
FROM genie_demo.clinical.enrollments
WHERE withdrawal_date IS NULL;

-- 提问：每个治疗领域的入组人数
SELECT t.therapeutic_area, COUNT(*) AS enrolled
FROM genie_demo.clinical.enrollments e
JOIN genie_demo.clinical.trials t ON e.trial_id = t.trial_id
GROUP BY t.therapeutic_area
ORDER BY enrolled DESC;

-- 提问：各试验的入组完成度（实际/计划）
SELECT t.trial_id,
       t.trial_name,
       t.target_enrollment,
       COUNT(e.enrollment_id) AS actual,
       ROUND(COUNT(e.enrollment_id) * 100.0 / t.target_enrollment, 1) AS pct_complete
FROM genie_demo.clinical.trials t
LEFT JOIN genie_demo.clinical.enrollments e ON t.trial_id = e.trial_id
GROUP BY t.trial_id, t.trial_name, t.target_enrollment
ORDER BY pct_complete DESC;

-- 提问：每个试验的严重不良事件 (SAE) 数量与发生率
SELECT t.trial_id,
       t.trial_name,
       COUNT(DISTINCT e.enrollment_id) AS total_subjects,
       COUNT(DISTINCT CASE WHEN ae.is_serious THEN e.enrollment_id END) AS subjects_with_sae,
       ROUND(COUNT(DISTINCT CASE WHEN ae.is_serious THEN e.enrollment_id END) * 100.0
             / COUNT(DISTINCT e.enrollment_id), 2) AS sae_rate_pct
FROM genie_demo.clinical.trials t
JOIN genie_demo.clinical.enrollments e ON t.trial_id = e.trial_id
LEFT JOIN genie_demo.clinical.adverse_events ae ON e.enrollment_id = ae.enrollment_id
GROUP BY t.trial_id, t.trial_name
ORDER BY sae_rate_pct DESC;

-- 提问：Treatment 组 vs Control 组的 AE 发生率对比
SELECT e.arm,
       COUNT(DISTINCT e.enrollment_id) AS subjects,
       COUNT(ae.ae_id) AS total_ae,
       ROUND(COUNT(ae.ae_id) * 1.0 / COUNT(DISTINCT e.enrollment_id), 2) AS ae_per_subject
FROM genie_demo.clinical.enrollments e
LEFT JOIN genie_demo.clinical.adverse_events ae ON e.enrollment_id = ae.enrollment_id
GROUP BY e.arm
ORDER BY ae_per_subject DESC;

-- 提问：最常见的 10 种不良事件
SELECT ae.event_term,
       ae.system_organ_class,
       COUNT(*) AS occurrences,
       SUM(CASE WHEN ae.is_serious THEN 1 ELSE 0 END) AS serious_count
FROM genie_demo.clinical.adverse_events ae
GROUP BY ae.event_term, ae.system_organ_class
ORDER BY occurrences DESC
LIMIT 10;

-- 提问：各区域的入组速度（每月入组人数趋势）
SELECT s.region,
       DATE_TRUNC('month', e.enrollment_date) AS month,
       COUNT(*) AS enrolled
FROM genie_demo.clinical.enrollments e
JOIN genie_demo.clinical.sites s ON e.site_id = s.site_id
GROUP BY s.region, DATE_TRUNC('month', e.enrollment_date)
ORDER BY month, s.region;

-- 提问：受试者退出原因分布
SELECT withdrawal_reason,
       COUNT(*) AS n,
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS pct
FROM genie_demo.clinical.enrollments
WHERE withdrawal_date IS NOT NULL
GROUP BY withdrawal_reason
ORDER BY n DESC;

-- 提问：肝功能异常（ALT 或 AST 超出参考上限）的受试者数量按试验分组
SELECT t.trial_id, t.trial_name,
       COUNT(DISTINCT e.patient_id) AS patients_with_lft_abnormal
FROM genie_demo.clinical.lab_results l
JOIN genie_demo.clinical.enrollments e ON l.enrollment_id = e.enrollment_id
JOIN genie_demo.clinical.trials t ON e.trial_id = t.trial_id
WHERE l.test_name IN ('ALT','AST') AND l.is_abnormal = TRUE
GROUP BY t.trial_id, t.trial_name
ORDER BY patients_with_lft_abnormal DESC;

-- 提问：Top 10 入组数最多的研究中心
SELECT s.site_name, s.country, s.region, COUNT(e.enrollment_id) AS enrolled
FROM genie_demo.clinical.sites s
JOIN genie_demo.clinical.enrollments e ON s.site_id = e.site_id
GROUP BY s.site_name, s.country, s.region
ORDER BY enrolled DESC
LIMIT 10;

-- 提问：每个 PI 负责的试验数与受试者数
SELECT i.full_name AS investigator,
       COUNT(DISTINCT e.trial_id)    AS trials_handled,
       COUNT(DISTINCT e.patient_id)  AS patients_enrolled
FROM genie_demo.clinical.investigators i
JOIN genie_demo.clinical.enrollments e ON i.investigator_id = e.investigator_id
WHERE i.role = 'Principal Investigator'
GROUP BY i.full_name
ORDER BY patients_enrolled DESC;
