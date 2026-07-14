import { createHash, randomUUID } from 'node:crypto'

import type { Player, Session } from './types.js'

const DEFAULT_SESSION_TTL_MS = 1000 * 60 * 60 * 24 * 7

export interface AuthServiceOptions {
  now?: () => Date
  sessionTtlMs?: number
}

export interface LoginResult {
  player: Player
  session: Session
}

export interface AuthService {
  loginWithWechatCode(code: string): Promise<LoginResult>
  requireSession(token: string, at?: Date): Session | null
  getPlayer(playerId: string): Player | null
}

function createMockPlayer(code: string): Player {
  const digest = createHash('sha256').update(code).digest('hex')
  const codeNumber = code.match(/\d+$/)?.[0]
  const suffix = codeNumber ?? String(Number.parseInt(digest.slice(0, 4), 16) % 10000 || 1)

  return {
    id: `mock_${code}`,
    nickname: `棋友 ${suffix}`,
  }
}

export function createAuthService(options: AuthServiceOptions = {}): AuthService {
  const now = options.now ?? (() => new Date())
  const sessionTtlMs = options.sessionTtlMs ?? DEFAULT_SESSION_TTL_MS
  const players = new Map<string, Player>()
  const sessions = new Map<string, Session>()

  return {
    async loginWithWechatCode(code: string): Promise<LoginResult> {
      const trimmedCode = code.trim()

      if (!trimmedCode) {
        throw new Error('微信登录 code 不能为空')
      }

      const player = createMockPlayer(trimmedCode)
      players.set(player.id, player)

      const createdAt = now()
      const expiresAt = new Date(createdAt.getTime() + sessionTtlMs)
      const session: Session = {
        token: randomUUID(),
        playerId: player.id,
        createdAt: createdAt.toISOString(),
        expiresAt: expiresAt.toISOString(),
      }
      sessions.set(session.token, session)

      return { player, session }
    },

    requireSession(token: string, at = now()): Session | null {
      const session = sessions.get(token)
      if (!session) return null

      if (new Date(session.expiresAt).getTime() <= at.getTime()) {
        sessions.delete(token)
        return null
      }

      return session
    },

    getPlayer(playerId: string): Player | null {
      return players.get(playerId) ?? null
    },
  }
}
