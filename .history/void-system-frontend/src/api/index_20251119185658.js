import axios from "axios"

const api = axios.create({
  baseURL: "http://127.0.0.1:8000",  // 连接 FastAPI
  timeout: 60000,  // 增加到60秒，足够AI生成内容
  headers: {
    'Content-Type': 'application/json'
  }
})

export default api
