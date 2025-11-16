import requests

def test_different_formats():
    base_url = "http://localhost:8000/lc/qa/invoke"
    
    test_cases = [
        {
            "name": "简单对象格式",
            "data": {
                "input": {
                    "question": "虚空系统的核心功能是什么？"
                }
            }
        },
        {
            "name": "包含 root 字段", 
            "data": {
                "input": {
                    "root": {
                        "question": "虚空系统的核心功能是什么？"
                    },
                    "question": "虚空系统的核心功能是什么？"
                }
            }
        },
        {
            "name": "直接字符串",
            "data": {
                "input": "虚空系统的核心功能是什么？"
            }
        },
        {
            "name": "嵌套问题字段",
            "data": {
                "input": {
                    "input": {
                        "question": "虚空系统的核心功能是什么？"
                    }
                }
            }
        }
    ]
    
    for test_case in test_cases:
        print(f"\n=== 测试: {test_case['name']} ===")
        print(f"发送数据: {test_case['data']}")
        
        try:
            response = requests.post(base_url, json=test_case['data'])
            print(f"状态码: {response.status_code}")
            if response.status_code == 200:
                print(f"✅ 成功: {response.json()}")
            else:
                print(f"❌ 失败: {response.json()}")
        except Exception as e:
            print(f"❌ 请求异常: {e}")

test_different_formats()