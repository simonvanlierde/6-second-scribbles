#!/usr/bin/env node

import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { z } from "zod";

const dir = dirname(fileURLToPath(import.meta.url));
const root = resolve(dir, "../..");
const contractsDir = resolve(root, "contracts");
const eventCatalogPath = resolve(contractsDir, "room-events.json");
const metadataPath = resolve(contractsDir, "room-websocket.metadata.json");
const asyncapiPath = resolve(contractsDir, "room-websocket.asyncapi.yaml");
const clientSchemaPath = resolve(
	contractsDir,
	"jsonschema/client-event.schema.json",
);
const serverSchemaPath = resolve(
	contractsDir,
	"jsonschema/server-event.schema.json",
);
const clientEventSchemaDir = resolve(contractsDir, "jsonschema/client-events");
const serverEventSchemaDir = resolve(contractsDir, "jsonschema/server-events");
const clientExamplesPath = resolve(contractsDir, "client-events.examples.json");
const serverExamplesPath = resolve(contractsDir, "server-events.examples.json");

function readJson(path) {
	return JSON.parse(readFileSync(path, "utf8"));
}

function formatIssues(issues) {
	return issues
		.map((issue) => {
			const path = issue.path.length > 0 ? issue.path.join(".") : "<root>";
			return `${path}: ${issue.message}`;
		})
		.join("; ");
}

function previewPayload(payload, maxLength = 240) {
	const serialized = JSON.stringify(payload);
	if (!serialized) {
		return "<unserializable payload>";
	}
	if (serialized.length <= maxLength) {
		return serialized;
	}
	return `${serialized.slice(0, maxLength)}...`;
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
			const message = formatIssues(result.error.issues);
			const payloadType = example.payload?.type ?? "<missing type>";
			const exampleName =
				typeof example.name === "string" ? example.name : "<unnamed>";
			throw new Error(
				`${label} example ${index} (${exampleName}, type=${payloadType}) is invalid: ${message}; payload=${previewPayload(example.payload)}`,
			);
		}
	}
}

function validateEventSchemas(direction, schemaDirPath, examplesPath) {
	const indexPath = resolve(schemaDirPath, "index.json");
	const index = readJson(indexPath);
	const examples = readJson(examplesPath);

	for (const [eventType, filename] of Object.entries(index)) {
		const schemaPath = resolve(schemaDirPath, filename);
		const validator = z.fromJSONSchema(readJson(schemaPath));
		const matchingExamples = examples.filter(
			(example) => example.payload?.type === eventType,
		);

		readFileSync(schemaPath, "utf8");
		for (const example of matchingExamples) {
			const result = validator.safeParse(example.payload);
			if (!result.success) {
				const message = formatIssues(result.error.issues);
				const exampleName =
					typeof example.name === "string" ? example.name : "<unnamed>";
				throw new Error(
					`${direction} event schema ${eventType} rejected example ${exampleName}: ${message}; payload=${previewPayload(example.payload)}`,
				);
			}
		}
	}
}

function validateAsyncApiRefs() {
	const eventCatalog = readJson(eventCatalogPath);
	readJson(metadataPath);
	const asyncapi = readFileSync(asyncapiPath, "utf8");
	const refs = [...asyncapi.matchAll(/^\s+\$ref:\s+(.+)$/gm)].map((match) =>
		match[1].trim(),
	);
	const localFileRefs = refs.filter((ref) => ref.startsWith("../"));

	for (const ref of localFileRefs) {
		const targetPath = resolve(dirname(asyncapiPath), ref);
		readFileSync(targetPath, "utf8");
	}

	const requiredSnippets = [
		"asyncapi: 3.1.0",
		"clientEvent",
		"serverEvent",
		"jsonschema/client-event.schema.json",
		"jsonschema/server-event.schema.json",
	];

	for (const snippet of requiredSnippets) {
		if (!asyncapi.includes(snippet)) {
			throw new Error(
				`AsyncAPI contract is missing expected content: ${snippet}`,
			);
		}
	}

	const expectedClientTypes = Object.keys(eventCatalog.client);
	const expectedServerTypes = Object.keys(eventCatalog.server);
	for (const eventType of [...expectedClientTypes, ...expectedServerTypes]) {
		if (!asyncapi.includes(eventType)) {
			throw new Error(
				`AsyncAPI contract is missing catalog event type: ${eventType}`,
			);
		}
	}
}

function validateCatalogAgainstSchemas() {
	const eventCatalog = readJson(eventCatalogPath);
	const clientSchema = readJson(clientSchemaPath);
	const serverSchema = readJson(serverSchemaPath);
	const clientIndex = readJson(resolve(clientEventSchemaDir, "index.json"));
	const serverIndex = readJson(resolve(serverEventSchemaDir, "index.json"));
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

	if (
		JSON.stringify(Object.keys(clientIndex).sort()) !==
		JSON.stringify(expectedClientTypes)
	) {
		throw new Error(`Client per-event schemas do not match contract catalog.`);
	}

	if (
		JSON.stringify(Object.keys(serverIndex).sort()) !==
		JSON.stringify(expectedServerTypes)
	) {
		throw new Error(`Server per-event schemas do not match contract catalog.`);
	}

	for (const [direction, entries] of Object.entries(eventCatalog)) {
		for (const [eventType, config] of Object.entries(entries)) {
			if (!config || typeof config !== "object") {
				throw new Error(
					`${direction} catalog entry ${eventType} must be an object.`,
				);
			}
			if (typeof config.group !== "string" || config.group.length === 0) {
				throw new Error(
					`${direction} catalog entry ${eventType} must include a non-empty group.`,
				);
			}
			if (typeof config.summary !== "string" || config.summary.length === 0) {
				throw new Error(
					`${direction} catalog entry ${eventType} must include a non-empty summary.`,
				);
			}
		}
	}
}

function validateExampleCoverage() {
	const eventCatalog = readJson(eventCatalogPath);
	const clientExamples = readJson(clientExamplesPath);
	const serverExamples = readJson(serverExamplesPath);
	const clientExampleTypes = new Set(
		clientExamples.map((example) => example.payload?.type).filter(Boolean),
	);
	const serverExampleTypes = new Set(
		serverExamples.map((example) => example.payload?.type).filter(Boolean),
	);

	for (const eventType of Object.keys(eventCatalog.client)) {
		if (
			!clientExampleTypes.has(eventType) &&
			eventCatalog.client[eventType].group === "connection"
		) {
			throw new Error(
				`Client connection event ${eventType} should have an example.`,
			);
		}
	}

	for (const eventType of Object.keys(eventCatalog.server)) {
		if (
			!serverExampleTypes.has(eventType) &&
			eventCatalog.server[eventType].group === "connection"
		) {
			throw new Error(
				`Server connection event ${eventType} should have an example.`,
			);
		}
	}
}

validateAsyncApiRefs();
validateCatalogAgainstSchemas();
validateExamples(clientSchemaPath, clientExamplesPath, "client");
validateExamples(serverSchemaPath, serverExamplesPath, "server");
validateEventSchemas("client", clientEventSchemaDir, clientExamplesPath);
validateEventSchemas("server", serverEventSchemaDir, serverExamplesPath);
validateExampleCoverage();

console.log(
	"✓ Validated contract catalog, coverage, AsyncAPI refs, and contract examples",
);
