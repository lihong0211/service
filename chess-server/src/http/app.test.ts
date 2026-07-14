import { describe, expect, it } from 'vitest'

import { createAuthService } from '../domain/auth.js'
import { createMatchmakingService } from '../domain/matchmaking.js'
import { createApp } from './app.js'

describe('HTTP app', () => {
  it('logs in with a WeChat code', async () => {
    const app = createApp({
      auth: createAuthService({ now: () => new Date('2026-07-15T00:00:00.000Z') }),
      matchmaking: createMatchmakingService(),
    })

    const response = await app.request('/auth/wechat-login', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ code: 'dev-code-1' }),
    })

    expect(response.status).toBe(200)
    await expect(response.json()).resolves.toMatchObject({
      player: { id: 'mock_dev-code-1', nickname: '棋友 1' },
      session: { playerId: 'mock_dev-code-1' },
    })
  })

  it('rejects matchmaking join without a session', async () => {
    const app = createApp({
      auth: createAuthService(),
      matchmaking: createMatchmakingService(),
    })

    const response = await app.request('/matchmaking/join', { method: 'POST' })

    expect(response.status).toBe(401)
  })

  it('joins matchmaking with a valid session', async () => {
    const auth = createAuthService()
    const login = await auth.loginWithWechatCode('dev-code-1')
    const app = createApp({
      auth,
      matchmaking: createMatchmakingService(),
    })

    const response = await app.request('/matchmaking/join', {
      method: 'POST',
      headers: { authorization: `Bearer ${login.session.token}` },
    })

    expect(response.status).toBe(200)
    await expect(response.json()).resolves.toEqual({ status: 'queued' })
  })
})
