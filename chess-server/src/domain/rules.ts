import { Xiangqi, type XiangqiMove, type XiangqiPiece } from 'xiangqi.js'

import type { Color, GameSnapshot, GameStatus, MoveResult, Piece, PieceType, Position } from './types.js'

const PIECE_TYPES: Record<string, PieceType> = {
  k: 'king',
  a: 'advisor',
  b: 'elephant',
  n: 'horse',
  r: 'chariot',
  c: 'cannon',
  p: 'soldier',
}

export function positionToIccs({ row, col }: Position): string {
  return `${String.fromCharCode(97 + col)}${9 - row}`
}

export function iccsToPosition(square: string): Position {
  return {
    row: 9 - Number(square[1]),
    col: square.charCodeAt(0) - 97,
  }
}

function toColor(color: 'r' | 'b'): Color {
  return color === 'r' ? 'red' : 'black'
}

function toPieceType(type: string): PieceType {
  const pieceType = PIECE_TYPES[type.toLowerCase()]
  if (!pieceType) {
    throw new Error(`未知棋子类型：${type}`)
  }

  return pieceType
}

function toPiece(piece: XiangqiPiece): Piece {
  return {
    color: toColor(piece.color),
    type: toPieceType(piece.type),
  }
}

function toMoveResult(move: XiangqiMove): MoveResult {
  return {
    color: toColor(move.color),
    from: iccsToPosition(move.from),
    to: iccsToPosition(move.to),
    piece: toPieceType(move.piece),
    captured: move.captured ? toPieceType(move.captured) : undefined,
    iccs: move.iccs,
  }
}

function getStatus(game: Xiangqi): GameStatus {
  if (game.in_checkmate()) return 'checkmate'
  if (game.in_stalemate()) return 'stalemate'
  if (game.in_draw()) return 'draw'
  if (game.in_check()) return 'check'
  return 'playing'
}

export class XiangqiRules {
  private readonly game: Xiangqi

  constructor(fen?: string) {
    this.game = new Xiangqi(fen)
  }

  getSnapshot(): GameSnapshot {
    const history = this.game.history({ verbose: true }) as XiangqiMove[]

    return {
      board: this.game.board().map((row) => row.map((piece) => (piece ? toPiece(piece) : null))),
      turn: toColor(this.game.turn()),
      status: getStatus(this.game),
      history: history.map(toMoveResult),
      fen: this.game.fen(),
    }
  }

  move(from: Position, to: Position): MoveResult | null {
    const move = this.game.move({
      from: positionToIccs(from),
      to: positionToIccs(to),
    })

    return move ? toMoveResult(move) : null
  }
}

export function createInitialSnapshot(): GameSnapshot {
  return new XiangqiRules().getSnapshot()
}

export function applyMoveToFen(fen: string, from: Position, to: Position): GameSnapshot | null {
  const rules = new XiangqiRules(fen)
  const move = rules.move(from, to)

  return move ? rules.getSnapshot() : null
}
