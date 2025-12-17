#!/usr/bin/env python3
"""创建测试用户"""

import sys
import os

# 添加父目录到Python路径
parent_dir = os.path.dirname(os.path.dirname(__file__))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from database import Database
from config import config
from services.user_service import UserService

def main():
    db = Database(config.get_database_path())
    user_service = UserService(db)

    try:
        # 创建测试用户
        result = user_service.register_user(
            username="test",
            password="test123",
            nickname="测试用户"
        )
        print("✅ 测试用户创建成功!")
        print(f"用户名: {result['username']}")
        print(f"昵称: {result['nickname']}")
        print(f"用户ID: {result['user_id']}")

    except Exception as e:
        print(f"❌ 创建用户失败: {e}")

if __name__ == "__main__":
    main()
