import { config } from "zod";

// Zod probes for eval with `new Function("")` when a schema is defined, to pick
// a faster parser. The CSP (frontend/Caddyfile) has no 'unsafe-eval', so turn
// the probe off. main.ts imports this module first, because schemas are defined
// when their modules load.
config({ jitless: true });
