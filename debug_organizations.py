#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试脚本：检查组织数据提取和同步问题
"""

import os
import sys
import logging
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 导入主同步脚本的类和函数
from sync_org_from_idc import OrgSyncFromIDC, get_attr, get_value

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,  # 使用DEBUG级别获取更详细的信息
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug_organizations.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class DebugOrgSync(OrgSyncFromIDC):
    """调试用的同步类，限制用户数量"""
    
    def __init__(self, max_users=1000):
        """初始化，设置最大用户数"""
        super().__init__()
        self.max_users = max_users
        logger.info(f"调试模式：最多处理 {self.max_users} 个用户")
    
    def get_all_users_from_idc(self):
        """
        重写父类方法，限制获取的用户数量
        """
        users = []
        page_size = 100  # 每页大小
        current_page = 0
        
        logger.info(f"开始从身份中台获取用户信息（限制：{self.max_users}个）...")
        
        # 方案1: 不传 sourceUserId，直接分页获取用户
        logger.info("方案1: 不传 sourceUserId，直接分页获取用户...")
        try:
            from cqhyxk.models import IdentityPageRequest
            
            while len(users) < self.max_users:
                # 计算本页需要获取的数量
                remaining = self.max_users - len(users)
                current_page_size = min(page_size, remaining)
                
                request = IdentityPageRequest(
                    current=current_page,
                    size=current_page_size
                )
                
                response = self.idc_client.get_identity_list(request)
                
                if not response or not response.data:
                    break
                
                # 获取分页信息
                page_info = get_attr(response.data, 'page')
                total_count = get_attr(page_info, 'total', 0) if page_info else 0
                
                # 获取用户列表
                page_users = get_attr(response.data, 'content') or []
                
                if not page_users:
                    break
                
                # 只添加需要的数量
                remaining = self.max_users - len(users)
                if remaining > 0:
                    users.extend(page_users[:remaining])
                
                logger.info(f"已获取 {len(users)}/{min(self.max_users, total_count) if total_count > 0 else self.max_users} 个用户（第 {current_page + 1} 页，本页 {len(page_users)} 条）...")
                
                # 如果已经获取了足够的用户或没有更多数据
                if len(users) >= self.max_users or len(page_users) < page_size:
                    break
                
                current_page += 1
            
            if users:
                logger.info(f"方案1成功！总共获取到 {len(users)} 个用户（限制：{self.max_users}）")
                return users
            else:
                logger.warning("方案1未获取到数据，尝试其他方案...")
        except Exception as e:
            logger.warning(f"方案1失败: {e}")
            logger.info("尝试使用示例用户ID进行测试...")
        
        # 方案2: 使用示例用户ID进行测试（如果方案1失败）
        sample_user_id = os.getenv('SAMPLE_USER_ID')
        if sample_user_id:
            logger.warning("方案2: 使用示例用户ID进行测试（仅返回单个用户）...")
            try:
                from cqhyxk.models import IdentityPageRequest
                request = IdentityPageRequest(
                    current=0,
                    size=1,
                    sourceUserId=sample_user_id
                )
                response = self.idc_client.get_identity_list(request)
                if response and response.data:
                    page_users = get_attr(response.data, 'content') or []
                    if page_users:
                        users = page_users[:1]  # 只取1个用户
                        logger.warning(f"方案2: 使用示例用户ID获取到 {len(users)} 个用户（仅用于测试）")
                        return users
            except Exception as e:
                logger.error(f"方案2也失败: {e}")
        
        # 所有方案都失败
        error_msg = f"""
无法获取用户信息！可能的原因：
1. API必须传 sourceUserId 参数，且未配置用户ID列表
2. 需要先调用其他API获取用户ID列表
3. 需要联系身份中台提供批量查询所有用户的API

建议解决方案：
1. 在 .env 文件中配置 USER_ID_LIST，格式：USER_ID_LIST=user1,user2,user3
2. 或者联系身份中台确认是否有直接获取所有用户的API
        """
        logger.error(error_msg)
        raise Exception("无法获取用户信息，请检查配置或联系身份中台确认API使用方式")


def debug_organizations(max_users=1000):
    """
    调试组织数据提取
    
    Args:
        max_users: 最大处理用户数量，默认1000
    """
    logger.info("=" * 50)
    logger.info(f"开始调试组织数据提取（限制：{max_users}个用户）")
    logger.info("=" * 50)
    
    try:
        sync = DebugOrgSync(max_users=max_users)
        
        # 1. 获取用户数据（已限制数量）
        logger.info(f"\n[步骤1] 获取用户数据（最多{max_users}个）...")
        users = sync.get_all_users_from_idc()
        logger.info(f"实际获取到 {len(users)} 个用户")
        
        if not users:
            logger.error("没有用户数据，无法提取组织信息")
            return
        
        # 2. 检查用户数据中的组织信息
        logger.info("\n[步骤2] 检查用户数据中的组织信息...")
        users_with_org = 0
        users_without_org = 0
        
        for idx, user in enumerate(users[:10], 1):  # 只检查前10个用户
            user_id = get_attr(user, 'sourceUserId')
            main_org = get_attr(user, 'mainOrg')
            org_list = get_attr(user, 'orgList') or []
            
            logger.info(f"\n用户 {idx}: {user_id}")
            logger.info(f"  mainOrg: {main_org}")
            logger.info(f"  orgList类型: {type(org_list)}, 长度: {len(org_list) if isinstance(org_list, list) else 'N/A'}")
            
            if main_org:
                org_id = get_attr(main_org, 'orgId') or get_attr(main_org, 'sourceOrgId')
                org_name = get_attr(main_org, 'orgName')
                logger.info(f"  主组织 - ID: {org_id}, Name: {org_name}")
                users_with_org += 1
            else:
                logger.warning(f"  用户 {user_id} 没有主组织")
            
            if isinstance(org_list, list) and len(org_list) > 0:
                logger.info(f"  orgList包含 {len(org_list)} 个组织:")
                for i, org in enumerate(org_list[:3], 1):  # 只显示前3个
                    org_id = get_attr(org, 'orgId') or get_attr(org, 'sourceOrgId')
                    org_name = get_attr(org, 'orgName')
                    logger.info(f"    组织{i} - ID: {org_id}, Name: {org_name}")
                if not main_org:
                    users_with_org += 1
            else:
                logger.warning(f"  用户 {user_id} 的orgList为空")
                if not main_org:
                    users_without_org += 1
        
        logger.info(f"\n统计（前{check_count}个用户）:")
        logger.info(f"  有组织信息的用户: {users_with_org}")
        logger.info(f"  无组织信息的用户: {users_without_org}")
        
        # 3. 从限制的用户中提取组织信息
        logger.info(f"\n[步骤3] 从 {len(users)} 个用户中提取组织信息...")
        
        # 手动提取组织信息（使用限制后的用户列表）
        organizations = []
        org_set = set()
        
        for user in users:
            # 提取主组织信息
            main_org = get_attr(user, 'mainOrg')
            if main_org:
                org_id = str(get_attr(main_org, 'orgId') or get_attr(main_org, 'sourceOrgId') or '')
                org_name = str(get_attr(main_org, 'orgName') or '')
                if org_id:
                    org_key = (org_id, org_name, '')
                    if org_key not in org_set:
                        org_set.add(org_key)
                        organizations.append({
                            'id': org_id,
                            'name': org_name or org_id,
                            'orgName': org_name,
                            'org_code': org_id,
                            'pid': ''
                        })
            
            # 提取orgList中的所有组织信息
            org_list = get_attr(user, 'orgList') or []
            if isinstance(org_list, list):
                for org in org_list:
                    org_id = str(get_attr(org, 'orgId') or get_attr(org, 'sourceOrgId') or '')
                    org_name = str(get_attr(org, 'orgName') or '')
                    if org_id:
                        org_key = (org_id, org_name, '')
                        if org_key not in org_set:
                            org_set.add(org_key)
                            organizations.append({
                                'id': org_id,
                                'name': org_name or org_id,
                                'orgName': org_name,
                                'org_code': org_id,
                                'pid': ''
                            })
        
        logger.info(f"从 {len(users)} 个用户中提取到 {len(organizations)} 个组织")
        
        if organizations:
            logger.info("\n前5个组织信息:")
            for idx, org in enumerate(organizations[:5], 1):
                logger.info(f"  组织{idx}: {org}")
        else:
            logger.error("未提取到任何组织！")
            logger.error("请检查:")
            logger.error("1. 用户数据中是否包含组织信息")
            logger.error("2. 组织提取逻辑是否正确")
        
        # 4. 检查数据库连接和表结构
        logger.info("\n[步骤4] 检查数据库连接和表结构...")
        try:
            conn = sync.get_db_connection()
            cur = conn.cursor()
            
            # 检查表是否存在
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'tmp_organization'
                );
            """)
            table_exists = cur.fetchone()[0]
            logger.info(f"  tmp_organization表存在: {table_exists}")
            
            if table_exists:
                # 检查表结构
                cur.execute("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'tmp_organization'
                    ORDER BY ordinal_position;
                """)
                columns = cur.fetchall()
                logger.info(f"  表结构:")
                for col_name, col_type in columns:
                    logger.info(f"    {col_name}: {col_type}")
                
                # 检查现有数据
                cur.execute("SELECT COUNT(*) FROM tmp_organization WHERE tenant_id = %s", (sync.tenant_id,))
                count = cur.fetchone()[0]
                logger.info(f"  现有组织记录数（租户ID={sync.tenant_id}）: {count}")
            
            cur.close()
            conn.close()
        except Exception as e:
            logger.error(f"数据库检查失败: {e}", exc_info=True)
        
        logger.info("\n" + "=" * 50)
        logger.info("调试完成！")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"调试过程出错: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='调试组织数据提取脚本')
    parser.add_argument(
        '--max-users',
        type=int,
        default=1000,
        help='最大处理用户数量（默认：1000）'
    )
    
    args = parser.parse_args()
    
    try:
        debug_organizations(max_users=args.max_users)
    except KeyboardInterrupt:
        logger.info("\n用户中断调试")
        sys.exit(1)
    except Exception as e:
        logger.error(f"程序执行失败: {e}", exc_info=True)
        sys.exit(1)

