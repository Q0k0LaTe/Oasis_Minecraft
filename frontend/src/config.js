// API 配置
// 使用环境变量或默认值
// 在开发环境使用 /api（走 Vite 代理），在生产环境使用相对路径（由 nginx 代理）
// 这样可以避免 CORS 问题，尤其是 SSE 流式响应
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

// 直连后端 URL（用于某些需要绕过代理的情况）
export const DIRECT_BACKEND_URL = import.meta.env.VITE_DIRECT_BACKEND_URL ||
  (import.meta.env.DEV ? 'http://localhost:3000' : '');

export const BACKEND_BASE_URL = API_BASE_URL.replace(/\/api\/?$/, '');
export const POLL_INTERVAL = 2000;

