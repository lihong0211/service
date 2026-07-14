import express, { type Express, type Request, type Response as ExpressResponse } from 'express'

import type { AuthService } from '../domain/auth.js'
import type { MatchmakingService } from '../domain/matchmaking.js'

export interface AppDependencies {
  auth: AuthService
  matchmaking: MatchmakingService
}

export interface AppHandle {
  express: Express
  request(path: string, init?: RequestInit): Promise<globalThis.Response>
}

function getBearerToken(req: Request): string | null {
  const header = req.header('authorization')
  if (!header?.startsWith('Bearer ')) return null
  return header.slice('Bearer '.length)
}

function sendError(res: ExpressResponse, status: number, message: string): void {
  res.status(status).json({ error: message })
}

export function createApp({ auth, matchmaking }: AppDependencies): AppHandle {
  const app = express()
  app.use(express.json())

  app.post('/auth/wechat-login', async (req, res) => {
    try {
      const result = await auth.loginWithWechatCode(String(req.body?.code ?? ''))
      res.json(result)
    } catch (error) {
      sendError(res, 400, error instanceof Error ? error.message : '登录失败')
    }
  })

  app.post('/matchmaking/join', (req, res) => {
    const token = getBearerToken(req)
    const session = token ? auth.requireSession(token) : null
    if (!session) {
      sendError(res, 401, '登录已失效')
      return
    }

    res.json(matchmaking.joinQueue(session.playerId))
  })

  app.post('/matchmaking/leave', (req, res) => {
    const token = getBearerToken(req)
    const session = token ? auth.requireSession(token) : null
    if (!session) {
      sendError(res, 401, '登录已失效')
      return
    }

    matchmaking.leaveQueue(session.playerId)
    res.json({ status: 'left' })
  })

  return {
    express: app,
    async request(path, init = {}) {
      const server = app.listen(0)
      const address = server.address()
      if (!address || typeof address === 'string') {
        server.close()
        throw new Error('测试服务器启动失败')
      }

      try {
        return await fetch(`http://127.0.0.1:${address.port}${path}`, init)
      } finally {
        server.close()
      }
    },
  }
}
