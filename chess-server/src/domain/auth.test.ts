import { describe, expect, it } from 'vitest'

import { createAuthService } from './auth.js'

describe('auth service', () => {
  it('returns a stable mock player and session for a WeChat code', async () => {
    const auth = createAuthService({ now: () => new Date('2026-07-15T00:00:00.000Z') })

    const first = await auth.loginWithWechatCode('dev-code-1')
    const second = await auth.loginWithWechatCode('dev-code-1')

    expect(first.player).toEqual({
      id: 'mock_dev-code-1',
      nickname: '棋友 1',
    })
    expect(second.player).toEqual(first.player)
    expect(first.session.token).not.toEqual(second.session.token)
    expect(auth.requireSession(first.session.token)?.playerId).toBe(first.player.id)
  })

  it('rejects empty login codes', async () => {
    const auth = createAuthService()

    await expect(auth.loginWithWechatCode('')).rejects.toThrow('微信登录 code 不能为空')
  })

  it('returns null for missing or expired sessions', async () => {
    const auth = createAuthService({
      now: () => new Date('2026-07-15T00:00:00.000Z'),
      sessionTtlMs: 10,
    })

    const result = await auth.loginWithWechatCode('dev-code-2')

    expect(auth.requireSession('missing')).toBeNull()
    expect(auth.requireSession(result.session.token, new Date('2026-07-15T00:00:00.011Z'))).toBeNull()
  })
})
