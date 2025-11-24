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
            related_attrs TEXT,  # JSON格式存储关联的属性ID和权重
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