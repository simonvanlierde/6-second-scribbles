// src/utils/logger.ts
import consola from 'consola'
import pino from 'pino'

import { DEBUG } from '../config/debug'

// Simple facade: use pino on Node (server) and consola in the browser (client).
// Keeps the default export with debug/info/warn/error and a setLogLevel helper.

type LogLevel = 'debug' | 'info' | 'warn' | 'error'

const isNode = typeof window === 'undefined'

// default level
const defaultLevel: LogLevel = DEBUG ? 'debug' : 'info'

// Browser implementation using consola
function createBrowserLogger(level: LogLevel) {
  const l = consola.withScope('app')
  // consola's level property typing is not strict here; narrow with a minimal cast
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  ;(l as any).level = level
  // browser retains multi-arg behavior; no formatting helper needed here

  return {
    debug: (...args: unknown[]) => {
      // preserve multi-arg behavior in browser so DevTools can inspect objects
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      ;(l as any).debug(...(args as any[]))
    },
    info: (...args: unknown[]) => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      ;(l as any).info(...(args as any[]))
    },
    warn: (...args: unknown[]) => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      ;(l as any).warn(...(args as any[]))
    },
    error: (...args: unknown[]) => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      ;(l as any).error(...(args as any[]))
    },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    setLogLevel: (newLevel: LogLevel) => { (l as any).level = newLevel },
    // expose raw consola instance for advanced uses or plugin equality
    __raw: l,
  }
}

// Node/server implementation using pino
function createServerLogger(level: LogLevel) {
  // Use pino-pretty in dev for readable output when DEBUG is true
  const p = DEBUG
    ? pino({ level }, pino.transport({ target: 'pino-pretty' }))
    : pino({ level })

  function formatArgs(args: unknown[]) {
    return args
      .map((a) => {
        if (a instanceof Error) return a.stack || a.message
        try {
          return typeof a === 'string' ? a : JSON.stringify(a)
        } catch {
          return String(a)
        }
      })
      .join(' ')
  }

  function callPino(method: 'debug' | 'info' | 'warn' | 'error', args: unknown[]) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  if (args.length === 0) return (p as any)[method]()
    const first = args[0]
    const rest = args.slice(1)

    // If first arg is an Error, pass it as first param to pino (pino prints error stack)
    if (first instanceof Error) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  if (rest.length) return (p as any)[method](first, formatArgs(rest))
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return (p as any)[method](first)
    }

    // If first arg is a plain object, send it as structured data to pino
    if (first && typeof first === 'object' && !Array.isArray(first)) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  if (rest.length) return (p as any)[method](first, formatArgs(rest))
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return (p as any)[method](first)
    }

    // Otherwise, serialize everything into a message string
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return (p as any)[method](formatArgs(args))
  }

  return {
    debug: (...args: unknown[]) => callPino('debug', args),
    info: (...args: unknown[]) => callPino('info', args),
    warn: (...args: unknown[]) => callPino('warn', args),
    error: (...args: unknown[]) => callPino('error', args),
    setLogLevel: (newLevel: LogLevel) => { p.level = newLevel },
  }
}

const impl = isNode ? createServerLogger(defaultLevel) : createBrowserLogger(defaultLevel)

export default impl
