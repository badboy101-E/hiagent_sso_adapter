#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本：仅获取1000个用户进行同步测试
用于验证同步功能是否正常工作
"""

import os
import sys
import logging
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 导入主同步脚本的类和函数
try:
    from sync_org_from_idc import OrgSyncFromIDC, get_attr, get_value
except ImportError:
    # 如果导入失败，尝试添加当前目录到路径
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from sync_org_from_idc import OrgSyncFromIDC, get_attr, get_value

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_sync_1000.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class TestSync1000Users(OrgSyncFromIDC):
    """测试类：仅同步1000个用户"""
    
    def __init__(self, max_users=1000):
        """初始化，设置最大用户数"""
        super().__init__()
        self.max_users = max_users
        logger.info(f"测试模式：最多同步 {self.max_users} 个用户")
    
    def get_all_users_from_idc(self):
        """
        重写父类方法，限制获取的用户数量
        """
        users = []
        page_size = 100  # 每页大小
        current_page = 0
        
        logger.info(f"开始从身份中台获取用户信息（限制：{self.max_users}个）...")
        
        # 方案1: 尝试不传 sourceUserId，直接分页获取所有用户
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
                
                logger.info(f"已获取 {len(users)}/{min(self.max_users, total_count)} 个用户（第 {current_page + 1} 页，本页 {len(page_users)} 条）...")
                
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
    
    def run(self):
        """执行测试同步流程"""
        logger.info("=" * 50)
        logger.info(f"开始测试同步（限制：{self.max_users}个用户）")
        logger.info("=" * 50)
        
        try:
            # 1. 获取用户信息（限制数量）
            logger.info(f"\n[1/5] 从身份中台获取用户信息（最多{self.max_users}个）...")
            users = self.get_all_users_from_idc()
            
            if not users:
                logger.error("未获取到任何用户数据，测试终止")
                return
            
            logger.info(f"实际获取到 {len(users)} 个用户")
            
            # 2. 同步用户
            logger.info("\n[2/5] 同步用户到临时表...")
            self.sync_users(users)
            active_user_ids = [str(get_attr(u, 'sourceUserId') or get_attr(u, 'userId') or get_attr(u, 'id') or '') 
                             for u in users if get_attr(u, 'sourceUserId') or get_attr(u, 'userId') or get_attr(u, 'id')]
            
            # 3. 获取组织架构信息
            logger.info("\n[3/5] 从用户信息中提取组织架构信息...")
            organizations = self.get_organizations_from_idc()
            
            # 4. 同步组织
            logger.info("\n[4/5] 同步组织到临时表...")
            self.sync_organizations(organizations)
            active_org_ids = [str(get_attr(o, 'id', '') or '') for o in organizations if get_attr(o, 'id')]
            
            # 5. 同步用户-组织关系
            logger.info("\n[5/5] 同步用户-组织关系到临时表...")
            self.sync_user_org_relations(users)
            
            # 注意：测试模式下不标记删除，避免影响现有数据
            logger.info("\n[测试模式] 跳过标记已删除的用户和组织（避免影响现有数据）")
            
            logger.info("\n" + "=" * 50)
            logger.info("测试同步完成!")
            logger.info(f"统计信息:")
            logger.info(f"  - 用户数量: {len(users)}")
            logger.info(f"  - 组织数量: {len(organizations)}")
            logger.info(f"  - 用户-组织关系: 已同步")
            logger.info("=" * 50)
            
        except Exception as e:
            logger.error(f"测试同步过程出错: {e}", exc_info=True)
            raise


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='测试同步脚本：仅同步指定数量的用户')
    parser.add_argument(
        '--max-users',
        type=int,
        default=1000,
        help='最大同步用户数量（默认：1000）'
    )
    
    args = parser.parse_args()
    
    try:
        sync = TestSync1000Users(max_users=args.max_users)
        sync.run()
    except KeyboardInterrupt:
        logger.info("\n用户中断测试")
        sys.exit(1)
    except Exception as e:
        logger.error(f"程序执行失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

