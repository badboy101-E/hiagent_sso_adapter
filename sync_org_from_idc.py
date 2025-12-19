#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从身份中台获取组织架构信息并同步到临时数据库
参考：云大组织架构同步.md
"""

import os
import sys
import uuid
import logging
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# 加载环境变量
load_dotenv()

# 导入身份中台SDK
try:
    from cqhyxk import CqhyxkClient
    from cqhyxk.models import IdentityPageRequest, MemberTagPageRequest
except ImportError:
    print("错误: 请先安装 cqhyxk SDK: pip install cqhyxk")
    sys.exit(1)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sync_org.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class OrgSyncFromIDC:
    """从身份中台同步组织架构信息到临时数据库"""
    
    def __init__(self):
        """初始化配置"""
        # 身份中台配置（从环境变量读取）
        self.idc_client = CqhyxkClient()
        
        # 租户ID（从环境变量读取）
        self.tenant_id = os.getenv('TENANT_ID', '0')
        if self.tenant_id == '0':
            logger.warning("警告: TENANT_ID 未设置，使用默认值 '0'")
        
        # 临时数据库配置
        self.tmp_db_config = {
            "host": os.getenv('TMP_DB_HOST', 'localhost'),
            "port": int(os.getenv('TMP_DB_PORT', '5432')),
            "database": os.getenv('TMP_DB_NAME', 'tmp_sync_db'),
            "user": os.getenv('TMP_DB_USER', 'tmp_user'),
            "password": os.getenv('TMP_DB_PASSWORD', '')
        }
        
        logger.info(f"初始化完成 - 租户ID: {self.tenant_id}")
        logger.info(f"临时数据库: {self.tmp_db_config['host']}:{self.tmp_db_config['port']}/{self.tmp_db_config['database']}")
    
    def get_db_connection(self):
        """获取数据库连接"""
        try:
            conn = psycopg2.connect(**self.tmp_db_config)
            return conn
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise
    
    def get_all_users_from_idc(self) -> List[Dict]:
        """
        从身份中台获取所有用户信息
        
        支持多种获取方式：
        1. 优先尝试：不传 sourceUserId，直接分页获取所有用户（如果API支持）
        2. 备用方案：如果API必须传 sourceUserId，则尝试批量查询
        3. 测试方案：使用配置的示例用户ID进行测试
        """
        users = []
        page_size = 100  # 每页大小
        
        logger.info("开始从身份中台获取用户信息...")
        
        # 方案1: 尝试不传 sourceUserId，直接分页获取所有用户
        logger.info("尝试方案1: 不传 sourceUserId，直接分页获取所有用户...")
        try:
            current_page = 0
            while True:
                # 不传 sourceUserId，尝试获取所有用户
                request = IdentityPageRequest(
                    current=current_page,
                    size=page_size
                    # 注意：不传 sourceUserId，如果API支持，应该返回所有用户
                )
                
                response = self.idc_client.get_identity_list(request)
                
                if not response or not response.data:
                    break
                
                # 根据API文档，响应结构：data.page（分页信息）、data.content（查询结果数组）
                page_info = response.data.get('page') or {}
                total_count = page_info.get('total', 0)
                
                # 获取用户列表
                page_users = response.data.get('content') or []
                
                if not page_users:
                    break
                
                users.extend(page_users)
                
                logger.info(f"已获取 {len(users)}/{total_count} 个用户（第 {current_page + 1} 页，每页 {len(page_users)} 条）...")
                
                # 如果返回的数据少于page_size，说明已经是最后一页
                if len(page_users) < page_size:
                    break
                
                # 如果已经获取了所有数据
                if total_count > 0 and len(users) >= total_count:
                    break
                
                current_page += 1
            
            if users:
                logger.info(f"方案1成功！总共获取到 {len(users)} 个用户")
                return users
            else:
                logger.warning("方案1未获取到数据，尝试其他方案...")
        except Exception as e:
            logger.warning(f"方案1失败: {e}")
            logger.info("提示：根据API文档，sourceUserId是非必填参数，如果仍然失败，请检查API配置或使用方案3配置USER_ID_LIST")
        
        # 方案2: 如果API必须传 sourceUserId，尝试批量查询
        # 注意：这需要先获取用户ID列表，可能需要其他API支持
        logger.info("尝试方案2: 查找是否有获取用户ID列表的API...")
        try:
            # 检查是否有获取用户列表的API（不包含详细信息）
            if hasattr(self.idc_client, 'get_user_list') or hasattr(self.idc_client, 'list_users'):
                logger.info("发现用户列表API，尝试获取所有用户ID...")
                # 这里需要根据实际SDK的方法名调整
                # user_ids = self.idc_client.get_user_list()
                # 然后批量查询每个用户的详细信息
                pass
        except Exception as e:
            logger.warning(f"方案2失败: {e}")
        
        # 方案3: 如果提供了用户ID列表配置，批量查询
        user_id_list_str = os.getenv('USER_ID_LIST', '')
        if user_id_list_str:
            logger.info("尝试方案3: 使用配置的用户ID列表批量查询...")
            try:
                user_ids = [uid.strip() for uid in user_id_list_str.split(',') if uid.strip()]
                logger.info(f"从配置中获取到 {len(user_ids)} 个用户ID，开始批量查询...")
                
                for user_id in user_ids:
                    try:
                        request = IdentityPageRequest(
                            current=0,
                            size=page_size,
                            sourceUserId=user_id
                        )
                        response = self.idc_client.get_identity_list(request)
                        if response and response.data and response.data.content:
                            page_users = response.data.content
                            # 去重（避免重复添加）
                            existing_ids = {u.get('userId') or u.get('id') for u in users}
                            for user in page_users:
                                uid = user.get('userId') or user.get('id')
                                if uid and uid not in existing_ids:
                                    users.append(user)
                                    existing_ids.add(uid)
                    except Exception as e:
                        logger.warning(f"查询用户ID {user_id} 失败: {e}")
                        continue
                
                if users:
                    logger.info(f"方案3成功！总共获取到 {len(users)} 个用户")
                    return users
            except Exception as e:
                logger.warning(f"方案3失败: {e}")
        
        # 方案4: 使用示例用户ID进行测试（仅用于测试）
        sample_user_id = os.getenv('SAMPLE_USER_ID')
        if sample_user_id:
            logger.warning("尝试方案4: 使用示例用户ID进行测试（仅返回单个用户）...")
            try:
                request = IdentityPageRequest(
                    current=0,
                    size=page_size,
                    sourceUserId=sample_user_id
                )
                response = self.idc_client.get_identity_list(request)
                if response and response.data and response.data.content:
                    users = response.data.content
                    logger.warning(f"方案4: 使用示例用户ID获取到 {len(users)} 个用户（仅用于测试）")
                    logger.warning("提示: 如需获取所有用户，请配置 USER_ID_LIST 或联系身份中台提供批量查询API")
                    return users
            except Exception as e:
                logger.error(f"方案4也失败: {e}")
        
        # 所有方案都失败
        error_msg = """
无法获取用户信息！可能的原因：
1. API必须传 sourceUserId 参数，且未配置用户ID列表
2. 需要先调用其他API获取用户ID列表
3. 需要联系身份中台提供批量查询所有用户的API

建议解决方案：
1. 在 .env 文件中配置 USER_ID_LIST，格式：USER_ID_LIST=user1,user2,user3
2. 或者联系身份中台确认是否有直接获取所有用户的API
3. 或者查看是否有组织架构相关的API可以直接获取组织信息
        """
        logger.error(error_msg)
        raise Exception("无法获取用户信息，请检查配置或联系身份中台确认API使用方式")
    
    def sync_users(self, users: List[Dict]):
        """同步用户信息到临时表"""
        if not users:
            logger.warning("没有用户数据需要同步")
            return
        
        conn = self.get_db_connection()
        try:
            cur = conn.cursor()
            success_count = 0
            error_count = 0
            
            for user_data in users:
                try:
                    # 解析用户数据（根据API文档：/open-api/member/identity/page）
                    # API返回字段：sourceUserId（学工号）、name（姓名）、mobile（手机号）、status（身份状态）
                    user_id = str(user_data.get('sourceUserId') or user_data.get('userId') or user_data.get('id') or '')
                    user_name = user_data.get('sourceUserId') or user_data.get('userName') or user_data.get('username') or user_data.get('user_name') or ''
                    display_name = user_data.get('name') or user_data.get('displayName') or user_data.get('display_name') or user_name
                    email = user_data.get('email') or user_data.get('mail') or ''
                    mobile = user_data.get('mobile') or user_data.get('phone') or user_data.get('telephone') or ''
                    # status: 1=正常, 2=数据源删除, 3=身份中台删除, 4=禁用, 5=失效, 6=回收站人员
                    # 只有status=1才是正常状态
                    api_status = user_data.get('status', 1)
                    status = 1 if api_status == 1 else 0  # 只有正常状态才启用
                    
                    if not user_id or not user_name:
                        logger.warning(f"跳过无效用户数据: {user_data}")
                        error_count += 1
                        continue
                    
                    # 插入或更新用户表（根据组织架构同步对接指南的表结构）
                    cur.execute("""
                        INSERT INTO tmp_user
                            (id, user_name, description, display_name, email, mobile,
                             tenant_id, source, status, is_deleted, updated_time)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, 'CAS', %s, 0, NOW())
                        ON CONFLICT (tenant_id, user_name)
                        DO UPDATE SET
                            display_name = EXCLUDED.display_name,
                            description = EXCLUDED.description,
                            email = EXCLUDED.email,
                            mobile = EXCLUDED.mobile,
                            status = EXCLUDED.status,
                            is_deleted = 0,
                            updated_time = NOW()
                    """, (
                        user_id,
                        user_name,
                        '',  # description字段，默认为空
                        display_name,
                        email or '',
                        mobile or '',
                        self.tenant_id,
                        status
                    ))
                    
                    success_count += 1
                    
                except Exception as e:
                    logger.error(f"同步用户失败 {user_data}: {e}")
                    error_count += 1
            
            conn.commit()
            logger.info(f"用户同步完成 - 成功: {success_count}, 失败: {error_count}")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"用户同步过程出错: {e}")
            raise
        finally:
            conn.close()
    
    def get_organizations_from_idc(self) -> List[Dict]:
        """
        从身份中台获取组织架构信息
        优先使用 cqhyxk SDK 直接获取组织列表，如果不支持则从用户信息中提取
        """
        organizations = []
        
        logger.info("开始从身份中台获取组织架构信息...")
        
        try:
            # 方案1: 尝试使用 cqhyxk SDK 直接获取组织列表
            if hasattr(self.idc_client, 'get_org_list'):
                logger.info("使用 cqhyxk SDK 直接获取组织列表...")
                try:
                    org_list_response = self.idc_client.get_org_list()
                    if org_list_response and org_list_response.data:
                        org_list = org_list_response.data
                        if isinstance(org_list, list):
                            for org in org_list:
                                organizations.append({
                                    'id': str(org.get('id') or org.get('orgId') or ''),
                                    'name': org.get('name') or org.get('orgName') or '',
                                    'org_code': org.get('orgCode') or org.get('org_code') or str(org.get('id') or ''),
                                    'pid': str(org.get('pid') or org.get('parentId') or org.get('parentOrgId') or '')
                                })
                        logger.info(f"通过 cqhyxk SDK 获取到 {len(organizations)} 个组织")
                        return organizations
                except Exception as e:
                    logger.warning(f"使用 cqhyxk SDK 直接获取组织列表失败，尝试备用方案: {e}")
            
            # 方案2: 从用户身份信息中提取组织信息（备用方案）
            logger.info("从用户身份信息中提取组织信息...")
            users = self.get_all_users_from_idc()
            org_set = set()
            
            for user in users:
                # 从用户信息中提取组织信息（根据API文档）
                # API返回：orgList（所属组织信息数组）和 mainOrg（主组织）
                # orgList内字段：orgId（组织编码）、orgName（组织名称）、sourceOrgId（组织原编码）
                
                # 提取主组织信息
                main_org = user.get('mainOrg')
                if main_org:
                    org_id = main_org.get('orgId') or main_org.get('sourceOrgId') or ''
                    org_name = main_org.get('orgName') or ''
                    if org_id:
                        org_key = (org_id, org_name, '')  # 主组织暂时没有父组织ID
                        if org_key not in org_set:
                            org_set.add(org_key)
                            organizations.append({
                                'id': org_id,
                                'name': org_name or org_id,
                                'org_code': org_id,
                                'pid': ''  # 主组织的父组织ID需要从其他接口获取
                            })
                
                # 提取orgList中的所有组织信息
                org_list = user.get('orgList') or []
                if isinstance(org_list, list):
                    for org in org_list:
                        org_id = org.get('orgId') or org.get('sourceOrgId') or ''
                        org_name = org.get('orgName') or ''
                        if org_id:
                            org_key = (org_id, org_name, '')  # orgList中的组织暂时没有父组织ID
                            if org_key not in org_set:
                                org_set.add(org_key)
                                organizations.append({
                                    'id': org_id,
                                    'name': org_name or org_id,
                                    'org_code': org_id,
                                    'pid': ''  # 需要从组织架构接口获取父组织ID
                                })
            
            logger.info(f"从用户信息中提取到 {len(organizations)} 个组织")
            
        except Exception as e:
            logger.error(f"获取组织架构信息失败: {e}")
            raise
        
        return organizations
    
    def sync_organizations(self, organizations: List[Dict]):
        """同步组织信息到临时表"""
        if not organizations:
            logger.warning("没有组织数据需要同步")
            return
        
        conn = self.get_db_connection()
        try:
            cur = conn.cursor()
            success_count = 0
            error_count = 0
            
            for org_data in organizations:
                try:
                    org_id = str(org_data.get('id') or '')
                    org_name = org_data.get('name') or ''
                    org_code = org_data.get('org_code') or org_id
                    pid = str(org_data.get('pid') or '')
                    
                    if not org_id:
                        logger.warning(f"跳过无效组织数据: {org_data}")
                        error_count += 1
                        continue
                    
                    # 插入或更新组织表
                    cur.execute("""
                        INSERT INTO tmp_organization
                            (id, name, org_code, tenant_id, pid, is_deleted, updated_time)
                        VALUES (%s, %s, %s, %s, %s, 0, NOW())
                        ON CONFLICT (tenant_id, org_code)
                        DO UPDATE SET
                            name = EXCLUDED.name,
                            pid = EXCLUDED.pid,
                            is_deleted = 0,
                            updated_time = NOW()
                    """, (
                        org_id,
                        org_name,
                        org_code,
                        self.tenant_id,
                        pid
                    ))
                    
                    success_count += 1
                    
                except Exception as e:
                    logger.error(f"同步组织失败 {org_data}: {e}")
                    error_count += 1
            
            conn.commit()
            logger.info(f"组织同步完成 - 成功: {success_count}, 失败: {error_count}")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"组织同步过程出错: {e}")
            raise
        finally:
            conn.close()
    
    def sync_user_org_relations(self, users: List[Dict]):
        """同步用户-组织关系到临时表"""
        if not users:
            logger.warning("没有用户数据，无法同步用户-组织关系")
            return
        
        conn = self.get_db_connection()
        try:
            cur = conn.cursor()
            
            # 先清空旧的关系数据
            cur.execute(
                "DELETE FROM tmp_org_user_relation WHERE tenant_id = %s",
                (self.tenant_id,)
            )
            logger.info("已清空旧的用户-组织关系数据")
            
            success_count = 0
            error_count = 0
            
            for user_data in users:
                try:
                    # 根据API文档，用户ID是sourceUserId
                    user_id = str(user_data.get('sourceUserId') or user_data.get('userId') or user_data.get('id') or '')
                    
                    if not user_id:
                        continue
                    
                    # 收集用户的所有组织ID（包括主组织和orgList中的所有组织）
                    org_ids = set()
                    
                    # 添加主组织
                    main_org = user_data.get('mainOrg')
                    if main_org:
                        org_id = main_org.get('orgId') or main_org.get('sourceOrgId')
                        if org_id:
                            org_ids.add(str(org_id))
                    
                    # 添加orgList中的所有组织
                    org_list = user_data.get('orgList') or []
                    if isinstance(org_list, list):
                        for org in org_list:
                            org_id = org.get('orgId') or org.get('sourceOrgId')
                            if org_id:
                                org_ids.add(str(org_id))
                    
                    # 为每个组织创建用户-组织关系
                    for org_id in org_ids:
                        try:
                            cur.execute("""
                                INSERT INTO tmp_org_user_relation
                                    (id, org_id, user_id, tenant_id)
                                VALUES (%s, %s, %s, %s)
                                ON CONFLICT DO NOTHING
                            """, (
                                str(uuid.uuid4()),
                                org_id,
                                user_id,
                                self.tenant_id
                            ))
                            success_count += 1
                        except Exception as e:
                            logger.warning(f"插入用户-组织关系失败 (user_id={user_id}, org_id={org_id}): {e}")
                            error_count += 1
                    
                except Exception as e:
                    logger.error(f"同步用户-组织关系失败 {user_data}: {e}")
                    error_count += 1
            
            conn.commit()
            logger.info(f"用户-组织关系同步完成 - 成功: {success_count}, 失败: {error_count}")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"用户-组织关系同步过程出错: {e}")
            raise
        finally:
            conn.close()
    
    def mark_deleted_users(self, active_user_ids: List[str]):
        """标记已删除的用户"""
        if not active_user_ids:
            return
        
        conn = self.get_db_connection()
        try:
            cur = conn.cursor()
            
            # 将不在活跃用户列表中的用户标记为已删除
            cur.execute("""
                UPDATE tmp_user
                SET is_deleted = 1, updated_time = NOW()
                WHERE tenant_id = %s AND id != ALL(%s)
            """, (self.tenant_id, active_user_ids))
            
            deleted_count = cur.rowcount
            conn.commit()
            logger.info(f"标记删除用户数量: {deleted_count}")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"标记删除用户过程出错: {e}")
            raise
        finally:
            conn.close()
    
    def mark_deleted_organizations(self, active_org_ids: List[str]):
        """标记已删除的组织"""
        if not active_org_ids:
            return
        
        conn = self.get_db_connection()
        try:
            cur = conn.cursor()
            
            # 将不在活跃组织列表中的组织标记为已删除
            cur.execute("""
                UPDATE tmp_organization
                SET is_deleted = 1, updated_time = NOW()
                WHERE tenant_id = %s AND id != ALL(%s)
            """, (self.tenant_id, active_org_ids))
            
            deleted_count = cur.rowcount
            conn.commit()
            logger.info(f"标记删除组织数量: {deleted_count}")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"标记删除组织过程出错: {e}")
            raise
        finally:
            conn.close()
    
    def run(self):
        """执行完整的同步流程"""
        logger.info("=" * 50)
        logger.info("开始从身份中台同步组织架构数据到临时表")
        logger.info("=" * 50)
        
        try:
            # 1. 获取用户信息
            logger.info("\n[1/5] 从身份中台获取用户信息...")
            users = self.get_all_users_from_idc()
            
            # 2. 同步用户
            logger.info("\n[2/5] 同步用户到临时表...")
            self.sync_users(users)
            active_user_ids = [str(u.get('userId') or u.get('id') or '') for u in users if u.get('userId') or u.get('id')]
            
            # 3. 获取组织架构信息
            logger.info("\n[3/5] 从身份中台获取组织架构信息...")
            organizations = self.get_organizations_from_idc()
            
            # 4. 同步组织
            logger.info("\n[4/5] 同步组织到临时表...")
            self.sync_organizations(organizations)
            active_org_ids = [str(o.get('id') or '') for o in organizations if o.get('id')]
            
            # 5. 同步用户-组织关系
            logger.info("\n[5/5] 同步用户-组织关系到临时表...")
            self.sync_user_org_relations(users)
            
            # 6. 标记已删除的用户和组织
            logger.info("\n[6/6] 标记已删除的用户和组织...")
            self.mark_deleted_users(active_user_ids)
            self.mark_deleted_organizations(active_org_ids)
            
            logger.info("\n" + "=" * 50)
            logger.info("同步完成!")
            logger.info("=" * 50)
            
        except Exception as e:
            logger.error(f"同步过程出错: {e}", exc_info=True)
            raise


def main():
    """主函数"""
    try:
        sync = OrgSyncFromIDC()
        sync.run()
    except KeyboardInterrupt:
        logger.info("\n用户中断同步")
        sys.exit(1)
    except Exception as e:
        logger.error(f"程序执行失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()


