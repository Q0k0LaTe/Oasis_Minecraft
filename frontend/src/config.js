// API 配置
// 使用环境变量或默认值
// 在开发环境使用完整 URL，在生产环境使用相对路径（由 nginx 代理）
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 
  (import.meta.env.DEV ? 'http://localhost:3000/api' : '/api');
export const BACKEND_BASE_URL = API_BASE_URL.replace(/\/api\/?$/, '');
export const POLL_INTERVAL = 2000;

