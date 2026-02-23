// Cloudflare Workers 配置
// 处理API请求，代理到后端服务

// 定义API路由和处理逻辑
addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

// 配置实际的后端API地址
const BACKEND_API_URL = 'https://your-deployed-flask-app.com/api';

async function handleRequest(request) {
  const url = new URL(request.url);
  
  // 处理CORS预检请求
  if (request.method === 'OPTIONS') {
    return handleCorsPreflight(request);
  }
  
  // 处理API请求
  if (url.pathname.startsWith('/api/')) {
    try {
      // 构建代理请求URL
      const apiPath = url.pathname.replace('/api', '');
      const proxyUrl = `${BACKEND_API_URL}${apiPath}${url.search}`;
      
      // 创建代理请求
      const proxyRequest = new Request(proxyUrl, {
        method: request.method,
        headers: request.headers,
        body: request.body,
        cf: request.cf
      });
      
      // 发送代理请求
      const response = await fetch(proxyRequest);
      
      // 添加CORS头
      const corsHeaders = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        'Access-Control-Allow-Credentials': 'true'
      };
      
      // 创建带有CORS头的响应
      const corsResponse = new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: {
          ...response.headers,
          ...corsHeaders
        }
      });
      
      return corsResponse;
    } catch (error) {
      return new Response(
        JSON.stringify({
          success: false,
          error: `API代理错误: ${error.message}`
        }),
        {
          headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Allow-Credentials': 'true'
          },
          status: 500
        }
      );
    }
  }
  
  // 处理其他请求，返回静态文件
  return await fetch(request);
}

// 处理CORS预检请求
function handleCorsPreflight(request) {
  const origin = request.headers.get('Origin') || '*';
  
  return new Response(null, {
    headers: {
      'Access-Control-Allow-Origin': origin,
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
      'Access-Control-Allow-Credentials': 'true',
      'Access-Control-Max-Age': '86400' // 24小时
    },
    status: 204
  });
}
