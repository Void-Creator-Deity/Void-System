# 检查任务表中的用户ID关联情况

import sqlite3
import json

db_path = 'void_system.db'

print("检查任务表中的用户ID关联情况...")

# 连接数据库
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# 获取所有任务
cursor.execute("SELECT task_id, user_id, task_name FROM tasks")
tasks = cursor.fetchall()

print(f"\n总任务数: {len(tasks)}")

# 统计每个用户的任务数量
user_task_count = {}
for task in tasks:
    user_id = task['user_id']
    if user_id in user_task_count:
        user_task_count[user_id] += 1
    else:
        user_task_count[user_id] = 1

print("\n每个用户的任务数量:")
for user_id, count in user_task_count.items():
    print(f"用户 {user_id}: {count} 个任务")

# 获取所有用户
cursor.execute("SELECT user_id, username FROM users")
users = cursor.fetchall()

print("\n系统中的用户:")
for user in users:
    print(f"ID: {user['user_id']}, 用户名: {user['username']}")

# 检查是否有任务没有关联用户ID
cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id IS NULL OR user_id = ''")
null_user_tasks = cursor.fetchone()[0]

print(f"\n没有关联用户ID的任务数: {null_user_tasks}")

# 检查是否有重复的任务ID
cursor.execute("SELECT task_id, COUNT(*) FROM tasks GROUP BY task_id HAVING COUNT(*) > 1")
duplicate_tasks = cursor.fetchall()

print(f"\n重复的任务ID数量: {len(duplicate_tasks)}")

# 关闭数据库连接
conn.close()

print("\n检查完成！")
