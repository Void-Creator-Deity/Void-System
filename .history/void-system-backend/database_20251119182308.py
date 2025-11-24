import sqlite3
import json
import uuid
from datetime import datetime

class Database:
    import sqlite3
import json
import uuid
from datetime import datetime

class Database:
    def __init__(self, db_path="void_system.db"):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
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
            estimated_time INTEGER,  # 预计耗时（分钟）
            reward_coins INTEGER DEFAULT 10,
            status TEXT DEFAULT 'pending',  # pending, in_progress, completed, failed
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            completed_at TEXT,
            proof_data TEXT,  # 完成证明数据（JSON）
            self_evaluation TEXT,  # 自评数据（JSON）
            ai_suggestion TEXT,  # AI建议（JSON）
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
        ''')
        
        # 系统币记录表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS coins (
            record_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            amount INTEGER NOT NULL,
            type TEXT NOT NULL,  # earn, spend, reward
            source TEXT,  # 来源描述
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
        ''')
        
        # 用户资源表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_resources (
            resource_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            resource_type TEXT NOT NULL,  # ai_qa, ai_advisor, material
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
    
    # 属性相关方法
    def add_attribute(self, user_id, attr_name, max_value=100, description=""):
        """添加用户属性"""
        conn = self.get_connection()
        cursor = conn.cursor()
        attr_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        cursor.execute(
            "INSERT INTO attributes (attr_id, user_id, attr_name, max_value, description, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (attr_id, user_id, attr_name, max_value, description, now, now)
        )
        conn.commit()
        conn.close()
        return attr_id
    
    def get_user_attributes(self, user_id):
        """获取用户所有属性"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM attributes WHERE user_id = ?", (user_id,))
        attrs = cursor.fetchall()
        conn.close()
        
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
    
    def update_attribute_value(self, attr_id, value):
        """更新属性值"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 先获取属性的最大值，确保不超过最大值
        cursor.execute("SELECT max_value FROM attributes WHERE attr_id = ?", (attr_id,))
        max_value = cursor.fetchone()
        if max_value:
            value = min(value, max_value[0])
        
        cursor.execute(
            "UPDATE attributes SET attr_value = ?, updated_at = ? WHERE attr_id = ?",
            (value, datetime.now().isoformat(), attr_id)
        )
        conn.commit()
        conn.close()
        return value
    
    def delete_attribute(self, attr_id, user_id):
        """删除用户属性（确保只能删除自己的属性）"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM attributes WHERE attr_id = ? AND user_id = ?",
            (attr_id, user_id)
        )
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        return affected > 0
    
    # 用户相关方法
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
    
    def update_last_login(self, user_id):
        """更新用户最后登录时间"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET last_login = ? WHERE user_id = ?",
            (datetime.now().isoformat(), user_id)
        )
        conn.commit()
        conn.close()
    
    def update_user_level(self, user_id, level):
        """更新用户等级"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET level = ? WHERE user_id = ?",
            (level, user_id)
        )
        conn.commit()
        conn.close()
        return True
    
    # 系统币相关方法
    def add_coins(self, user_id, amount, source="task_complete"):
        """增加用户系统币"""
        conn = self.get_connection()
        cursor = conn.cursor()
        record_id = str(uuid.uuid4())
        
        cursor.execute(
            "INSERT INTO coins (record_id, user_id, amount, type, source) VALUES (?, ?, ?, ?, ?)",
            (record_id, user_id, amount, "earn", source)
        )
        conn.commit()
        conn.close()
        return True
    
    def spend_coins(self, user_id, amount, source="resource_exchange"):
        """扣除用户系统币"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 先检查余额是否足够
        balance = self.get_user_balance(user_id)
        if balance < amount:
            conn.close()
            return False
        
        record_id = str(uuid.uuid4())
        cursor.execute(
            "INSERT INTO coins (record_id, user_id, amount, type, source) VALUES (?, ?, ?, ?, ?)",
            (record_id, user_id, -amount, "spend", source)
        )
        conn.commit()
        conn.close()
        return True
    
    def get_user_balance(self, user_id):
        """获取用户系统币余额"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT SUM(amount) FROM coins WHERE user_id = ?",
            (user_id,)
        )
        balance = cursor.fetchone()[0]
        conn.close()
        return balance or 0
    
    def get_coin_history(self, user_id, limit=50):
        """获取用户系统币收支记录"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM coins WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit)
        )
        records = cursor.fetchall()
        conn.close()
        
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
    
    # 用户资源相关方法
    def add_user_resource(self, user_id, resource_type, quantity=1):
        """增加用户资源数量"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 检查资源是否已存在
        cursor.execute(
            "SELECT resource_id, quantity FROM user_resources WHERE user_id = ? AND resource_type = ?",
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
                "INSERT INTO user_resources (resource_id, user_id, resource_type, quantity) VALUES (?, ?, ?, ?)",
                (resource_id, user_id, resource_type, quantity)
            )
        
        conn.commit()
        conn.close()
        return True
    
    def spend_user_resource(self, user_id, resource_type, quantity=1):
        """使用用户资源"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 检查资源是否足够
        cursor.execute(
            "SELECT resource_id, quantity FROM user_resources WHERE user_id = ? AND resource_type = ?",
            (user_id, resource_type)
        )
        result = cursor.fetchone()
        
        if not result or result[1] < quantity:
            conn.close()
            return False
        
        # 更新数量
        new_quantity = result[1] - quantity
        cursor.execute(
            "UPDATE user_resources SET quantity = ? WHERE resource_id = ?",
            (new_quantity, result[0])
        )
        
        conn.commit()
        conn.close()
        return True
    
    def get_user_resources(self, user_id):
        """获取用户资源列表"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT resource_type, quantity FROM user_resources WHERE user_id = ?",
            (user_id,)
        )
        resources = cursor.fetchall()
        conn.close()
        
        result = {}
        for resource in resources:
            result[resource[0]] = resource[1]
        return result
    
    # 任务相关方法
    def create_task(self, user_id, task_name, description="", related_attrs=None, estimated_time=30, reward_coins=10):
        """创建新任务"""
        conn = self.get_connection()
        cursor = conn.cursor()
        task_id = str(uuid.uuid4())
        
        # 将关联属性转换为JSON字符串
        related_attrs_json = json.dumps(related_attrs or {})
        
        cursor.execute(
            "INSERT INTO tasks (task_id, user_id, task_name, description, related_attrs, estimated_time, reward_coins) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (task_id, user_id, task_name, description, related_attrs_json, estimated_time, reward_coins)
        )
        conn.commit()
        conn.close()
        return task_id
    
    def get_user_tasks(self, user_id, status=None):
        """获取用户任务列表"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if status:
            cursor.execute("SELECT * FROM tasks WHERE user_id = ? AND status = ? ORDER BY created_at DESC", (user_id, status))
        else:
            cursor.execute("SELECT * FROM tasks WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
        
        tasks = cursor.fetchall()
        conn.close()
        
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
    
    def update_task_status(self, task_id, user_id, status):
        """更新任务状态"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        params = [status, task_id, user_id]
        query = "UPDATE tasks SET status = ? WHERE task_id = ? AND user_id = ?"
        
        # 如果状态是完成，记录完成时间
        if status == 'completed':
            query = "UPDATE tasks SET status = ?, completed_at = ? WHERE task_id = ? AND user_id = ?"
            params = [status, datetime.now().isoformat(), task_id, user_id]
        
        cursor.execute(query, params)
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        return affected > 0
    
    def submit_task_proof(self, task_id, user_id, proof_data):
        """提交任务完成证明"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE tasks SET proof_data = ? WHERE task_id = ? AND user_id = ?",
            (json.dumps(proof_data), task_id, user_id)
        )
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        return affected > 0
    
    def update_task_evaluation(self, task_id, user_id, self_evaluation=None, ai_suggestion=None):
        """更新任务自评和AI建议"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 先获取现有数据
        cursor.execute("SELECT self_evaluation, ai_suggestion FROM tasks WHERE task_id = ? AND user_id = ?", (task_id, user_id))
        result = cursor.fetchone()
        if not result:
            conn.close()
            return False
        
        current_self_eval = json.loads(result[0] or "{}")
        current_ai_suggest = json.loads(result[1] or "{}")
        
        # 更新数据
        if self_evaluation:
            current_self_eval.update(self_evaluation)
        if ai_suggestion:
            current_ai_suggest.update(ai_suggestion)
        
        cursor.execute(
            "UPDATE tasks SET self_evaluation = ?, ai_suggestion = ? WHERE task_id = ? AND user_id = ?",
            (json.dumps(current_self_eval), json.dumps(current_ai_suggest), task_id, user_id)
        )
        
        conn.commit()
        conn.close()
        return True
    
    # 用户相关方法
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
    
    def update_last_login(self, user_id):
        """更新用户最后登录时间"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET last_login = ? WHERE user_id = ?",
            (datetime.now().isoformat(), user_id)
        )
        conn.commit()
        conn.close()
    
    def update_user_level(self, user_id, level):
        """更新用户等级"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET level = ? WHERE user_id = ?",
            (level, user_id)
        )
        conn.commit()
        conn.close()