#!/usr/bin/env node

import { readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const dir = dirname(fileURLToPath(import.meta.url));
const root = resolve(dir, "../..");
const contractsDir = resolve(root, "contracts");
const eventCatalogPath = resolve(contractsDir, "room-events.json");
const metadataPath = resolve(contractsDir, "room-websocket.metadata.json");
const asyncapiPath = resolve(contractsDir, "room-websocket.asyncapi.yaml");

const eventCatalog = JSON.parse(readFileSync(eventCatalogPath, "utf8"));
const metadata = JSON.parse(readFileSync(metadataPath, "utf8"));

function readExamples(relativePath) {
  return JSON.parse(readFileSync(resolve(dirname(metadataPath), relativePath), "utf8"));
}

function isPlainObject(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function quoteString(value) {
  if (value === "") return '""';
  if (/^[A-Za-z0-9_./{}:-]+$/.test(value)) return value;
  return JSON.stringify(value);
}

function toYaml(value, indent = 0) {
  const pad = "  ".repeat(indent);

  if (Array.isArray(value)) {
    if (value.length === 0) return `${pad}[]`;
    return value
      .map((item) => {
        if (isPlainObject(item) || Array.isArray(item)) {
          const rendered = toYaml(item, indent + 1);
          const [firstLine, ...rest] = rendered.split("\n");
          return `${pad}- ${firstLine.trimStart()}${rest.length ? `\n${rest.join("\n")}` : ""}`;
        }
        return `${pad}- ${formatScalar(item)}`;
      })
      .join("\n");
  }

  if (isPlainObject(value)) {
    return Object.entries(value)
      .map(([key, item]) => {
        if (Array.isArray(item) || isPlainObject(item)) {
          return `${pad}${key}:\n${toYaml(item, indent + 1)}`;
        }
        if (typeof item === "string" && item.includes("\n")) {
          const block = item
            .split("\n")
            .map((line) => `${"  ".repeat(indent + 1)}${line}`)
            .join("\n");
          return `${pad}${key}: |\n${block}`;
        }
        return `${pad}${key}: ${formatScalar(item)}`;
      })
      .join("\n");
  }

  return `${pad}${formatScalar(value)}`;
}

function formatScalar(value) {
  if (typeof value === "string") return quoteString(value);
  if (value === null) return "null";
  return String(value);
}

const clientExamples = readExamples(metadata.messages.clientEvent.examplesRef);
const serverExamples = readExamples(metadata.messages.serverEvent.examplesRef);
const exampleMap = {
  client: Object.fromEntries(clientExamples.map((example) => [example.payload.type, example])),
  server: Object.fromEntries(serverExamples.map((example) => [example.payload.type, example])),
};

function eventMessageKey(direction, eventType) {
  return `${direction}_${eventType}`;
}

function eventSchemaRef(direction, eventType) {
  return `jsonschema/${direction}-events/${eventType}.schema.json`;
}

function buildEventMessages(direction) {
  return Object.fromEntries(
    Object.entries(eventCatalog[direction]).map(([eventType, config]) => [
      eventMessageKey(direction, eventType),
      {
        name: eventType,
        title: eventType,
        summary: config.summary,
        contentType: "application/json",
        payload: { $ref: eventSchemaRef(direction, eventType) },
        examples: exampleMap[direction][eventType] ? [exampleMap[direction][eventType]] : [],
      },
    ]),
  );
}

function buildOperationMessageRefs(direction) {
  return Object.keys(eventCatalog[direction]).map((eventType) => ({
    $ref: `#/components/messages/${eventMessageKey(direction, eventType)}`,
  }));
}

const document = {
  asyncapi: "3.1.0",
  info: {
    ...metadata.info,
    tags: metadata.tags.map((name) => ({ name })),
  },
  servers: {
    [metadata.server.name]: {
      host: metadata.server.host,
      protocol: metadata.server.protocol,
      pathname: metadata.server.pathname,
      description: metadata.server.description,
    },
  },
  channels: {
    [metadata.channel.name]: {
      address: metadata.channel.address,
      title: metadata.channel.title,
      summary: metadata.channel.summary,
      parameters: {
        [metadata.channel.parameterName]: {
          description: metadata.channel.parameterDescription,
        },
      },
      messages: {
        clientEvent: { $ref: "#/components/messages/clientEvent" },
        serverEvent: { $ref: "#/components/messages/serverEvent" },
      },
    },
  },
  operations: {
    sendClientEvent: {
      action: metadata.operations.sendClientEvent.action,
      title: metadata.operations.sendClientEvent.title,
      summary: metadata.operations.sendClientEvent.summary,
      channel: { $ref: `#/channels/${metadata.channel.name}` },
      messages: buildOperationMessageRefs("client"),
    },
    receiveServerEvent: {
      action: metadata.operations.receiveServerEvent.action,
      title: metadata.operations.receiveServerEvent.title,
      summary: metadata.operations.receiveServerEvent.summary,
      channel: { $ref: `#/channels/${metadata.channel.name}` },
      messages: buildOperationMessageRefs("server"),
    },
  },
  components: {
    messages: {
      ...buildEventMessages("client"),
      ...buildEventMessages("server"),
      clientEvent: {
        name: "clientEvent",
        title: metadata.messages.clientEvent.title,
        summary: `${metadata.messages.clientEvent.summary} Event types: ${Object.keys(eventCatalog.client).join(", ")}.`,
        contentType: "application/json",
        payload: { $ref: metadata.messages.clientEvent.schemaRef },
        examples: clientExamples,
      },
      serverEvent: {
        name: "serverEvent",
        title: metadata.messages.serverEvent.title,
        summary: `${metadata.messages.serverEvent.summary} Event types: ${Object.keys(eventCatalog.server).join(", ")}.`,
        contentType: "application/json",
        payload: { $ref: metadata.messages.serverEvent.schemaRef },
        examples: serverExamples,
      },
    },
  },
};

writeFileSync(asyncapiPath, `${toYaml(document)}\n`);
console.log("✓ Generated contracts/room-websocket.asyncapi.yaml");
