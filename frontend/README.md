生产环境（Docker）：前端通过 nginx 代理 /api 到后端服务
开发环境：使用 Vite 的代理配置，或直接使用 http://localhost:3000/api
可通过环境变量 VITE_API_BASE_URL 自定义 API地址