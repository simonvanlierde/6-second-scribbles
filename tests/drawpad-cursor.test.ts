/* eslint-disable @typescript-eslint/no-explicit-any */
/* eslint-disable import/no-unresolved */
import { describe, expect, it } from 'vitest'

import { clientToCanvasCoords } from '../src/utils/canvasCoords'

function createFakeCanvas(left = 10, top = 20) {
  const el: any = {
    getBoundingClientRect: () => ({ left, top, width: 200, height: 100 }),
  }
  return el as HTMLCanvasElement
}

describe('clientToCanvasCoords', () => {
  it('maps client coordinates to canvas CSS coordinates using bounding rect offsets', () => {
    const fake = createFakeCanvas(100, 50)

    const result = clientToCanvasCoords(fake, 150, 80)

    // clientX 150 - rect.left 100 => x 50
    // clientY 80 - rect.top 50 => y 30
    expect(result).toEqual({ x: 50, y: 30 })
  })
})
