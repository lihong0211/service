import { randomUUID } from 'node:crypto'

import { applyMoveToFen, createInitialSnapshot } from './rules.js'
import type { Color, MoveCommand, Room } from './types.js'

export interface MatchmakingServiceOptions {
  now?: () => Date
  id?: () => string
}

export type JoinQueueResult =
  | { status: 'queued'; room?: undefined }
  | { status: 'matched'; room: Room }

export interface SubmitMoveResult {
  accepted: boolean
  reason?: string
  room?: Room
}

export interface MatchmakingService {
  joinQueue(playerId: string): JoinQueueResult
  leaveQueue(playerId: string): void
  submitMove(command: MoveCommand): SubmitMoveResult
  getRoom(roomId: string): Room | null
  getQueue(): string[]
}

function playerColor(room: Room, playerId: string): Color | null {
  if (room.redPlayerId === playerId) return 'red'
  if (room.blackPlayerId === playerId) return 'black'
  return null
}

export function createMatchmakingService(options: MatchmakingServiceOptions = {}): MatchmakingService {
  const now = options.now ?? (() => new Date())
  const id = options.id ?? randomUUID
  const queue: string[] = []
  const rooms = new Map<string, Room>()

  function createRoom(redPlayerId: string, blackPlayerId: string): Room {
    const timestamp = now().toISOString()
    return {
      id: id(),
      redPlayerId,
      blackPlayerId,
      snapshot: createInitialSnapshot(),
      createdAt: timestamp,
      updatedAt: timestamp,
    }
  }

  return {
    joinQueue(playerId: string): JoinQueueResult {
      if (queue.includes(playerId)) {
        return { status: 'queued' }
      }

      const opponentId = queue.find((queuedPlayerId) => queuedPlayerId !== playerId)
      if (!opponentId) {
        queue.push(playerId)
        return { status: 'queued' }
      }

      queue.splice(queue.indexOf(opponentId), 1)
      const room = createRoom(opponentId, playerId)
      rooms.set(room.id, room)

      return { status: 'matched', room }
    },

    leaveQueue(playerId: string): void {
      const index = queue.indexOf(playerId)
      if (index >= 0) queue.splice(index, 1)
    },

    submitMove(command: MoveCommand): SubmitMoveResult {
      const room = rooms.get(command.roomId)
      if (!room) {
        return { accepted: false, reason: '房间不存在' }
      }

      const color = playerColor(room, command.playerId)
      if (!color) {
        return { accepted: false, reason: '你不在这个房间中', room }
      }

      if (room.snapshot.turn !== color) {
        return { accepted: false, reason: '当前不是你的回合', room }
      }

      const snapshot = applyMoveToFen(room.snapshot.fen, command.from, command.to)
      if (!snapshot) {
        return { accepted: false, reason: '非法走子', room }
      }

      const updatedRoom = {
        ...room,
        snapshot,
        updatedAt: now().toISOString(),
      }
      rooms.set(room.id, updatedRoom)

      return { accepted: true, room: updatedRoom }
    },

    getRoom(roomId: string): Room | null {
      return rooms.get(roomId) ?? null
    },

    getQueue(): string[] {
      return [...queue]
    },
  }
}
