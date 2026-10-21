import type { ZodType } from "zod";
import { API_HOST } from "@/config/gameConfig";

type ApiRequestOptions<T> = {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  schema?: ZodType<T>;
};

/** A non-2xx response; `message` is the backend's `detail` when it sent one. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

export async function apiRequest<T>(path: string, options: ApiRequestOptions<T> = {}): Promise<T> {
  const response = await fetch(`${API_HOST}${path}`, {
    method: options.method ?? "GET",
    credentials: "include",
    headers: options.body ? { "Content-Type": "application/json" } : undefined,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });

  if (response.ok === false) {
    let detail = `Request failed with status ${response.status}`;

    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) {
        detail = payload.detail;
      }
    } catch {
      /* keep generic error */
    }

    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const payload = await response.json();
  return options.schema ? options.schema.parse(payload) : (payload as T);
}
