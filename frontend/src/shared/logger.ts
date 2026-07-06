/**
 * Thin console wrapper so app code never calls `console` directly — Biome's
 * `noConsole` stays enforced everywhere except this one module. `debug`/`info`
 * are DEV-only; `warn`/`error` always emit.
 */
const DEV = import.meta.env.DEV;

type LogFn = (...args: unknown[]) => void;

export interface Logger {
  debug: LogFn;
  info: LogFn;
  warn: LogFn;
  error: LogFn;
}

export function createLogger(scope: string): Logger {
  const tag = `[${scope}]`;
  return {
    debug: (...args) => {
      if (DEV) console.debug(tag, ...args);
    },
    info: (...args) => {
      if (DEV) console.info(tag, ...args);
    },
    warn: (...args) => console.warn(tag, ...args),
    error: (...args) => console.error(tag, ...args),
  };
}
