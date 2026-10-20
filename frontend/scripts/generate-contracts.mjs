#!/usr/bin/env node
// Generate shared frontend contract artifacts.

import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { jsonSchemaToZod } from "json-schema-to-zod";

const dir = dirname(fileURLToPath(import.meta.url));
const contractsRoot = resolve(dir, process.env.CONTRACTS_DIR ?? "../../contracts");
const generated = resolve(dir, process.env.FRONTEND_GENERATED_DIR ?? "../src/generated");
const contracts = join(contractsRoot, "jsonschema");
const openApiPath = join(contractsRoot, "openapi.json");
const read = (filename) => JSON.parse(readFileSync(join(contracts, filename), "utf-8"));
const openApi = JSON.parse(readFileSync(openApiPath, "utf-8"));
const componentSchemas = openApi?.components?.schemas;

if (!componentSchemas || typeof componentSchemas !== "object") {
  throw new Error("OpenAPI document is missing components.schemas");
}

const refPrefix = "#/components/schemas/";

function inlineRefs(node) {
  if (Array.isArray(node)) {
    return node.map((item) => inlineRefs(item));
  }

  if (!node || typeof node !== "object") {
    return node;
  }

  if (typeof node.$ref === "string") {
    const schemaName = node.$ref.replace(refPrefix, "");
    const target = componentSchemas[schemaName];
    if (!target) {
      throw new Error(`Unknown schema ref: ${node.$ref}`);
    }
    return inlineRefs(structuredClone(target));
  }

  return Object.fromEntries(Object.entries(node).map(([key, value]) => [key, inlineRefs(value)]));
}

const header = `\
// ⚠️  AUTO-GENERATED — do not edit.
// Contract:        backend/app/rooms/protocol.py
// Generated from:  backend/app/rooms/protocol.py
// Source schemas:  contracts/jsonschema/
// Regenerate:      just generate-contracts
`;

const schemaSpecs = [
  {
    filename: "server-event.schema.json",
    name: "ServerEventSchema",
    typeName: "ServerEvent",
    module: "esm",
  },
  {
    filename: "client-event.schema.json",
    name: "ClientEventSchema",
    typeName: "ClientEvent",
    module: "none",
  },
];

const [serverSpec, clientSpec] = schemaSpecs;
const serverSchema = read(serverSpec.filename);
const clientSchema = read(clientSpec.filename);
const serverModule = jsonSchemaToZod(serverSchema, {
  name: serverSpec.name,
  module: serverSpec.module,
});
const clientExpression = jsonSchemaToZod(clientSchema, {
  module: clientSpec.module,
});

// Only what the app imports: the schemas that validate each direction, the event
// unions, and ServerEventOf to pick one server event out of the union.
const output = [
  header,
  serverModule,
  `export type ${serverSpec.typeName} = z.infer<typeof ${serverSpec.name}>;`,
  `export type ${serverSpec.typeName}Of<TType extends ${serverSpec.typeName}["type"]> = Extract<${serverSpec.typeName}, { type: TType }>;`,
  "",
  `export const ${clientSpec.name} = ${clientExpression};`,
  `export type ${clientSpec.typeName} = z.infer<typeof ${clientSpec.name}>;`,
].join("\n");

mkdirSync(generated, { recursive: true });
const protocolPath = join(generated, "protocol.ts");
writeFileSync(protocolPath, output);

// The OpenAPI schemas the app uses, and how: "schema" to validate a response,
// "type" for the TypeScript type alone. Add a name here before importing it.
const apiExports = {
  CreateRoomResponse: ["schema"],
  Difficulty: ["type"],
  GamePhase: ["type"],
  LocaleAvailabilityItem: ["schema", "type"],
  QuickPlayResponse: ["schema"],
  RoomStatusResponse: ["schema"],
  UserResponse: ["schema", "type"],
};
const apiBlocks = Object.entries(apiExports).map(([schemaName, kinds]) => {
  const schema = componentSchemas[schemaName];
  if (!schema) throw new Error(`OpenAPI document has no schema ${schemaName}`);
  const expression = jsonSchemaToZod(inlineRefs(structuredClone(schema)), { module: "none" });
  const lines = [`${kinds.includes("schema") ? "export " : ""}const ${schemaName}Schema = ${expression};`];
  if (kinds.includes("type")) lines.push(`export type ${schemaName} = z.infer<typeof ${schemaName}Schema>;`);
  return lines.join("\n");
});
const apiOutput = [
  `// ⚠️  AUTO-GENERATED — do not edit.`,
  `// Contract:        contracts/openapi.json`,
  `// Generated from:  backend/app/main.py`,
  `// Source schemas:  contracts/openapi.json#/components/schemas`,
  `// Regenerate:      just generate-contracts`,
  "",
  'import { z } from "zod";',
  "",
  ...apiBlocks,
].join("\n\n");
const apiPath = join(generated, "api.ts");
writeFileSync(apiPath, apiOutput);

console.log(`✓ Generated ${protocolPath}`);
console.log(`✓ Generated ${apiPath}`);
