-- 查询示例：如何从关系表中获取组织名称

-- 1. 查询用户-组织关系，包含组织名称（通过JOIN）
SELECT 
    r.id AS relation_id,
    r.user_id,
    r.org_id,
    o.name AS org_name,  -- 从tmp_organization表获取组织名称
    o.org_code,
    r.tenant_id,
    r.created_time,
    r.updated_time
FROM tmp_org_user_relation r
LEFT JOIN tmp_organization o ON r.org_id = o.id AND r.tenant_id = o.tenant_id
WHERE r.tenant_id = 'your_tenant_id'
ORDER BY r.user_id, o.name;

-- 2. 查询特定用户的所有组织（包含组织名称）
SELECT 
    u.user_name,
    u.display_name,
    o.name AS org_name,
    o.org_code,
    r.org_id
FROM tmp_org_user_relation r
JOIN tmp_user u ON r.user_id = u.id AND r.tenant_id = u.tenant_id
JOIN tmp_organization o ON r.org_id = o.id AND r.tenant_id = o.tenant_id
WHERE r.user_id = 'your_user_id' 
  AND r.tenant_id = 'your_tenant_id';

-- 3. 查询特定组织的所有用户（包含用户和组织信息）
SELECT 
    o.name AS org_name,
    o.org_code,
    u.user_name,
    u.display_name,
    u.email,
    u.mobile
FROM tmp_org_user_relation r
JOIN tmp_organization o ON r.org_id = o.id AND r.tenant_id = o.tenant_id
JOIN tmp_user u ON r.user_id = u.id AND r.tenant_id = u.tenant_id
WHERE r.org_id = 'your_org_id'
  AND r.tenant_id = 'your_tenant_id'
  AND u.is_deleted = 0
  AND o.is_deleted = 0
ORDER BY u.display_name;

-- 4. 统计每个组织的用户数量
SELECT 
    o.name AS org_name,
    o.org_code,
    COUNT(DISTINCT r.user_id) AS user_count
FROM tmp_organization o
LEFT JOIN tmp_org_user_relation r ON o.id = r.org_id AND o.tenant_id = r.tenant_id
LEFT JOIN tmp_user u ON r.user_id = u.id AND r.tenant_id = u.tenant_id AND u.is_deleted = 0
WHERE o.tenant_id = 'your_tenant_id'
  AND o.is_deleted = 0
GROUP BY o.id, o.name, o.org_code
ORDER BY user_count DESC;

-- 5. 查询用户的主组织（如果mainOrg信息已同步）
-- 注意：如果需要在关系表中标识主组织，可能需要添加is_main字段
-- 当前版本中，可以通过查询tmp_user表获取用户信息，然后通过orgList判断主组织

