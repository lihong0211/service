declare module 'xiangqi.js' {
  export interface XiangqiPiece {
    type: string
    color: 'r' | 'b'
  }

  export interface XiangqiMove {
    color: 'r' | 'b'
    from: string
    to: string
    flags: string
    piece: string
    captured?: string
    iccs: string
  }

  export class Xiangqi {
    constructor(fen?: string)
    board(): Array<Array<XiangqiPiece | null>>
    fen(): string
    history(options?: { verbose?: boolean }): XiangqiMove[] | string[]
    in_check(): boolean
    in_checkmate(): boolean
    in_draw(): boolean
    in_stalemate(): boolean
    load(fen: string): boolean
    move(move: string | { from: string; to: string }): XiangqiMove | null
    moves(options?: { square?: string; verbose?: boolean }): XiangqiMove[] | string[]
    reset(): void
    turn(): 'r' | 'b'
    undo(): XiangqiMove | null
  }
}
