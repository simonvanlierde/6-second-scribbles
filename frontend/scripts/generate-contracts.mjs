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
const eventCatalogPath = join(contractsRoot, "room-events.json");
const openApiPath = join(contractsRoot, "openapi.json");
const read = (filename) => JSON.parse(readFileSync(join(contracts, filename), "utf-8"));
const eventCatalog = JSON.parse(readFileSync(eventCatalogPath, "utf-8"));
const openApi = JSON.parse(readFileSync(openApiPath, "utf-8"));
const componentSchemas = openApi?.components?.schemas;

if (!componentSchemas || typeof componentSchemas !== "object") {
  throw new Error("OpenAPI document is missing components.schemas");
}

const getDiscriminatorValues = (schema) => {
  const mapping = schema?.discriminator?.mapping;
  if (!mapping || typeof mapping !== "object") return [];
  return [...new Set(Object.keys(mapping))].sort();
};
const groupEntries = (entries) =>
  Object.entries(
    Object.entries(entries).reduce((groups, [eventType, config]) => {
      const group = config.group;
      groups[group] ??= [];
      groups[group].push(eventType);
      return groups;
    }, {}),
  ).map(([group, eventTypes]) => [group, eventTypes.sort()]);
const summaryEntries = (entries) =>
  Object.fromEntries(
    Object.entries(entries)
      .map(([eventType, config]) => [eventType, config.summary])
      .sort(([left], [right]) => left.localeCompare(right)),
  );
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
  { filename: "server-event.schema.json", name: "ServerEventSchema", typeName: "ServerEvent", module: "esm" },
  { filename: "client-event.schema.json", name: "ClientEventSchema", typeName: "ClientEvent", module: "none" },
];

const [serverSpec, clientSpec] = schemaSpecs;
const serverSchema = read(serverSpec.filename);
const clientSchema = read(clientSpec.filename);
const serverModule = jsonSchemaToZod(serverSchema, { name: serverSpec.name, module: serverSpec.module });
const clientExpression = jsonSchemaToZod(clientSchema, { module: clientSpec.module });
const serverEventTypes = getDiscriminatorValues(serverSchema);
const clientEventTypes = getDiscriminatorValues(clientSchema);
const serverGroups = groupEntries(eventCatalog.server);
const clientGroups = groupEntries(eventCatalog.client);
const serverSummaries = summaryEntries(eventCatalog.server);
const clientSummaries = summaryEntries(eventCatalog.client);

const output = [
  header,
  serverModule,
  `export type ${serverSpec.typeName} = z.infer<typeof ${serverSpec.name}>;`,
  `export type ${serverSpec.typeName}Type = ${serverSpec.typeName}["type"];`,
  `export type ${serverSpec.typeName}Of<TType extends ${serverSpec.typeName}Type> = Extract<${serverSpec.typeName}, { type: TType }>;`,
  `export type ${serverSpec.typeName}Map = { [TType in ${serverSpec.typeName}Type]: ${serverSpec.typeName}Of<TType> };`,
  `export const ${serverSpec.typeName[0].toLowerCase()}${serverSpec.typeName.slice(1)}Types = ${JSON.stringify(serverEventTypes)} as const satisfies readonly ${serverSpec.typeName}Type[];`,
  `export const serverEventGroups = ${JSON.stringify(Object.fromEntries(serverGroups))} as const satisfies Record<string, readonly ServerEventType[]>;`,
  `export const serverEventSummaries = ${JSON.stringify(serverSummaries)} as const satisfies Record<ServerEventType, string>;`,
  `export type ServerEventGroupName = keyof typeof serverEventGroups;`,
  `export type ServerEventGroup<TGroup extends ServerEventGroupName> = ServerEventOf<(typeof serverEventGroups)[TGroup][number]>;`,
  "",
  `export const ${clientSpec.name} = ${clientExpression};`,
  `export type ${clientSpec.typeName} = z.infer<typeof ${clientSpec.name}>;`,
  `export type ${clientSpec.typeName}Type = ${clientSpec.typeName}["type"];`,
  `export type ${clientSpec.typeName}Of<TType extends ${clientSpec.typeName}Type> = Extract<${clientSpec.typeName}, { type: TType }>;`,
  `export type ${clientSpec.typeName}Map = { [TType in ${clientSpec.typeName}Type]: ${clientSpec.typeName}Of<TType> };`,
  `export const ${clientSpec.typeName[0].toLowerCase()}${clientSpec.typeName.slice(1)}Types = ${JSON.stringify(clientEventTypes)} as const satisfies readonly ${clientSpec.typeName}Type[];`,
  `export const clientEventGroups = ${JSON.stringify(Object.fromEntries(clientGroups))} as const satisfies Record<string, readonly ClientEventType[]>;`,
  `export const clientEventSummaries = ${JSON.stringify(clientSummaries)} as const satisfies Record<ClientEventType, string>;`,
  `export type ClientEventGroupName = keyof typeof clientEventGroups;`,
  `export type ClientEventGroup<TGroup extends ClientEventGroupName> = ClientEventOf<(typeof clientEventGroups)[TGroup][number]>;`,
].join("\n");

mkdirSync(generated, { recursive: true });
const protocolPath = join(generated, "protocol.ts");
writeFileSync(protocolPath, output);

const schemaNames = Object.keys(componentSchemas).sort();
const apiBlocks = schemaNames.map((schemaName) => {
  const expression = jsonSchemaToZod(inlineRefs(structuredClone(componentSchemas[schemaName])), { module: "none" });
  return `export const ${schemaName}Schema = ${expression};\nexport type ${schemaName} = z.infer<typeof ${schemaName}Schema>;`;
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
  "",
  `export const apiSchemaNames = ${JSON.stringify(schemaNames)} as const;`,
].join("\n\n");
const apiPath = join(generated, "api.ts");
writeFileSync(apiPath, apiOutput);

console.log(`✓ Generated ${protocolPath}`);
console.log(`✓ Generated ${apiPath}`);
