from fastapi import FastAPI
from main import app

routes = []
for route in app.routes:
    if hasattr(route, 'path') and hasattr(route, 'methods'):
        routes.append((route.path, list(route.methods)))

routes.sort()

print("当前API路由列表：")
print("=" * 50)
for path, methods in routes:
    print(f"{path} - {methods}")

# 检查是否有重复路径
path_count = {}
for path, _ in routes:
    path_count[path] = path_count.get(path, 0) + 1

duplicates = [path for path, count in path_count.items() if count > 1]
if duplicates:
    print("\n发现重复路径：")
    print("=" * 30)
    for path in duplicates:
        print(f"- {path}")
else:
    print("\n没有发现重复路径")

# 检查文档相关路由
print("\n文档相关路由：")
print("=" * 30)
doc_routes = [route for route in routes if '/documents' in route[0]]
for path, methods in doc_routes:
    print(f"{path} - {methods}")

# 检查问答相关路由
print("\n问答相关路由：")
print("=" * 30)
qa_routes = [route for route in routes if '/qa' in route[0]]
for path, methods in qa_routes:
    print(f"{path} - {methods}")
