-- 创建临时表脚本
-- 数据库：PostgreSQL
-- 用途：存储从身份中台同步的组织架构信息

-- 临时用户表 (tmp_user)
CREATE TABLE IF NOT EXISTS tmp_user (
    id              VARCHAR(64)     NOT NULL PRIMARY KEY,  -- 直接用三方系统的用户ID
    created_time    TIMESTAMP       DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_time    TIMESTAMP       DEFAULT CURRENT_TIMESTAMP NOT NULL,
    tenant_id       VARCHAR(64)     DEFAULT '0' NOT NULL,  -- 从HiAgent获取租户ID
    user_name       VARCHAR(128)    DEFAULT '' NOT NULL,   -- 用户名(唯一)
    description     VARCHAR(255)    DEFAULT '' NOT NULL,
    display_name    VARCHAR(255)    DEFAULT '' NOT NULL,   -- 显示名称
    email           VARCHAR(256)    DEFAULT '' NOT NULL,
    mobile          VARCHAR(256)    DEFAULT '' NOT NULL,
    source          VARCHAR(16)     DEFAULT 'CAS' NOT NULL,-- 用户来源
    status          SMALLINT        DEFAULT 1 NOT NULL,    -- 1:active 0:inactive
    is_deleted      SMALLINT        DEFAULT 0 NOT NULL,    -- 0:否 1:是
    CONSTRAINT uk_tenant_id_user_name UNIQUE (tenant_id, user_name)
);

-- 临时组织表 (tmp_organization)
CREATE TABLE IF NOT EXISTS tmp_organization (
    id              VARCHAR(64)     NOT NULL PRIMARY KEY,  -- 直接用三方系统的组织ID
    created_time    TIMESTAMP       DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_time    TIMESTAMP       DEFAULT CURRENT_TIMESTAMP NOT NULL,
    name            VARCHAR(128)    DEFAULT '' NOT NULL,   -- 组织名称
    org_code        VARCHAR(128)    DEFAULT '' NOT NULL,   -- 组织编码(唯一)
    tenant_id       VARCHAR(64)     DEFAULT '' NOT NULL,   -- 租户ID
    pid             VARCHAR(64)     DEFAULT '' NOT NULL,   -- 父节点ID(根节点为空)
    is_deleted      SMALLINT        DEFAULT 0 NOT NULL,
    CONSTRAINT uk_tenant_id_org_code UNIQUE (tenant_id, org_code)
);

-- 临时用户组织关系表 (tmp_org_user_relation)
CREATE TABLE IF NOT EXISTS tmp_org_user_relation (
    id              VARCHAR(64)     NOT NULL PRIMARY KEY,
    created_time    TIMESTAMP       DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_time    TIMESTAMP       DEFAULT CURRENT_TIMESTAMP NOT NULL,
    org_id          VARCHAR(64)     NOT NULL,              -- 组织ID
    user_id         VARCHAR(64)     DEFAULT '' NOT NULL,   -- 用户ID
    tenant_id       VARCHAR(64)     DEFAULT '' NOT NULL    -- 租户ID
);

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_tmp_user_tenant_id ON tmp_user(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tmp_user_status ON tmp_user(status);
CREATE INDEX IF NOT EXISTS idx_tmp_user_is_deleted ON tmp_user(is_deleted);

CREATE INDEX IF NOT EXISTS idx_tmp_org_tenant_id ON tmp_organization(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tmp_org_pid ON tmp_organization(pid);
CREATE INDEX IF NOT EXISTS idx_tmp_org_is_deleted ON tmp_organization(is_deleted);

CREATE INDEX IF NOT EXISTS idx_tmp_relation_org_id ON tmp_org_user_relation(org_id);
CREATE INDEX IF NOT EXISTS idx_tmp_relation_user_id ON tmp_org_user_relation(user_id);
CREATE INDEX IF NOT EXISTS idx_tmp_relation_tenant_id ON tmp_org_user_relation(tenant_id);

-- 显示创建结果
SELECT '临时表创建完成！' AS message;
SELECT COUNT(*) AS tmp_user_count FROM tmp_user;
SELECT COUNT(*) AS tmp_org_count FROM tmp_organization;
SELECT COUNT(*) AS tmp_relation_count FROM tmp_org_user_relation;

