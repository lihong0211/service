import { describe, expect, it } from 'vitest'

import { createMatchmakingService } from './matchmaking.js'

describe('matchmaking service', () => {
  it('pairs two queued players into one room', () => {
    const matchmaking = createMatchmakingService({
      now: () => new Date('2026-07-15T00:00:00.000Z'),
      id: () => 'room-1',
    })

    expect(matchmaking.joinQueue('player-a')).toEqual({ status: 'queued' })

    const result = matchmaking.joinQueue('player-b')

    expect(result.status).toBe('matched')
    expect(result.room?.id).toBe('room-1')
    expect(result.room?.redPlayerId).toBe('player-a')
    expect(result.room?.blackPlayerId).toBe('player-b')
    expect(matchmaking.getQueue()).toEqual([])
  })

  it('does not enqueue the same player twice', () => {
    const matchmaking = createMatchmakingService()

    matchmaking.joinQueue('player-a')

    expect(matchmaking.joinQueue('player-a')).toEqual({ status: 'queued' })
    expect(matchmaking.getQueue()).toEqual(['player-a'])
  })

  it('applies legal moves and updates the room snapshot', () => {
    const matchmaking = createMatchmakingService({ id: () => 'room-1' })
    matchmaking.joinQueue('red')
    const matched = matchmaking.joinQueue('black')

    const result = matchmaking.submitMove({
      roomId: matched.room?.id ?? '',
      playerId: 'red',
      from: { row: 6, col: 0 },
      to: { row: 5, col: 0 },
      clientMoveId: 'move-1',
    })

    expect(result.accepted).toBe(true)
    expect(result.room?.snapshot.turn).toBe('black')
    expect(result.room?.snapshot.history).toHaveLength(1)
  })

  it('rejects illegal moves and keeps the room unchanged', () => {
    const matchmaking = createMatchmakingService({ id: () => 'room-1' })
    matchmaking.joinQueue('red')
    const matched = matchmaking.joinQueue('black')
    const before = matched.room?.snapshot.fen

    const result = matchmaking.submitMove({
      roomId: matched.room?.id ?? '',
      playerId: 'red',
      from: { row: 9, col: 0 },
      to: { row: 0, col: 0 },
      clientMoveId: 'move-1',
    })

    expect(result.accepted).toBe(false)
    expect(result.reason).toBe('非法走子')
    expect(result.room?.snapshot.fen).toBe(before)
  })

  it('rejects moves from a player whose side is not on turn', () => {
    const matchmaking = createMatchmakingService({ id: () => 'room-1' })
    matchmaking.joinQueue('red')
    const matched = matchmaking.joinQueue('black')

    const result = matchmaking.submitMove({
      roomId: matched.room?.id ?? '',
      playerId: 'black',
      from: { row: 3, col: 0 },
      to: { row: 4, col: 0 },
      clientMoveId: 'move-1',
    })

    expect(result.accepted).toBe(false)
    expect(result.reason).toBe('当前不是你的回合')
  })
})
