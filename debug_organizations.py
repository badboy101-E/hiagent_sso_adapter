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
from sync_org_from_idc import OrgSyncFromIDC, get_attr

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


def debug_organizations():
    """调试组织数据提取"""
    logger.info("=" * 50)
    logger.info("开始调试组织数据提取")
    logger.info("=" * 50)
    
    try:
        sync = OrgSyncFromIDC()
        
        # 1. 获取用户数据
        logger.info("\n[步骤1] 获取用户数据...")
        users = sync.get_all_users_from_idc()
        logger.info(f"获取到 {len(users)} 个用户")
        
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
        
        logger.info(f"\n统计（前10个用户）:")
        logger.info(f"  有组织信息的用户: {users_with_org}")
        logger.info(f"  无组织信息的用户: {users_without_org}")
        
        # 3. 提取组织信息
        logger.info("\n[步骤3] 提取组织信息...")
        organizations = sync.get_organizations_from_idc()
        logger.info(f"提取到 {len(organizations)} 个组织")
        
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
    try:
        debug_organizations()
    except KeyboardInterrupt:
        logger.info("\n用户中断调试")
        sys.exit(1)
    except Exception as e:
        logger.error(f"程序执行失败: {e}", exc_info=True)
        sys.exit(1)

