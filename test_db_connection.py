#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试数据库连接脚本
"""

import os
import sys
from dotenv import load_dotenv
import psycopg2

# 加载环境变量
load_dotenv()

def test_connection():
    """测试数据库连接"""
    db_config = {
        "host": os.getenv('TMP_DB_HOST', 'localhost'),
        "port": int(os.getenv('TMP_DB_PORT', '5432')),
        "database": os.getenv('TMP_DB_NAME', 'postgres'),
        "user": os.getenv('TMP_DB_USER', 'pguser'),
        "password": os.getenv('TMP_DB_PASSWORD', '')
    }
    
    print("=" * 50)
    print("测试数据库连接")
    print("=" * 50)
    print(f"主机: {db_config['host']}")
    print(f"端口: {db_config['port']}")
    print(f"数据库: {db_config['database']}")
    print(f"用户: {db_config['user']}")
    print("=" * 50)
    
    try:
        conn = psycopg2.connect(**db_config)
        print("✓ 数据库连接成功！")
        
        # 检查临时表是否存在
        cur = conn.cursor()
        tables = ['tmp_user', 'tmp_organization', 'tmp_org_user_relation']
        
        print("\n检查临时表:")
        for table in tables:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = %s
                );
            """, (table,))
            exists = cur.fetchone()[0]
            if exists:
                # 获取表记录数
                cur.execute(f"SELECT COUNT(*) FROM {table};")
                count = cur.fetchone()[0]
                print(f"  ✓ {table} - 存在 (记录数: {count})")
            else:
                print(f"  ✗ {table} - 不存在")
        
        cur.close()
        conn.close()
        print("\n✓ 测试完成！")
        return True
        
    except psycopg2.OperationalError as e:
        print(f"✗ 数据库连接失败: {e}")
        print("\n请检查:")
        print("1. 数据库服务器是否可访问")
        print("2. 用户名和密码是否正确")
        print("3. 数据库名称是否正确")
        print("4. 网络连接是否正常")
        return False
    except Exception as e:
        print(f"✗ 发生错误: {e}")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)

