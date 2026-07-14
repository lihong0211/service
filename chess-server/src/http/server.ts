import { createServer, type Server } from 'node:http'
import { URL } from 'node:url'

import { WebSocketServer, type WebSocket } from 'ws'

import type { MoveCommand, Room } from '../domain/types.js'
import { createApp, type AppDependencies } from './app.js'

export interface RealtimeServer {
  server: Server
  close(): Promise<void>
}

interface SocketBinding {
  socket: WebSocket
}

function send(socket: WebSocket, event: unknown): void {
  if (socket.readyState === socket.OPEN) {
    socket.send(JSON.stringify(event))
  }
}

function roomPlayers(room: Room): string[] {
  return [room.redPlayerId, room.blackPlayerId]
}

export function createHttpServer({ auth, matchmaking }: AppDependencies): RealtimeServer {
  const { express } = createApp({ auth, matchmaking })
  const server = createServer(express)
  const wss = new WebSocketServer({ server, path: '/rooms' })
  const sockets = new Map<string, SocketBinding>()

  function broadcastRoom(room: Room, eventType = 'room-updated'): void {
    for (const playerId of roomPlayers(room)) {
      const binding = sockets.get(playerId)
      if (binding) {
        send(binding.socket, { type: eventType, room })
      }
    }
  }

  function authenticate(requestUrl: string | undefined): string | null {
    const url = new URL(requestUrl ?? '', 'http://127.0.0.1')
    const token = url.searchParams.get('token')
    const session = token ? auth.requireSession(token) : null
    return session?.playerId ?? null
  }

  wss.on('connection', (socket, request) => {
    const playerId = authenticate(request.url)
    if (!playerId) {
      send(socket, { type: 'error', message: '登录已失效' })
      socket.close()
      return
    }

    sockets.set(playerId, { socket })

    socket.on('message', (raw) => {
      try {
        const message = JSON.parse(String(raw)) as { type?: string; payload?: unknown }
        if (message.type === 'join-match') {
          const result = matchmaking.joinQueue(playerId)
          if (result.status === 'matched') {
            broadcastRoom(result.room, 'room-created')
          } else {
            send(socket, { type: 'matchmaking-queued' })
          }
          return
        }

        if (message.type !== 'move') return

        const command = message.payload as Omit<MoveCommand, 'playerId'>
        const result = matchmaking.submitMove({ ...command, playerId })
        if (result.room && result.accepted) {
          broadcastRoom(result.room, 'move-accepted')
        } else {
          send(socket, {
            type: 'move-rejected',
            reason: result.reason ?? '走子失败',
            room: result.room,
          })
        }
      } catch {
        send(socket, { type: 'error', message: '消息格式错误' })
      }
    })

    socket.on('close', () => {
      matchmaking.leaveQueue(playerId)
      sockets.delete(playerId)
    })
  })

  return {
    server,
    close() {
      return new Promise((resolve, reject) => {
        wss.close((wsError) => {
          if (wsError) {
            reject(wsError)
            return
          }

          server.close((serverError) => {
            if (serverError) reject(serverError)
            else resolve()
          })
        })
      })
    },
  }
}
