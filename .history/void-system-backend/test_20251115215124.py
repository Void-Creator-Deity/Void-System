import requests
response = requests.post(
    "http://localhost:8000/lv/qa/invoke",
    json={'question': '虚空系统的核心功能是什么？'}
)
print(response.json())