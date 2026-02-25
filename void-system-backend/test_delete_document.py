#!/usr/bin/env python3
# 测试文档删除功能

import sys
import os
import json
import sqlite3

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import Database

def test_document_deletion():
    """测试文档删除功能"""
    print("=== 测试文档删除功能 ===")
    
    # 创建数据库实例
    db = Database()
    
    # 测试数据
    test_user_id = "test_user_123"
    test_doc_id = "test_doc_456"
    
    try:
        # 1. 首先添加一个测试文档
        print("1. 添加测试文档...")
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # 插入测试数据
        test_doc = {
            "doc_id": test_doc_id,
            "user_id": test_user_id,
            "title": "测试文档",
            "original_name": "test.txt",
            "file_type": "txt",
            "file_size": 1024,
            "storage_path": "",
            "parse_status": "completed",
            "vector_collection": "",
            "chroma_ids": "[]",
            "tags": "[]",
            "created_at": "2025-12-24T00:00:00",
            "updated_at": "2025-12-24T00:00:00"
        }
        
        cursor.execute(
            "INSERT INTO user_documents (" + ", ".join(test_doc.keys()) + ") VALUES (" + ", ".join(["?"] * len(test_doc)) + ")",
            tuple(test_doc.values())
        )
        conn.commit()
        conn.close()
        print("   ✓ 测试文档添加成功")
        
        # 2. 测试文档存在检查
        print("2. 测试文档存在检查...")
        exists = db.check_document_exists(test_doc_id, test_user_id)
        print(f"   ✓ 文档存在检查结果: {'存在' if exists else '不存在'}")
        assert exists, "文档应该存在"
        
        # 3. 测试获取文档信息
        print("3. 测试获取文档信息...")
        doc = db.get_user_document(test_user_id, test_doc_id)
        print(f"   ✓ 获取文档信息成功: {doc['title']}")
        assert doc is not None, "应该能够获取到文档信息"
        
        # 4. 测试文档删除
        print("4. 测试文档删除...")
        delete_success = db.delete_user_document(test_doc_id, test_user_id)
        print(f"   ✓ 文档删除结果: {'成功' if delete_success else '失败'}")
        assert delete_success, "文档删除应该成功"
        
        # 5. 测试删除后文档不存在
        print("5. 测试删除后文档不存在...")
        exists_after_delete = db.check_document_exists(test_doc_id, test_user_id)
        print(f"   ✓ 删除后文档存在检查结果: {'存在' if exists_after_delete else '不存在'}")
        assert not exists_after_delete, "删除后文档应该不存在"
        
        # 6. 测试获取已删除文档
        print("6. 测试获取已删除文档...")
        doc_after_delete = db.get_user_document(test_user_id, test_doc_id)
        print(f"   ✓ 获取已删除文档结果: {'None' if doc_after_delete is None else '存在'}")
        assert doc_after_delete is None, "已删除文档应该无法获取"
        
        # 7. 测试删除不存在的文档
        print("7. 测试删除不存在的文档...")
        delete_nonexistent = db.delete_user_document("nonexistent_doc", test_user_id)
        print(f"   ✓ 删除不存在文档结果: {'成功' if delete_nonexistent else '失败'}")
        assert not delete_nonexistent, "删除不存在文档应该失败"
        
        print("\n=== 所有测试通过！文档删除功能正常 ===")
        return True
        
    except Exception as e:
        print(f"\n=== 测试失败: {str(e)} ===")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # 清理测试数据（以防万一）
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM user_documents WHERE doc_id = ? AND user_id = ?",
                (test_doc_id, test_user_id)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"清理测试数据失败: {str(e)}")

if __name__ == "__main__":
    success = test_document_deletion()
    sys.exit(0 if success else 1)
