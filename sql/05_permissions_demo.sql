-- ============================================================
-- 05_permissions_demo.sql
-- 演示：不同权限用户使用 Genie 的隔离方式
-- 通过 Unity Catalog Row Filter + Column Mask 实现，
-- Genie Space 无需重新绑定，原有 Space 透明继承所有治理规则。
--
-- 演示效果：
--   - clinical_site_managers_cn  -> sites 表只能看到 China 行；patients 敏感列脱敏
--   - clinical_safety_reviewers  -> sites 全量；patients 敏感列明文
-- ============================================================

USE CATALOG genie_demo;
USE SCHEMA clinical;

-- ⚠️ 重置环境时手动执行（仅在已存在策略时运行，否则会报错）：
--   ALTER TABLE sites       DROP ROW FILTER;
--   ALTER TABLE enrollments DROP ROW FILTER;
--   ALTER TABLE patients ALTER COLUMN comorbidities DROP MASK;
--   ALTER TABLE patients ALTER COLUMN bmi           DROP MASK;
--   ALTER TABLE patients ALTER COLUMN smoker        DROP MASK;

-- ------------------------------------------------------------
-- 1. Row Filter on sites: 中国站点经理只能看 country='China'
-- ------------------------------------------------------------
-- 注意：使用 is_member()（workspace 组）；如果使用 account-level 组请改为 is_account_group_member()
CREATE OR REPLACE FUNCTION rf_sites_by_country(country STRING)
RETURN
  is_member('clinical_safety_reviewers')
  OR (is_member('clinical_site_managers_cn') AND country = 'China');

ALTER TABLE sites SET ROW FILTER rf_sites_by_country ON (country);

-- ------------------------------------------------------------
-- 2. Column Mask on patients: bmi / smoker / comorbidities
--    仅 safety_reviewer 可看明文，其他角色脱敏
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION mask_string_for_safety(val STRING)
RETURN CASE
  WHEN is_member('clinical_safety_reviewers') THEN val
  ELSE 'REDACTED'
END;

CREATE OR REPLACE FUNCTION mask_double_for_safety(val DOUBLE)
RETURN CASE
  WHEN is_member('clinical_safety_reviewers') THEN val
  ELSE CAST(NULL AS DOUBLE)
END;

CREATE OR REPLACE FUNCTION mask_bool_for_safety(val BOOLEAN)
RETURN CASE
  WHEN is_member('clinical_safety_reviewers') THEN val
  ELSE CAST(NULL AS BOOLEAN)
END;

ALTER TABLE patients ALTER COLUMN comorbidities SET MASK mask_string_for_safety;
ALTER TABLE patients ALTER COLUMN bmi           SET MASK mask_double_for_safety;
ALTER TABLE patients ALTER COLUMN smoker        SET MASK mask_bool_for_safety;

-- ------------------------------------------------------------
-- 3. 授权
-- ------------------------------------------------------------
GRANT USE CATALOG ON CATALOG genie_demo
  TO `clinical_site_managers_cn`, `clinical_safety_reviewers`;
GRANT USE SCHEMA ON SCHEMA genie_demo.clinical
  TO `clinical_site_managers_cn`, `clinical_safety_reviewers`;
GRANT SELECT ON SCHEMA genie_demo.clinical
  TO `clinical_site_managers_cn`, `clinical_safety_reviewers`;

GRANT EXECUTE ON FUNCTION rf_sites_by_country     TO `clinical_site_managers_cn`, `clinical_safety_reviewers`;
GRANT EXECUTE ON FUNCTION mask_string_for_safety  TO `clinical_site_managers_cn`, `clinical_safety_reviewers`;
GRANT EXECUTE ON FUNCTION mask_double_for_safety  TO `clinical_site_managers_cn`, `clinical_safety_reviewers`;
GRANT EXECUTE ON FUNCTION mask_bool_for_safety    TO `clinical_site_managers_cn`, `clinical_safety_reviewers`;
