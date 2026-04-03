#!/usr/bin/env node
// Converts the pre-processed JSON Schemas into a Zod TypeScript file.
// Run via: npm run contracts:types  (contract export runs first)
//
// Note: Zod 4's `z.fromJSONSchema()` is useful for runtime validation, but its
// current type signature returns a generic `ZodType`, so it does not preserve
// the discriminated-union TypeScript inference we want here.

import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { jsonSchemaToZod } from "json-schema-to-zod";

const dir = dirname(fileURLToPath(import.meta.url));
const generated = join(dir, "../src/generated");
const contracts = join(dir, "../../contracts/jsonschema");
const eventCatalogPath = join(dir, "../../contracts/room-events.json");
const read = (filename) => JSON.parse(readFileSync(join(contracts, filename), "utf-8"));
const eventCatalog = JSON.parse(readFileSync(eventCatalogPath, "utf-8"));
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

const header = `\
// ⚠️  AUTO-GENERATED — do not edit.
// Contract:        contracts/room-websocket.asyncapi.yaml
// Generated from:  backend/app/rooms/protocol.py
// Source schemas:  contracts/jsonschema/
// Regenerate:      npm run contracts:types
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

writeFileSync(join(generated, "protocol.ts"), output);

console.log("✓ Generated frontend/src/generated/protocol.ts");
