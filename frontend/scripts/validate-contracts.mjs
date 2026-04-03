#!/usr/bin/env node

import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { z } from "zod";

const dir = dirname(fileURLToPath(import.meta.url));
const root = resolve(dir, "../..");
const contractsDir = resolve(root, "contracts");
const eventCatalogPath = resolve(contractsDir, "catalog/room-events.json");
const metadataPath = resolve(contractsDir, "asyncapi/room-websocket.metadata.json");
const asyncapiPath = resolve(contractsDir, "asyncapi/room-websocket.asyncapi.yaml");
const clientSchemaPath = resolve(contractsDir, "jsonschema/client-event.schema.json");
const serverSchemaPath = resolve(contractsDir, "jsonschema/server-event.schema.json");
const clientExamplesPath = resolve(contractsDir, "examples/client-events.json");
const serverExamplesPath = resolve(contractsDir, "examples/server-events.json");

function readJson(path) {
  return JSON.parse(readFileSync(path, "utf8"));
}

function validateExamples(schemaPath, examplesPath, label) {
  const schema = readJson(schemaPath);
  const examples = readJson(examplesPath);
  const validator = z.fromJSONSchema(schema);

  if (!Array.isArray(examples)) {
    throw new Error(`${label} examples must be an array.`);
  }

  for (const [index, example] of examples.entries()) {
    if (!example || typeof example !== "object" || !("payload" in example)) {
      throw new Error(`${label} example ${index} must include a payload.`);
    }

    const result = validator.safeParse(example.payload);
    if (!result.success) {
      const message = result.error.issues.map((issue) => `${issue.path.join(".")}: ${issue.message}`).join("; ");
      throw new Error(`${label} example ${index} is invalid: ${message}`);
    }
  }
}

function validateAsyncApiRefs() {
  const eventCatalog = readJson(eventCatalogPath);
  readJson(metadataPath);
  const asyncapi = readFileSync(asyncapiPath, "utf8");
  const refs = [...asyncapi.matchAll(/^\s+\$ref:\s+(.+)$/gm)].map((match) => match[1].trim());
  const localFileRefs = refs.filter((ref) => ref.startsWith("../"));

  for (const ref of localFileRefs) {
    const targetPath = resolve(dirname(asyncapiPath), ref);
    readFileSync(targetPath, "utf8");
  }

  const requiredSnippets = [
    "asyncapi: 3.1.0",
    "clientEvent",
    "serverEvent",
    "../jsonschema/client-event.schema.json",
    "../jsonschema/server-event.schema.json",
  ];

  for (const snippet of requiredSnippets) {
    if (!asyncapi.includes(snippet)) {
      throw new Error(`AsyncAPI contract is missing expected content: ${snippet}`);
    }
  }

  const expectedClientTypes = Object.keys(eventCatalog.client);
  const expectedServerTypes = Object.keys(eventCatalog.server);
  for (const eventType of [...expectedClientTypes, ...expectedServerTypes]) {
    if (!asyncapi.includes(eventType)) {
      throw new Error(`AsyncAPI contract is missing catalog event type: ${eventType}`);
    }
  }
}

function validateCatalogAgainstSchemas() {
  const eventCatalog = readJson(eventCatalogPath);
  const clientSchema = readJson(clientSchemaPath);
  const serverSchema = readJson(serverSchemaPath);
  const clientTypes = Object.keys(clientSchema.discriminator.mapping).sort();
  const serverTypes = Object.keys(serverSchema.discriminator.mapping).sort();
  const expectedClientTypes = Object.keys(eventCatalog.client).sort();
  const expectedServerTypes = Object.keys(eventCatalog.server).sort();

  if (JSON.stringify(clientTypes) !== JSON.stringify(expectedClientTypes)) {
    throw new Error(`Client schema types do not match contract catalog.`);
  }

  if (JSON.stringify(serverTypes) !== JSON.stringify(expectedServerTypes)) {
    throw new Error(`Server schema types do not match contract catalog.`);
  }

  for (const [direction, entries] of Object.entries(eventCatalog)) {
    for (const [eventType, config] of Object.entries(entries)) {
      if (!config || typeof config !== "object") {
        throw new Error(`${direction} catalog entry ${eventType} must be an object.`);
      }
      if (typeof config.group !== "string" || config.group.length === 0) {
        throw new Error(`${direction} catalog entry ${eventType} must include a non-empty group.`);
      }
      if (typeof config.summary !== "string" || config.summary.length === 0) {
        throw new Error(`${direction} catalog entry ${eventType} must include a non-empty summary.`);
      }
    }
  }
}

function validateExampleCoverage() {
  const eventCatalog = readJson(eventCatalogPath);
  const clientExamples = readJson(clientExamplesPath);
  const serverExamples = readJson(serverExamplesPath);
  const clientExampleTypes = new Set(clientExamples.map((example) => example.payload?.type).filter(Boolean));
  const serverExampleTypes = new Set(serverExamples.map((example) => example.payload?.type).filter(Boolean));

  for (const eventType of Object.keys(eventCatalog.client)) {
    if (!clientExampleTypes.has(eventType) && eventCatalog.client[eventType].group === "connection") {
      throw new Error(`Client connection event ${eventType} should have an example.`);
    }
  }

  for (const eventType of Object.keys(eventCatalog.server)) {
    if (!serverExampleTypes.has(eventType) && eventCatalog.server[eventType].group === "connection") {
      throw new Error(`Server connection event ${eventType} should have an example.`);
    }
  }
}

validateAsyncApiRefs();
validateCatalogAgainstSchemas();
validateExamples(clientSchemaPath, clientExamplesPath, "client");
validateExamples(serverSchemaPath, serverExamplesPath, "server");
validateExampleCoverage();

console.log("✓ Validated contract catalog, coverage, AsyncAPI refs, and contract examples");
