# 身份中台组织架构同步脚本

本脚本用于从身份中台获取组织架构信息，并同步到临时数据库表中，供 iam-adapter 使用。

## 功能说明

- 从身份中台获取用户信息
- 从身份中台获取组织架构信息
- 同步用户、组织、用户-组织关系到临时数据库
- 标记已删除的用户和组织

## 环境要求

- Python 3.7+
- PostgreSQL 数据库（临时数据库）

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置说明

1. 复制 `env.example` 为 `.env`
2. 修改 `.env` 文件中的配置信息：

```bash
cp env.example .env
```

### 必需配置项

- `CQHYXK_BASEURL`: 身份中台API地址
- `CQHYXK_APP_KEY`: 身份中台应用Key
- `CQHYXK_APP_SECRET`: 身份中台应用Secret
- `TENANT_ID`: 租户ID（从HiAgent环境获取）
- `TMP_DB_HOST`: 临时数据库地址
- `TMP_DB_PORT`: 临时数据库端口
- `TMP_DB_NAME`: 临时数据库名称
- `TMP_DB_USER`: 临时数据库用户名
- `TMP_DB_PASSWORD`: 临时数据库密码

### 可选配置项

- `SAMPLE_USER_ID`: 示例用户ID（用于测试）
- `USER_ID_LIST`: 用户ID列表（如果API必须传sourceUserId，可以配置多个用户ID，用逗号分隔，例如：`USER_ID_LIST=20160019,20160020,20160021`）

## 数据库表结构

在使用本脚本前，需要先在临时数据库中创建以下表：

### 临时用户表 (tmp_user)

```sql
CREATE TABLE IF NOT EXISTS tmp_user (
    id              VARCHAR(64)     NOT NULL PRIMARY KEY,
    created_time    TIMESTAMP       DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_time    TIMESTAMP       DEFAULT CURRENT_TIMESTAMP NOT NULL,
    tenant_id       VARCHAR(64)     DEFAULT '0' NOT NULL,
    user_name       VARCHAR(128)    DEFAULT '' NOT NULL,
    description     VARCHAR(255)    DEFAULT '' NOT NULL,
    display_name    VARCHAR(255)    DEFAULT '' NOT NULL,
    email           VARCHAR(256)    DEFAULT '' NOT NULL,
    mobile          VARCHAR(256)    DEFAULT '' NOT NULL,
    source          VARCHAR(16)     DEFAULT 'CAS' NOT NULL,
    status          SMALLINT        DEFAULT 1 NOT NULL,
    is_deleted      SMALLINT        DEFAULT 0 NOT NULL,
    CONSTRAINT uk_tenant_id_user_name UNIQUE (tenant_id, user_name)
);
```

### 临时组织表 (tmp_organization)

```sql
CREATE TABLE IF NOT EXISTS tmp_organization (
    id              VARCHAR(64)     NOT NULL PRIMARY KEY,
    created_time    TIMESTAMP       DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_time    TIMESTAMP       DEFAULT CURRENT_TIMESTAMP NOT NULL,
    name            VARCHAR(128)    DEFAULT '' NOT NULL,
    org_code        VARCHAR(128)    DEFAULT '' NOT NULL,
    tenant_id       VARCHAR(64)     DEFAULT '' NOT NULL,
    pid             VARCHAR(64)     DEFAULT '' NOT NULL,
    is_deleted      SMALLINT        DEFAULT 0 NOT NULL,
    CONSTRAINT uk_tenant_id_org_code UNIQUE (tenant_id, org_code)
);
```

### 临时用户组织关系表 (tmp_org_user_relation)

```sql
CREATE TABLE IF NOT EXISTS tmp_org_user_relation (
    id              VARCHAR(64)     NOT NULL PRIMARY KEY,
    created_time    TIMESTAMP       DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_time    TIMESTAMP       DEFAULT CURRENT_TIMESTAMP NOT NULL,
    org_id          VARCHAR(64)     NOT NULL,
    user_id         VARCHAR(64)     DEFAULT '' NOT NULL,
    tenant_id       VARCHAR(64)     DEFAULT '' NOT NULL
);
```

## 快速开始

详细步骤请参考：[快速开始.md](./快速开始.md)

### 快速配置

1. 复制配置文件：`cp env.example .env`
2. 修改配置：编辑 `.env` 文件，填入实际的API密钥、数据库配置和租户ID
3. 创建临时表：`psql -h your_db_host -p 5432 -U your_db_user -d postgres -f init_tables.sql`
4. 测试连接：`python test_db_connection.py`
5. 运行同步：`python sync_org_from_idc.py`

## 使用方法

### 手动执行

```bash
python sync_org_from_idc.py
```

### 定时执行（使用cron）

```bash
# 编辑crontab
crontab -e

# 添加定时任务，例如每天凌晨2点执行
0 2 * * * cd /path/to/hiagent-sso-adapter && /usr/bin/python3 sync_org_from_idc.py >> /var/log/sync_org.log 2>&1
```

## 日志说明

脚本执行时会生成日志文件 `sync_org.log`，记录同步过程的详细信息。

## 注意事项

1. **API使用说明（基于[官方API文档](https://github.com/liudonghua123/cqhyxk/blob/main/docs/cqhyxk_OpenAPI_v2.4.md)）**: 
   - **接口**: `/open-api/member/identity/page` (POST)
   - **关键参数**: `sourceUserId` 是**非必填参数**（`是否必须: false`），因此可以直接不传该参数来获取所有用户
   - **分页支持**: 支持 `current`（当前页）和 `size`（页面大小）参数进行分页查询
   - **组织信息**: API响应中已包含 `orgList`（所属组织信息数组）和 `mainOrg`（主组织）字段，可直接提取组织架构信息
   
   - 脚本会尝试多种方式获取所有用户信息：
     - **方案1（优先，推荐）**: 不传 `sourceUserId`，直接分页获取所有用户（根据API文档，这是标准用法）
     - **方案2**: 查找是否有获取用户ID列表的API
     - **方案3**: 如果配置了 `USER_ID_LIST`，批量查询指定用户ID列表（适用于需要筛选特定用户的情况）
     - **方案4**: 使用 `SAMPLE_USER_ID` 进行测试（仅返回单个用户）
   
   - **数据字段映射**（根据API文档）:
     - 用户ID: `sourceUserId`（学工号）
     - 姓名: `name`
     - 手机号: `mobile`
     - 身份状态: `status`（1=正常，2=数据源删除，3=身份中台删除，4=禁用，5=失效，6=回收站人员）
     - 组织信息: `orgList`（数组）和 `mainOrg`（主组织）
     - 组织编码: `orgId` 或 `sourceOrgId`
     - 组织名称: `orgName`

2. **数据映射**: 脚本中的数据字段映射可能需要根据实际API返回的数据结构进行调整。请检查以下方法中的字段映射：
   - `sync_users()`: 用户字段映射
   - `get_organizations_from_idc()`: 组织字段提取
   - `sync_user_org_relations()`: 用户-组织关系字段映射

3. **错误处理**: 脚本包含基本的错误处理，但建议在生产环境中添加更完善的错误处理和重试机制。

4. **性能优化**: 如果数据量很大，可以考虑：
   - 使用批量插入
   - 添加事务控制
   - 实现增量同步
   - 如果使用 `USER_ID_LIST`，考虑分批处理避免单次请求过多

## 参考文档

- [组织架构同步对接指南.md](./组织架构同步对接指南.md)
- [cqhyxk SDK文档](https://pypi.org/project/cqhyxk/)
- [身份中台V2.0 OpenAPI接口文档](https://github.com/liudonghua123/cqhyxk/blob/main/docs/cqhyxk_OpenAPI_v2.4.md) - **官方API文档，包含详细的接口说明和字段定义**

## 问题排查

1. **连接失败**: 检查数据库配置和网络连接
2. **API调用失败**: 检查身份中台的配置和权限
3. **数据同步失败**: 查看日志文件 `sync_org.log` 获取详细错误信息


