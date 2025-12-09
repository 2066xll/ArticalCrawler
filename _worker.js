// Cloudflare Workers 配置
// 处理API请求，代理到后端服务

// 定义API路由和处理逻辑
addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  const url = new URL(request.url)
  
  // 处理API请求
  if (url.pathname.startsWith('/api/')) {
    try {
      // 这里可以添加API请求的处理逻辑
      // 对于Flask应用，我们需要将请求代理到后端服务
      // 由于Cloudflare Pages Functions无法直接运行Python，我们需要使用其他方式集成
      
      // 暂时返回一个友好的错误信息，说明API服务不可用
      return new Response(
        JSON.stringify({
          success: false,
          error: 'API服务不可用，请使用完整的Flask应用部署方案'
        }),
        {
          headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
          },
          status: 200
        }
      )
    } catch (error) {
      return new Response(
        JSON.stringify({
          success: false,
          error: `API处理错误: ${error.message}`
        }),
        {
          headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
          },
          status: 500
        }
      )
    }
  }
  
  // 处理其他请求，返回静态文件
  return await fetch(request)
}
