export interface Position {
  row: number
  col: number
}

export type Color = 'red' | 'black'

export type PieceType =
  | 'king'
  | 'advisor'
  | 'elephant'
  | 'horse'
  | 'chariot'
  | 'cannon'
  | 'soldier'

export type GameStatus = 'playing' | 'check' | 'checkmate' | 'draw' | 'stalemate'

export interface Piece {
  color: Color
  type: PieceType
}

export interface MoveResult {
  color: Color
  from: Position
  to: Position
  piece: PieceType
  captured?: PieceType
  iccs: string
}

export interface GameSnapshot {
  board: Array<Array<Piece | null>>
  turn: Color
  status: GameStatus
  history: MoveResult[]
  fen: string
}

export interface Player {
  id: string
  nickname: string
  avatarUrl?: string
}

export interface Session {
  token: string
  playerId: string
  createdAt: string
  expiresAt: string
}

export interface Room {
  id: string
  redPlayerId: string
  blackPlayerId: string
  snapshot: GameSnapshot
  createdAt: string
  updatedAt: string
}

export interface MoveCommand {
  roomId: string
  playerId: string
  from: Position
  to: Position
  clientMoveId: string
}
