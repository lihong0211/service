import { createAuthService } from './domain/auth.js'
import { createMatchmakingService } from './domain/matchmaking.js'
import { createHttpServer } from './http/server.js'

const port = Number(process.env.PORT ?? 8787)

const runtime = createHttpServer({
  auth: createAuthService(),
  matchmaking: createMatchmakingService(),
})

runtime.server.listen(port, () => {
  console.log(`chess-server listening on http://127.0.0.1:${port}`)
  console.log('微信凭据未配置时使用开发 mock 登录模式')
})
