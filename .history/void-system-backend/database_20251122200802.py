"""
Void System Database Module
----------------------------
提供数据库操作接口，包括用户、属性、任务、系统币等核心功能的数据管理。
"""

import sqlite3
import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any


class Database:
    def __init__(self, db_path: str = "void_system.db"):
        """
        初始化数据库连接
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)
    
    def init_database(self):
        """初始化数据库表结构"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 用户表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE,
            password_hash TEXT,
            nickname TEXT,
            level INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_login TEXT
        )
        ''')
        
        # 属性表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS attributes (
            attr_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            attr_name TEXT NOT NULL,
            attr_value INTEGER DEFAULT 0,
            max_value INTEGER DEFAULT 100,
            description TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
        ''')
        
        # 任务表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            task_name TEXT NOT NULL,
            description TEXT,
            related_attrs TEXT,  -- JSON格式存储关联的属性ID和权重
            estimated_time INTEGER,  -- 预计耗时（分钟）
            reward_coins INTEGER DEFAULT 10,
            status TEXT DEFAULT 'pending',  -- pending, in_progress, completed, failed
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            completed_at TEXT,
            proof_data TEXT,  -- 完成证明数据（JSON）
            self_evaluation TEXT,  -- 自评数据（JSON）
            ai_suggestion TEXT,  -- AI建议（JSON）
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
        ''')
        
        # 系统币记录表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS coins (
            record_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            amount INTEGER NOT NULL,
            type TEXT NOT NULL,  -- earn, spend, reward
            source TEXT,  -- 来源描述
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
        ''')
        
        # 用户资源表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_resources (
            resource_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            resource_type TEXT NOT NULL,  -- ai_qa, ai_advisor, material
            quantity INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
        ''')
        
        # 添加索引优化查询性能
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_attributes_user_id ON attributes(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_coins_user_id ON coins(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_resources_user_id ON user_resources(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_resources_type ON user_resources(resource_type)")
        
        conn.commit()
        conn.close()
    
    # ==================== 属性相关方法 ====================
    
    def add_attribute(
        self, 
        user_id: str, 
        attr_name: str, 
        max_value: int = 100, 
        description: str = ""
    ) -> str:
        """
        添加用户属性
        
        Args:
            user_id: 用户ID
            attr_name: 属性名称
            max_value: 最大值，默认100
            description: 属性描述
            
        Returns:
            新创建的属性ID
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        attr_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        try:
            cursor.execute(
                """INSERT INTO attributes 
                   (attr_id, user_id, attr_name, max_value, description, created_at, updated_at) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (attr_id, user_id, attr_name, max_value, description, now, now)
            )
            conn.commit()
            return attr_id
        finally:
            conn.close()
    
    def get_user_attributes(self, user_id: str) -> List[Dict[str, Any]]:
        """
        获取用户所有属性
        
        Args:
            user_id: 用户ID
            
        Returns:
            属性列表
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT * FROM attributes WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,)
            )
            attrs = cursor.fetchall()
            
            result = []
            for attr in attrs:
                result.append({
                    "attr_id": attr[0],
                    "user_id": attr[1],
                    "attr_name": attr[2],
                    "attr_value": attr[3],
                    "max_value": attr[4],
                    "description": attr[5],
                    "created_at": attr[6],
                    "updated_at": attr[7]
                })
            return result
        finally:
            conn.close()
    
    def update_attribute_value(self, attr_id: str, value: int) -> int:
        """
        更新属性值
        
        Args:
            attr_id: 属性ID
            value: 新的属性值
            
        Returns:
            更新后的属性值（不超过最大值）
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 先获取属性的最大值，确保不超过最大值
            cursor.execute(
                "SELECT max_value FROM attributes WHERE attr_id = ?", 
                (attr_id,)
            )
            max_value_result = cursor.fetchone()
            if max_value_result:
                value = min(value, max_value_result[0])
            
            cursor.execute(
                "UPDATE attributes SET attr_value = ?, updated_at = ? WHERE attr_id = ?",
                (value, datetime.now().isoformat(), attr_id)
            )
            conn.commit()
            return value
        finally:
            conn.close()
    
    def delete_attribute(self, attr_id: str, user_id: str) -> bool:
        """
        删除用户属性（确保只能删除自己的属性）
        
        Args:
            attr_id: 属性ID
            user_id: 用户ID
            
        Returns:
            是否删除成功
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "DELETE FROM attributes WHERE attr_id = ? AND user_id = ?",
                (attr_id, user_id)
            )
            affected = cursor.rowcount
            conn.commit()
            return affected > 0
        finally:
            conn.close()
    
    # ==================== 用户相关方法 ====================
    def add_user(self, username, email=None, password_hash=None, nickname=None):
        """添加新用户"""
        conn = self.get_connection()
        cursor = conn.cursor()
        user_id = str(uuid.uuid4())
        
        try:
            cursor.execute(
                "INSERT INTO users (user_id, username, email, password_hash, nickname) VALUES (?, ?, ?, ?, ?)",
                (user_id, username, email, password_hash, nickname or username)
            )
            conn.commit()
            return user_id
        except sqlite3.IntegrityError:
            return None  # 用户名或邮箱已存在
        finally:
            conn.close()
    
    def get_user_by_username(self, username):
        """通过用户名获取用户信息"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return {
                "user_id": user[0],
                "username": user[1],
                "email": user[2],
                "password_hash": user[3],
                "nickname": user[4],
                "level": user[5],
                "created_at": user[6],
                "last_login": user[7]
            }
        return None
    
    def update_last_login(self, user_id: str) -> None:
        """
        更新用户最后登录时间
        
        Args:
            user_id: 用户ID
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "UPDATE users SET last_login = ? WHERE user_id = ?",
                (datetime.now().isoformat(), user_id)
            )
            conn.commit()
        finally:
            conn.close()
    
    def update_user_level(self, user_id: str, level: int) -> bool:
        """
        更新用户等级
        
        Args:
            user_id: 用户ID
            level: 新等级
            
        Returns:
            是否更新成功
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "UPDATE users SET level = ? WHERE user_id = ?",
                (level, user_id)
            )
            conn.commit()
            return True
        finally:
            conn.close()
    
    # ==================== 系统币相关方法 ====================
    def add_coins(self, user_id: str, amount: int, source: str = "task_complete") -> bool:
        """
        增加用户系统币
        
        Args:
            user_id: 用户ID
            amount: 增加的金额
            source: 来源描述
            
        Returns:
            是否添加成功
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        record_id = str(uuid.uuid4())
        
        try:
            cursor.execute(
                """INSERT INTO coins (record_id, user_id, amount, type, source) 
                   VALUES (?, ?, ?, ?, ?)""",
                (record_id, user_id, amount, "earn", source)
            )
            conn.commit()
            return True
        finally:
            conn.close()
    
    def spend_coins(self, user_id: str, amount: int, source: str = "resource_exchange") -> bool:
        """
        扣除用户系统币
        
        Args:
            user_id: 用户ID
            amount: 扣除的金额
            source: 来源描述
            
        Returns:
            是否扣除成功（余额不足时返回False）
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 先检查余额是否足够
            balance = self.get_user_balance(user_id)
            if balance < amount:
                return False
            
            record_id = str(uuid.uuid4())
            cursor.execute(
                """INSERT INTO coins (record_id, user_id, amount, type, source) 
                   VALUES (?, ?, ?, ?, ?)""",
                (record_id, user_id, -amount, "spend", source)
            )
            conn.commit()
            return True
        finally:
            conn.close()
    
    def get_user_balance(self, user_id: str) -> int:
        """
        获取用户系统币余额
        
        Args:
            user_id: 用户ID
            
        Returns:
            用户余额（如果没有记录则返回0）
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT SUM(amount) FROM coins WHERE user_id = ?",
                (user_id,)
            )
            balance = cursor.fetchone()[0]
            return balance or 0
        finally:
            conn.close()
    
    def get_coin_history(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取用户系统币收支记录
        
        Args:
            user_id: 用户ID
            limit: 返回记录数量限制
            
        Returns:
            系统币记录列表
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """SELECT * FROM coins WHERE user_id = ? 
                   ORDER BY created_at DESC LIMIT ?""",
                (user_id, limit)
            )
            records = cursor.fetchall()
            
            result = []
            for record in records:
                result.append({
                    "record_id": record[0],
                    "user_id": record[1],
                    "amount": record[2],
                    "type": record[3],
                    "source": record[4],
                    "created_at": record[5]
                })
            return result
        finally:
            conn.close()
    
    # ==================== 用户资源相关方法 ====================
    def add_user_resource(
        self, 
        user_id: str, 
        resource_type: str, 
        quantity: int = 1
    ) -> bool:
        """
        增加用户资源数量
        
        Args:
            user_id: 用户ID
            resource_type: 资源类型
            quantity: 增加的数量
            
        Returns:
            是否添加成功
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 检查资源是否已存在
            cursor.execute(
                """SELECT resource_id, quantity FROM user_resources 
                   WHERE user_id = ? AND resource_type = ?""",
                (user_id, resource_type)
            )
            result = cursor.fetchone()
            
            if result:
                # 已存在，更新数量
                new_quantity = result[1] + quantity
                cursor.execute(
                    "UPDATE user_resources SET quantity = ? WHERE resource_id = ?",
                    (new_quantity, result[0])
                )
            else:
                # 不存在，创建新记录
                resource_id = str(uuid.uuid4())
                cursor.execute(
                    """INSERT INTO user_resources 
                       (resource_id, user_id, resource_type, quantity) 
                       VALUES (?, ?, ?, ?)""",
                    (resource_id, user_id, resource_type, quantity)
                )
            
            conn.commit()
            return True
        finally:
            conn.close()
    
    def spend_user_resource(
        self, 
        user_id: str, 
        resource_type: str, 
        quantity: int = 1
    ) -> bool:
        """
        使用用户资源
        
        Args:
            user_id: 用户ID
            resource_type: 资源类型
            quantity: 使用的数量
            
        Returns:
            是否使用成功（资源不足时返回False）
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 检查资源是否足够
            cursor.execute(
                """SELECT resource_id, quantity FROM user_resources 
                   WHERE user_id = ? AND resource_type = ?""",
                (user_id, resource_type)
            )
            result = cursor.fetchone()
            
            if not result or result[1] < quantity:
                return False
            
            # 更新数量
            new_quantity = result[1] - quantity
            cursor.execute(
                "UPDATE user_resources SET quantity = ? WHERE resource_id = ?",
                (new_quantity, result[0])
            )
            
            conn.commit()
            return True
        finally:
            conn.close()
    
    def get_user_resources(self, user_id: str) -> Dict[str, int]:
        """
        获取用户资源列表
        
        Args:
            user_id: 用户ID
            
        Returns:
            资源类型和数量的字典
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT resource_type, quantity FROM user_resources WHERE user_id = ?",
                (user_id,)
            )
            resources = cursor.fetchall()
            
            result = {}
            for resource in resources:
                result[resource[0]] = resource[1]
            return result
        finally:
            conn.close()
    
    # ==================== 任务相关方法 ====================
    def create_task(
        self, 
        user_id: str, 
        task_name: str, 
        description: str = "", 
        related_attrs: Optional[Dict[str, Any]] = None, 
        estimated_time: int = 30, 
        reward_coins: int = 10
    ) -> str:
        """
        创建新任务
        
        Args:
            user_id: 用户ID
            task_name: 任务名称
            description: 任务描述
            related_attrs: 关联的属性字典（属性ID: 权重）
            estimated_time: 预计耗时（分钟）
            reward_coins: 奖励系统币数量
            
        Returns:
            新创建的任务ID
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        task_id = str(uuid.uuid4())
        
        # 将关联属性转换为JSON字符串
        related_attrs_json = json.dumps(related_attrs or {})
        
        try:
            cursor.execute(
                """INSERT INTO tasks 
                   (task_id, user_id, task_name, description, related_attrs, estimated_time, reward_coins) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (task_id, user_id, task_name, description, related_attrs_json, estimated_time, reward_coins)
            )
            conn.commit()
            return task_id
        finally:
            conn.close()
    
    def get_user_tasks(
        self, 
        user_id: str, 
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取用户任务列表
        
        Args:
            user_id: 用户ID
            status: 任务状态筛选（可选）
            
        Returns:
            任务列表
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if status:
                cursor.execute(
                    """SELECT * FROM tasks 
                       WHERE user_id = ? AND status = ? 
                       ORDER BY created_at DESC""",
                    (user_id, status)
                )
            else:
                cursor.execute(
                    """SELECT * FROM tasks 
                       WHERE user_id = ? 
                       ORDER BY created_at DESC""",
                    (user_id,)
                )
            
            tasks = cursor.fetchall()
            
            result = []
            for task in tasks:
                task_dict = {
                    "task_id": task[0],
                    "user_id": task[1],
                    "task_name": task[2],
                    "description": task[3],
                    "related_attrs": json.loads(task[4] or "{}"),
                    "estimated_time": task[5],
                    "reward_coins": task[6],
                    "status": task[7],
                    "created_at": task[8],
                    "completed_at": task[9],
                    "proof_data": json.loads(task[10] or "{}"),
                    "self_evaluation": json.loads(task[11] or "{}"),
                    "ai_suggestion": json.loads(task[12] or "{}")
                }
                result.append(task_dict)
            return result
        finally:
            conn.close()
    
    def update_task_status(self, task_id: str, user_id: str, status: str) -> bool:
        """
        更新任务状态
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            status: 新状态
            
        Returns:
            是否更新成功
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 如果状态是完成，记录完成时间
            if status == 'completed':
                cursor.execute(
                    """UPDATE tasks SET status = ?, completed_at = ? 
                       WHERE task_id = ? AND user_id = ?""",
                    (status, datetime.now().isoformat(), task_id, user_id)
                )
            else:
                cursor.execute(
                    "UPDATE tasks SET status = ? WHERE task_id = ? AND user_id = ?",
                    (status, task_id, user_id)
                )
            
            affected = cursor.rowcount
            conn.commit()
            return affected > 0
        finally:
            conn.close()
    
    def submit_task_proof(
        self, 
        task_id: str, 
        user_id: str, 
        proof_data: Dict[str, Any]
    ) -> bool:
        """
        提交任务完成证明
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            proof_data: 证明数据字典
            
        Returns:
            是否提交成功
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "UPDATE tasks SET proof_data = ? WHERE task_id = ? AND user_id = ?",
                (json.dumps(proof_data), task_id, user_id)
            )
            affected = cursor.rowcount
            conn.commit()
            return affected > 0
        finally:
            conn.close()
    
    def update_task_evaluation(
        self, 
        task_id: str, 
        user_id: str, 
        self_evaluation: Optional[Dict[str, Any]] = None, 
        ai_suggestion: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        更新任务自评和AI建议
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            self_evaluation: 自评数据（可选）
            ai_suggestion: AI建议（可选）
            
        Returns:
            是否更新成功
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 先获取现有数据
            cursor.execute(
                """SELECT self_evaluation, ai_suggestion FROM tasks 
                   WHERE task_id = ? AND user_id = ?""",
                (task_id, user_id)
            )
            result = cursor.fetchone()
            if not result:
                return False
            
            current_self_eval = json.loads(result[0] or "{}")
            current_ai_suggest = json.loads(result[1] or "{}")
            
            # 更新数据
            if self_evaluation:
                current_self_eval.update(self_evaluation)
            if ai_suggestion:
                current_ai_suggest.update(ai_suggestion)
            
            cursor.execute(
                """UPDATE tasks SET self_evaluation = ?, ai_suggestion = ? 
                   WHERE task_id = ? AND user_id = ?""",
                (json.dumps(current_self_eval), json.dumps(current_ai_suggest), task_id, user_id)
            )
            
            conn.commit()
            return True
        finally:
            conn.close()