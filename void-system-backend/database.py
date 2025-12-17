"""
Void System Database Module
----------------------------
提供数据库操作接口，包括用户、属性、任务、系统币等核心功能的数据管理。
"""
import sqlite3
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import logging

logger: logging.Logger = logging.getLogger("void-system-db")

class Database:
    def __init__(self, db_path: str = "void_system.db") -> None:
        """
        初始化数据库连接
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 返回字典格式
        return conn
    
    def test_connection(self) -> None:
        """测试数据库连接"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
    
    def close(self) -> None:
        """关闭数据库连接（如果需要）"""
        pass  # SQLite会自动管理连接
    
    def init_database(self) -> None:
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
            experience INTEGER DEFAULT 0,
            role TEXT DEFAULT 'user',  -- 新增角色字段：user/admin/editor
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
            icon TEXT DEFAULT '📊',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
        ''')
        
        # 任务类别表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS task_categories (
            category_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            category_name TEXT NOT NULL,
            description TEXT,
            icon TEXT DEFAULT '📚',
            color TEXT DEFAULT '#3B82F6',
            is_preset INTEGER DEFAULT 0,
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
            category_id TEXT,
            task_name TEXT NOT NULL,
            description TEXT,
            related_attrs TEXT,
            estimated_time INTEGER,
            reward_coins INTEGER DEFAULT 10,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            completed_at TEXT,
            proof_data TEXT,
            self_evaluation TEXT,
            ai_suggestion TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (category_id) REFERENCES task_categories(category_id) ON DELETE SET NULL
        )
        ''')
        
        # 系统币记录表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS coins (
            record_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            amount INTEGER NOT NULL,
            type TEXT NOT NULL,
            source TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
        ''')
        
        # 用户资源表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_resources (
            resource_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            resource_key TEXT NOT NULL,
            quantity INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
        ''')
        
        # 购买记录表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS purchase_history (
            purchase_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            item_id TEXT NOT NULL,
            item_name TEXT NOT NULL,
            quantity INTEGER DEFAULT 1,
            unit_price INTEGER NOT NULL,
            total_price INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
        ''')
        
        # 经验值记录表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS experience (
            record_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            amount INTEGER NOT NULL,
            source TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
        ''')
        
        # 系统RAG文档表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_rag_documents (
            id VARCHAR(36) PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            file_name VARCHAR(255),
            file_type VARCHAR(10),
            file_size INTEGER,
            chroma_ids TEXT,  -- 存储Chroma中的向量ID列表
            uploaded_by VARCHAR(36),  -- 管理员ID
            upload_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            tags JSON,  -- 标签数组
            description TEXT,
            version INTEGER DEFAULT 1
        )
        ''')
        
        # 用户会话临时文件表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_session_files (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL,
            session_id VARCHAR(36) NOT NULL,
            file_name VARCHAR(255),
            content_preview TEXT,  -- 仅存储前500字符
            original_size INTEGER,
            upload_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            expires_at DATETIME,  -- 24小时后过期
            is_processed BOOLEAN DEFAULT FALSE
        )
        ''')

        # 用户文档表 - DeepSeek风格文档管理
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_documents (
            doc_id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL,
            title VARCHAR(255) NOT NULL,
            original_name VARCHAR(255),
            file_type VARCHAR(10),
            file_size INTEGER,
            storage_path TEXT,
            parse_status TEXT DEFAULT 'pending',
            vector_collection TEXT,  -- 用户专属向量集合名
            chroma_ids TEXT,         -- Chroma向量ID列表(JSON)
            content_preview TEXT,
            tags JSON,
            error_message TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
        ''')

        # 文档版本表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_document_versions (
            version_id VARCHAR(36) PRIMARY KEY,
            doc_id VARCHAR(36) NOT NULL,
            version_number INTEGER DEFAULT 1,
            file_path TEXT,
            changes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (doc_id) REFERENCES user_documents(doc_id) ON DELETE CASCADE
        )
        ''')
        
        # 添加用户会话临时文件表索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_session ON user_session_files(user_id, session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_expires ON user_session_files(expires_at)')
        
        # 添加索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_attributes_user_id ON attributes(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_category ON tasks(category_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_coins_user_id ON coins(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_resources_user_id ON user_resources(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_categories_user_id ON task_categories(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_purchase_user_id ON purchase_history(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_experience_user_id ON experience(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_system_rag_documents_uploaded_by ON system_rag_documents(uploaded_by)")

        # 用户文档相关索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_documents_user_id ON user_documents(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_documents_status ON user_documents(parse_status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_documents_created ON user_documents(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_document_versions_doc_id ON user_document_versions(doc_id)")
        
        conn.commit()
        conn.close()
    
    # ==================== 用户相关方法 ====================
    def add_user(
        self,
        username: str,
        email: Optional[str] = None,
        password_hash: Optional[str] = None,
        nickname: Optional[str] = None
    ) -> Optional[str]:
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
        except sqlite3.IntegrityError as e:
            logger.error(f"添加用户失败: {e}")
            return None
        finally:
            conn.close()
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """通过用户名获取用户信息"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        finally:
            conn.close()
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """通过邮箱获取用户信息"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        finally:
            conn.close()
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """通过用户ID获取用户信息"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        finally:
            conn.close()
    
    def update_last_login(self, user_id: str) -> None:
        """更新用户最后登录时间"""
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
    
    def update_user_info(self, user_id: str, nickname: Optional[str] = None, 
                        email: Optional[str] = None) -> bool:
        """更新用户信息"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            updates: List[str] = []
            params: List[Any] = []
            
            if nickname is not None:
                updates.append("nickname = ?")
                params.append(nickname)
            
            if email is not None:
                updates.append("email = ?")
                params.append(email)
            
            if not updates:
                return False
            
            params.append(user_id)
            query = f"UPDATE users SET {', '.join(updates)} WHERE user_id = ?"
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def update_user_profile(self, user_id: str, nickname: Optional[str] = None, 
                           email: Optional[str] = None) -> bool:
        """更新用户资料（别名方法，与update_user_info相同）"""
        return self.update_user_info(user_id, nickname, email)
    
    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """获取用户统计信息"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # 获取总任务数
            cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ?", (user_id,))
            total_tasks = cursor.fetchone()[0]
            
            # 获取已完成任务数
            cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = 'completed'", (user_id,))
            completed_tasks = cursor.fetchone()[0]
            
            # 获取进行中任务数
            cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = 'in_progress'", (user_id,))
            in_progress_tasks = cursor.fetchone()[0]
            
            # 获取总经验值
            cursor.execute("SELECT SUM(amount) FROM experience WHERE user_id = ?", (user_id,))
            total_exp = cursor.fetchone()[0] or 0
            
            # 获取总获得金币
            cursor.execute("SELECT SUM(amount) FROM coins WHERE user_id = ? AND amount > 0", (user_id,))
            total_earned_coins = cursor.fetchone()[0] or 0
            
            # 获取总消费金币
            cursor.execute("SELECT ABS(SUM(amount)) FROM coins WHERE user_id = ? AND amount < 0", (user_id,))
            total_spent_coins = cursor.fetchone()[0] or 0
            
            return {
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "in_progress_tasks": in_progress_tasks,
                "completion_rate": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
                "total_experience": total_exp,
                "total_earned_coins": total_earned_coins,
                "total_spent_coins": total_spent_coins
            }
        finally:
            conn.close()
    
    # ==================== 属性相关方法 ====================
    def add_attribute(
        self,
        user_id: str,
        attr_name: str,
        max_value: int = 100,
        description: str = "",
        icon: str = "📊"
    ) -> str:
        """
        添加用户属性
        Args:
            user_id: 用户ID
            attr_name: 属性名称
            max_value: 最大值，默认100
            description: 属性描述
            icon: 属性图标
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
                   (attr_id, user_id, attr_name, max_value, description, icon, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (attr_id, user_id, attr_name, max_value, description, icon, now, now)
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
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
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
    
    def update_attribute(self, attr_id: str, attr_value: Optional[int] = None, 
                        description: Optional[str] = None, max_value: Optional[int] = None) -> bool:
        """更新属性信息"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            updates: List[str] = []
            params: List[Any] = []
            
            if attr_value is not None:
                updates.append("attr_value = ?")
                params.append(attr_value)
            
            if description is not None:
                updates.append("description = ?")
                params.append(description)
            
            if max_value is not None:
                updates.append("max_value = ?")
                params.append(max_value)
            
            if not updates:
                return False
            
            updates.append("updated_at = ?")
            params.append(datetime.now().isoformat())
            params.append(attr_id)
            
            query = f"UPDATE attributes SET {', '.join(updates)} WHERE attr_id = ?"
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def delete_attribute(self, attr_id: str) -> bool:
        """删除属性"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM attributes WHERE attr_id = ?", (attr_id,))
            conn.commit()
            return cursor.rowcount > 0
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
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
    
    def get_income_expense_stats(self, user_id: str) -> Dict[str, Any]:
        """获取用户收支统计"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # 总收入
            cursor.execute("SELECT SUM(amount) FROM coins WHERE user_id = ? AND amount > 0", (user_id,))
            total_income = cursor.fetchone()[0] or 0
            
            # 总支出
            cursor.execute("SELECT ABS(SUM(amount)) FROM coins WHERE user_id = ? AND amount < 0", (user_id,))
            total_expense = cursor.fetchone()[0] or 0
            
            # 最近7天收入
            cursor.execute("""
                SELECT SUM(amount) FROM coins 
                WHERE user_id = ? AND amount > 0 
                AND created_at >= date('now', '-7 days')
            """, (user_id,))
            weekly_income = cursor.fetchone()[0] or 0
            
            # 最近7天支出
            cursor.execute("""
                SELECT ABS(SUM(amount)) FROM coins 
                WHERE user_id = ? AND amount < 0 
                AND created_at >= date('now', '-7 days')
            """, (user_id,))
            weekly_expense = cursor.fetchone()[0] or 0
            
            return {
                "total_income": total_income,
                "total_expense": total_expense,
                "weekly_income": weekly_income,
                "weekly_expense": weekly_expense,
                "net_income": total_income - total_expense
            }
        finally:
            conn.close()
    
    # ==================== 经验值相关方法 ====================
    def add_experience(self, user_id: str, amount: int, source: str = "task_complete") -> bool:
        """增加用户经验值"""
        conn = self.get_connection()
        cursor = conn.cursor()
        record_id = str(uuid.uuid4())
        try:
            # 添加经验记录
            cursor.execute(
                """INSERT INTO experience (record_id, user_id, amount, source)
                   VALUES (?, ?, ?, ?)""",
                (record_id, user_id, amount, source)
            )
            
            # 更新用户表中的经验值
            cursor.execute(
                "UPDATE users SET experience = experience + ? WHERE user_id = ?",
                (amount, user_id)
            )
            
            conn.commit()
            return True
        finally:
            conn.close()
    
    # ==================== 用户资源相关方法 ====================
    def add_user_resource(self, user_id: str, resource_key: str, quantity: int = 1) -> bool:
        """
        增加用户资源数量
        Args:
            user_id: 用户ID
            resource_key: 资源键名
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
                   WHERE user_id = ? AND resource_key = ?""",
                (user_id, resource_key)
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
                       (resource_id, user_id, resource_key, quantity)
                       VALUES (?, ?, ?, ?)""",
                    (resource_id, user_id, resource_key, quantity)
                )
            
            conn.commit()
            return True
        finally:
            conn.close()
    
    def spend_user_resource(self, user_id: str, resource_key: str, quantity: int = 1) -> bool:
        """
        使用用户资源
        Args:
            user_id: 用户ID
            resource_key: 资源键名
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
                   WHERE user_id = ? AND resource_key = ?""",
                (user_id, resource_key)
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
            资源键名和数量的字典
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT resource_key, quantity FROM user_resources WHERE user_id = ?",
                (user_id,)
            )
            rows = cursor.fetchall()
            result: Dict[str, int] = {}
            for row in rows:
                result[row[0]] = row[1]
            return result
        finally:
            conn.close()
    
    # ==================== 任务相关方法 ====================
    def add_task(
        self,
        user_id: str,
        task_name: str,
        description: str = "",
        related_attrs: Optional[Dict[str, Any]] = None,
        estimated_time: int = 30,
        reward_coins: int = 10,
        category_id: Optional[str] = None
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
            category_id: 任务类别ID
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
                   (task_id, user_id, category_id, task_name, description, 
                    related_attrs, estimated_time, reward_coins)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (task_id, user_id, category_id, task_name, description, 
                 related_attrs_json, estimated_time, reward_coins)
            )
            conn.commit()
            return task_id
        finally:
            conn.close()
    
    def get_user_tasks(
        self,
        user_id: str,
        task_status: Optional[str] = None,
        category_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        获取用户任务列表
        Args:
            user_id: 用户ID
            task_status: 任务状态筛选（可选）
            category_id: 任务类别筛选（可选）
            limit: 返回数量限制（可选）
            offset: 偏移量（可选）
        Returns:
            任务列表
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            query = "SELECT * FROM tasks WHERE user_id = ?"
            params: List[Any] = [user_id]
            
            if task_status:
                query += " AND status = ?"
                params.append(task_status)
            
            if category_id:
                query += " AND category_id = ?"
                params.append(category_id)
            
            query += " ORDER BY created_at DESC"
            
            if limit is not None:
                query += " LIMIT ?"
                params.append(limit)
            
            if offset is not None and limit is not None:
                query += " OFFSET ?"
                params.append(offset)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            result: List[Dict[str, Any]] = []
            for row in rows:
                task_dict = dict(row)
                # 解析JSON字段，添加错误处理
                try:
                    if task_dict.get("related_attrs"):
                        task_dict["related_attrs"] = json.loads(task_dict["related_attrs"])
                    else:
                        task_dict["related_attrs"] = {}
                except json.JSONDecodeError:
                    task_dict["related_attrs"] = {}
                
                try:
                    if task_dict.get("proof_data"):
                        task_dict["proof_data"] = json.loads(task_dict["proof_data"])
                    else:
                        task_dict["proof_data"] = {}
                except json.JSONDecodeError:
                    task_dict["proof_data"] = {}
                
                try:
                    if task_dict.get("self_evaluation"):
                        task_dict["self_evaluation"] = json.loads(task_dict["self_evaluation"])
                    else:
                        task_dict["self_evaluation"] = {}
                except json.JSONDecodeError:
                    task_dict["self_evaluation"] = {}
                
                try:
                    if task_dict.get("ai_suggestion"):
                        task_dict["ai_suggestion"] = json.loads(task_dict["ai_suggestion"])
                    else:
                        task_dict["ai_suggestion"] = {}
                except json.JSONDecodeError:
                    task_dict["ai_suggestion"] = {}
                
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
            conn.commit()
            return cursor.rowcount > 0
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
            conn.commit()
            return cursor.rowcount > 0
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
            updates: List[str] = []
            params: List[Any] = []
            
            if self_evaluation is not None:
                updates.append("self_evaluation = ?")
                params.append(json.dumps(self_evaluation))
            
            if ai_suggestion is not None:
                updates.append("ai_suggestion = ?")
                params.append(json.dumps(ai_suggestion))
            
            if not updates:
                return False
            
            params.append(task_id)
            params.append(user_id)
            
            query = f"UPDATE tasks SET {', '.join(updates)} WHERE task_id = ? AND user_id = ?"
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def get_task_stats(self, user_id: str) -> Dict[str, Any]:
        """获取任务统计信息"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # 各状态任务数量
            cursor.execute("""
                SELECT status, COUNT(*) as count 
                FROM tasks 
                WHERE user_id = ? 
                GROUP BY status
            """, (user_id,))
            rows = cursor.fetchall()
            
            status_stats: Dict[str, int] = {}
            total_tasks: int = 0
            for row in rows:
                status_stats[row[0]] = row[1]
                total_tasks += row[1]
            
            # 最近30天完成任务数
            cursor.execute("""
                SELECT COUNT(*) 
                FROM tasks 
                WHERE user_id = ? AND status = 'completed' 
                AND completed_at >= date('now', '-30 days')
            """, (user_id,))
            completed_last_30_days_result = cursor.fetchone()
            completed_last_30_days = completed_last_30_days_result[0] if completed_last_30_days_result else 0
            
            # 平均完成时间（按已完成任务）
            cursor.execute("""
                SELECT AVG(estimated_time) 
                FROM tasks 
                WHERE user_id = ? AND status = 'completed'
            """, (user_id,))
            avg_estimated_time_result = cursor.fetchone()
            avg_estimated_time = avg_estimated_time_result[0] if avg_estimated_time_result[0] is not None else 0
            
            return {
                "total_tasks": total_tasks,
                "status_stats": status_stats,
                "completed_last_30_days": completed_last_30_days,
                "avg_estimated_time": round(avg_estimated_time, 1)
            }
        finally:
            conn.close()
    
    # ==================== 任务类别相关方法 ====================
    def add_task_category(
        self,
        user_id: str,
        category_name: str,
        description: str = "",
        icon: str = "📚",
        color: str = "#3B82F6",
        is_preset: int = 0
    ) -> str:
        """
        添加任务类别
        Args:
            user_id: 用户ID
            category_name: 类别名称
            description: 类别描述
            icon: 类别图标
            color: 类别颜色
            is_preset: 是否为预设类别（0: 自定义, 1: 预设）
        Returns:
            新创建的类别ID
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        category_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        try:
            cursor.execute(
                """INSERT INTO task_categories
                   (category_id, user_id, category_name, description, icon, color, is_preset, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (category_id, user_id, category_name, description, icon, color, is_preset, now, now)
            )
            conn.commit()
            return category_id
        finally:
            conn.close()
    
    def get_user_task_categories(
        self,
        user_id: str,
        include_preset: bool = True
    ) -> List[Dict[str, Any]]:
        """
        获取用户的任务类别列表
        Args:
            user_id: 用户ID
            include_preset: 是否包含预设类别
        Returns:
            任务类别列表
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            if include_preset:
                cursor.execute(
                    """SELECT * FROM task_categories
                       WHERE user_id = ?
                       ORDER BY is_preset DESC, created_at DESC""",
                    (user_id,)
                )
            else:
                cursor.execute(
                    """SELECT * FROM task_categories
                       WHERE user_id = ? AND is_preset = 0
                       ORDER BY created_at DESC""",
                    (user_id,)
                )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
    
    def update_task_category(
        self,
        category_id: str,
        user_id: str,
        category_name: Optional[str] = None,
        description: Optional[str] = None,
        icon: Optional[str] = None,
        color: Optional[str] = None
    ) -> bool:
        """
        更新任务类别
        Args:
            category_id: 类别ID
            user_id: 用户ID
            category_name: 新的类别名称（可选）
            description: 新的类别描述（可选）
            icon: 新的类别图标（可选）
            color: 新的类别颜色（可选）
        Returns:
            是否更新成功
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            updates: List[str] = []
            params: List[Any] = []
            
            if category_name is not None:
                updates.append("category_name = ?")
                params.append(category_name)
            
            if description is not None:
                updates.append("description = ?")
                params.append(description)
            
            if icon is not None:
                updates.append("icon = ?")
                params.append(icon)
            
            if color is not None:
                updates.append("color = ?")
                params.append(color)
            
            if not updates:
                return False
            
            updates.append("updated_at = ?")
            params.append(datetime.now().isoformat())
            params.append(category_id)
            params.append(user_id)
            
            query = f"UPDATE task_categories SET {', '.join(updates)} WHERE category_id = ? AND user_id = ?"
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def delete_task_category(self, category_id: str, user_id: str) -> bool:
        """
        删除任务类别
        Args:
            category_id: 类别ID
            user_id: 用户ID
        Returns:
            是否删除成功
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # 只能删除自定义类别，不能删除预设类别
            cursor.execute(
                """DELETE FROM task_categories
                   WHERE category_id = ? AND user_id = ? AND is_preset = 0""",
                (category_id, user_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def init_preset_categories(self, user_id: str) -> None:
        """
        初始化预设任务类别
        Args:
            user_id: 用户ID
        """
        preset_categories = [
            ("学习Python数据分析", "学习Python数据分析相关知识和技能", "🐍"),
            ("准备英语四级考试", "英语四级考试备考计划", "📚"),
            ("学习Vue 3框架", "学习Vue 3前端框架", "💻"),
            ("减肥健身计划", "制定并执行减肥健身计划", "🏃‍♂️"),
            ("学习摄影技巧", "学习摄影基础知识和技巧", "📷"),
            ("准备考研数学", "考研数学备考计划", "📐"),
            ("学习UI设计", "学习UI设计相关知识", "🎨"),
            ("学习吉他基础", "学习吉他基础知识和弹奏技巧", "🎸")
        ]
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # 检查是否已存在预设类别
            cursor.execute(
                """SELECT COUNT(*) FROM task_categories
                   WHERE user_id = ? AND is_preset = 1""",
                (user_id,)
            )
            if cursor.fetchone()[0] > 0:
                return  # 已存在预设类别，跳过初始化
            
            # 批量插入预设类别
            now = datetime.now().isoformat()
            for category_name, description, icon in preset_categories:
                category_id = str(uuid.uuid4())
                cursor.execute(
                    """INSERT INTO task_categories
                       (category_id, user_id, category_name, description, icon, is_preset, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (category_id, user_id, category_name, description, icon, 1, now, now)
                )
            conn.commit()
        finally:
            conn.close()
    
    # ==================== 购买记录相关方法 ====================
    def record_purchase(
        self,
        user_id: str,
        item_id: str,
        item_name: str,
        quantity: int = 1,
        total_price: int = 0
    ) -> bool:
        """记录购买记录"""
        conn = self.get_connection()
        cursor = conn.cursor()
        purchase_id = str(uuid.uuid4())
        unit_price = total_price // quantity if quantity > 0 else 0
        try:
            cursor.execute(
                """INSERT INTO purchase_history 
                   (purchase_id, user_id, item_id, item_name, quantity, unit_price, total_price)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (purchase_id, user_id, item_id, item_name, quantity, unit_price, total_price)
            )
            conn.commit()
            return True
        finally:
            conn.close()
    
    # ==================== RAG文档管理相关方法 ====================
    def add_system_rag_document(
        self,
        title: str,
        uploaded_by: str,
        file_name: str = "",
        file_type: str = "",
        file_size: int = 0,
        chroma_ids: str = "",
        tags: Optional[List[str]] = None,
        description: str = ""
    ) -> str:
        """
        添加系统RAG文档
        Args:
            title: 文档标题
            uploaded_by: 上传者ID
            file_name: 文件名
            file_type: 文件类型
            file_size: 文件大小
            chroma_ids: Chroma向量ID列表（JSON格式）
            tags: 标签列表
            description: 文档描述
        Returns:
            新创建的文档ID
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        doc_id = str(uuid.uuid4())
        tags_json = json.dumps(tags or [])
        try:
            cursor.execute(
                """INSERT INTO system_rag_documents 
                   (id, title, file_name, file_type, file_size, chroma_ids, uploaded_by, tags, description) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (doc_id, title, file_name, file_type, file_size, chroma_ids, uploaded_by, tags_json, description)
            )
            conn.commit()
            return doc_id
        finally:
            conn.close()
    
    def get_system_rag_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        获取单个系统RAG文档
        Args:
            doc_id: 文档ID
        Returns:
            文档信息，不存在则返回None
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT * FROM system_rag_documents WHERE id = ?",
                (doc_id,)
            )
            row = cursor.fetchone()
            if row:
                doc_dict = dict(row)
                # 解析JSON字段
                if doc_dict.get("tags"):
                    doc_dict["tags"] = json.loads(doc_dict["tags"])
                return doc_dict
            return None
        finally:
            conn.close()
    
    def list_system_rag_documents(self, filter_tags: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        列出所有系统RAG文档
        Args:
            filter_tags: 标签过滤（可选）
        Returns:
            文档列表
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            if filter_tags:
                # 使用标签过滤（简化实现，实际可能需要更复杂的JSON查询）
                cursor.execute(
                    "SELECT * FROM system_rag_documents WHERE is_active = 1 ORDER BY upload_time DESC"
                )
            else:
                cursor.execute(
                    "SELECT * FROM system_rag_documents WHERE is_active = 1 ORDER BY upload_time DESC"
                )
            rows = cursor.fetchall()
            results = []
            for row in rows:
                doc_dict = dict(row)
                # 解析JSON字段
                if doc_dict.get("tags"):
                    doc_dict["tags"] = json.loads(doc_dict["tags"])
                results.append(doc_dict)
            return results
        finally:
            conn.close()
    
    def update_system_rag_document(
        self,
        doc_id: str,
        title: Optional[str] = None,
        file_name: Optional[str] = None,
        file_type: Optional[str] = None,
        file_size: Optional[int] = None,
        chroma_ids: Optional[str] = None,
        is_active: Optional[bool] = None,
        tags: Optional[List[str]] = None,
        description: Optional[str] = None
    ) -> bool:
        """
        更新系统RAG文档
        Args:
            doc_id: 文档ID
            title: 文档标题（可选）
            file_name: 文件名（可选）
            file_type: 文件类型（可选）
            file_size: 文件大小（可选）
            chroma_ids: Chroma向量ID列表（可选）
            is_active: 是否激活（可选）
            tags: 标签列表（可选）
            description: 文档描述（可选）
        Returns:
            是否更新成功
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            updates: List[str] = []
            params: List[Any] = []
            
            if title is not None:
                updates.append("title = ?")
                params.append(title)
            
            if file_name is not None:
                updates.append("file_name = ?")
                params.append(file_name)
            
            if file_type is not None:
                updates.append("file_type = ?")
                params.append(file_type)
            
            if file_size is not None:
                updates.append("file_size = ?")
                params.append(file_size)
            
            if chroma_ids is not None:
                updates.append("chroma_ids = ?")
                params.append(chroma_ids)
            
            if is_active is not None:
                updates.append("is_active = ?")
                params.append(is_active)
            
            if tags is not None:
                updates.append("tags = ?")
                params.append(json.dumps(tags))
            
            if description is not None:
                updates.append("description = ?")
                params.append(description)
            
            if not updates:
                return False
            
            params.append(doc_id)
            query = f"UPDATE system_rag_documents SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def delete_old_task_history(self, days: int = 7) -> int:
        """
        删除超过指定天数的任务生成历史记录
        
        Args:
            days: 保留天数
            
        Returns:
            删除的记录数量
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # SQLite日期函数使用
            cursor.execute(
                "DELETE FROM task_generation_history WHERE created_at < datetime('now', '-' || ? || ' days')",
                (days,)
            )
            deleted_count = cursor.rowcount
            conn.commit()
            return deleted_count
        finally:
            conn.close()
    
    def delete_system_rag_document(self, doc_id: str) -> bool:
        """
        删除系统RAG文档（软删除，将is_active设为False）
        Args:
            doc_id: 文档ID
        Returns:
            是否删除成功
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE system_rag_documents SET is_active = 0 WHERE id = ?",
                (doc_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    # ==================== 临时文件管理相关方法 ====================
    # ... existing code ...

    # ==================== 用户文档管理相关方法 ====================
    def add_user_session_file(
        self,
        user_id: str,
        session_id: str,
        file_name: str,
        content_preview: str,
        original_size: int
    ) -> str:
        """
        添加用户会话临时文件
        Args:
            user_id: 用户ID
            session_id: 会话ID
            file_name: 文件名
            content_preview: 内容预览（前500字符）
            original_size: 原始文件大小
        Returns:
            新创建的文件ID
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        file_id = str(uuid.uuid4())
        upload_time = datetime.now()
        expires_at = upload_time + timedelta(days=1)  # 24小时后过期
        try:
            cursor.execute(
                """INSERT INTO user_session_files 
                   (id, user_id, session_id, file_name, content_preview, original_size, upload_time, expires_at) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (file_id, user_id, session_id, file_name, content_preview, original_size, 
                 upload_time.isoformat(), expires_at.isoformat())
            )
            conn.commit()
            return file_id
        finally:
            conn.close()
    
    def get_user_session_files(self, user_id: str, session_id: str) -> List[Dict[str, Any]]:
        """
        获取用户会话临时文件列表
        Args:
            user_id: 用户ID
            session_id: 会话ID
        Returns:
            临时文件列表
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """SELECT * FROM user_session_files 
                   WHERE user_id = ? AND session_id = ? AND expires_at > ? 
                   ORDER BY upload_time DESC""",
                (user_id, session_id, datetime.now().isoformat())
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
    
    def cleanup_expired_session_files(self) -> int:
        """
        清理过期的会话临时文件
        Returns:
            清理的文件数量
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "DELETE FROM user_session_files WHERE expires_at <= ?",
                (datetime.now().isoformat(),)
            )
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()

    # ==================== 用户文档管理相关方法 ====================

    def add_user_document(self, user_id: str, title: str, original_name: str, file_type: str,
                         file_size: int, storage_path: str, content_preview: str = "",
                         tags: Optional[List[str]] = None) -> str:
        """
        添加用户文档记录
        Args:
            user_id: 用户ID
            title: 文档标题
            original_name: 原始文件名
            file_type: 文件类型
            file_size: 文件大小
            storage_path: 存储路径
            content_preview: 内容预览
            tags: 标签列表
        Returns:
            新创建的文档ID
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        doc_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        try:
            cursor.execute(
                """INSERT INTO user_documents
                   (doc_id, user_id, title, original_name, file_type, file_size,
                    storage_path, content_preview, tags, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (doc_id, user_id, title, original_name, file_type, file_size,
                 storage_path, content_preview, json.dumps(tags or []), now, now)
            )
            conn.commit()
            return doc_id
        finally:
            conn.close()

    def get_user_documents(self, user_id: str, status: Optional[str] = None,
                          limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        获取用户文档列表
        Args:
            user_id: 用户ID
            status: 解析状态筛选
            limit: 返回数量限制
            offset: 偏移量
        Returns:
            文档列表
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            query = "SELECT * FROM user_documents WHERE user_id = ?"
            params = [user_id]

            if status:
                query += " AND parse_status = ?"
                params.append(status)

            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            rows = cursor.fetchall()

            result = []
            for row in rows:
                doc_dict = dict(row)
                # 解析JSON字段
                try:
                    doc_dict["tags"] = json.loads(doc_dict.get("tags", "[]"))
                    doc_dict["chroma_ids"] = json.loads(doc_dict.get("chroma_ids", "[]")) if doc_dict.get("chroma_ids") else []
                except json.JSONDecodeError:
                    doc_dict["tags"] = []
                    doc_dict["chroma_ids"] = []
                result.append(doc_dict)

            return result
        finally:
            conn.close()

    def get_user_document(self, user_id: str, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        获取单个用户文档
        Args:
            user_id: 用户ID
            doc_id: 文档ID
        Returns:
            文档信息或None
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "SELECT * FROM user_documents WHERE doc_id = ? AND user_id = ?",
                (doc_id, user_id)
            )
            row = cursor.fetchone()

            if row:
                doc_dict = dict(row)
                try:
                    doc_dict["tags"] = json.loads(doc_dict.get("tags", "[]"))
                    doc_dict["chroma_ids"] = json.loads(doc_dict.get("chroma_ids", "[]")) if doc_dict.get("chroma_ids") else []
                except json.JSONDecodeError:
                    doc_dict["tags"] = []
                    doc_dict["chroma_ids"] = []
                return doc_dict

            return None
        finally:
            conn.close()

    def update_user_document_status(self, doc_id: str, status: str,
                                   vector_collection: Optional[str] = None,
                                   chroma_ids: Optional[List[str]] = None,
                                   error_message: Optional[str] = None) -> bool:
        """
        更新文档解析状态
        Args:
            doc_id: 文档ID
            status: 新状态
            vector_collection: 向量集合名
            chroma_ids: Chroma向量ID列表
            error_message: 错误信息
        Returns:
            是否更新成功
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            updates = ["parse_status = ?", "updated_at = ?"]
            params = [status, datetime.now().isoformat()]

            if vector_collection:
                updates.append("vector_collection = ?")
                params.append(vector_collection)

            if chroma_ids:
                updates.append("chroma_ids = ?")
                params.append(json.dumps(chroma_ids))

            if error_message:
                updates.append("error_message = ?")
                params.append(error_message)

            params.append(doc_id)

            query = f"UPDATE user_documents SET {', '.join(updates)} WHERE doc_id = ?"
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def update_user_document_info(self, doc_id: str, user_id: str, title: Optional[str] = None,
                                 tags: Optional[List[str]] = None) -> bool:
        """
        更新文档基本信息
        Args:
            doc_id: 文档ID
            user_id: 用户ID
            title: 新标题
            tags: 新标签
        Returns:
            是否更新成功
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            updates = ["updated_at = ?"]
            params = [datetime.now().isoformat()]

            if title:
                updates.append("title = ?")
                params.append(title)

            if tags is not None:
                updates.append("tags = ?")
                params.append(json.dumps(tags))

            if len(updates) == 1:  # 只有时间更新
                return True

            params.extend([doc_id, user_id])
            query = f"UPDATE user_documents SET {', '.join(updates)} WHERE doc_id = ? AND user_id = ?"
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def delete_user_document(self, doc_id: str, user_id: str) -> bool:
        """
        删除用户文档
        Args:
            doc_id: 文档ID
            user_id: 用户ID
        Returns:
            是否删除成功
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # 获取文档信息，用于清理向量数据
            doc = self.get_user_document(user_id, doc_id)
            if not doc:
                return False

            # 如果有向量数据，需要清理（这里简化处理，实际需要向量管理器配合）

            cursor.execute(
                "DELETE FROM user_documents WHERE doc_id = ? AND user_id = ?",
                (doc_id, user_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def get_user_document_stats(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户文档统计信息
        Args:
            user_id: 用户ID
        Returns:
            统计信息
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # 总文档数
            cursor.execute("SELECT COUNT(*) FROM user_documents WHERE user_id = ?", (user_id,))
            total_docs = cursor.fetchone()[0]

            # 各状态文档数
            cursor.execute("""
                SELECT parse_status, COUNT(*) as count
                FROM user_documents
                WHERE user_id = ?
                GROUP BY parse_status
            """, (user_id,))
            status_rows = cursor.fetchall()
            status_stats = {row[0]: row[1] for row in status_rows}

            # 总存储大小
            cursor.execute("SELECT SUM(file_size) FROM user_documents WHERE user_id = ?", (user_id,))
            total_size = cursor.fetchone()[0] or 0

            return {
                "total_documents": total_docs,
                "status_stats": status_stats,
                "total_size": total_size,
                "completed_documents": status_stats.get("completed", 0)
            }
        finally:
            conn.close()