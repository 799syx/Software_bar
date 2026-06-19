import type { ChatResponse } from "./types";

const DEFAULT_API_BASE = "http://127.0.0.1:8000";

export const API_BASE = (import.meta.env.VITE_API_BASE || DEFAULT_API_BASE).replace(/\/$/, "");

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(message: string, status = 0, code = "network_error") {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

type RequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
  token?: string;
};

function buildHeaders(options: RequestOptions) {
  const headers = new Headers(options.headers);
  if (options.body !== undefined) headers.set("Content-Type", "application/json");
  if (options.token) headers.set("X-Admin-Token", options.token);
  return headers;
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: buildHeaders(options),
      body: options.body === undefined ? undefined : JSON.stringify(options.body)
    });
  } catch {
    throw new ApiError("后端未启动或网络不可达，请先启动 backend/app.py。", 0, "network_error");
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = typeof data?.message === "string" ? data.message : `${options.method || "GET"} ${path} failed`;
    const code = typeof data?.code === "string" ? data.code : "request_failed";
    throw new ApiError(message, response.status, code);
  }
  return data as T;
}

export function apiGet<T>(path: string, token?: string) {
  return apiRequest<T>(path, { token });
}

export function apiPost<T>(path: string, body: unknown, token?: string) {
  return apiRequest<T>(path, { method: "POST", body, token });
}

export function apiPut<T>(path: string, body: unknown, token?: string) {
  return apiRequest<T>(path, { method: "PUT", body, token });
}

export function apiDelete<T>(path: string, token?: string) {
  return apiRequest<T>(path, { method: "DELETE", token });
}

export async function safeApiGet<T>(path: string, fallback: T, token?: string): Promise<T> {
  try {
    return await apiGet<T>(path, token);
  } catch {
    return fallback;
  }
}

export async function apiStreamChat(question: string, onDelta: (text: string) => void): Promise<ChatResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question })
    });
  } catch {
    throw new ApiError("后端未启动或网络不可达，请先启动 backend/app.py。", 0, "network_error");
  }
  if (!response.ok || !response.body) {
    const data = await response.json().catch(() => ({}));
    throw new ApiError(
      typeof data?.message === "string" ? data.message : "流式问答请求失败",
      response.status,
      typeof data?.code === "string" ? data.code : "stream_failed"
    );
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  let eventName = "message";
  let finalRecord: ChatResponse | null = null;

  function consumeEvent(rawEvent: string) {
    const lines = rawEvent.split(/\r?\n/);
    const dataLines: string[] = [];
    eventName = "message";
    for (const line of lines) {
      if (line.startsWith("event:")) eventName = line.slice(6).trim();
      if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
    }
    if (!dataLines.length) return;
    const data = JSON.parse(dataLines.join("\n"));
    if (eventName === "delta") onDelta(String(data.text || ""));
    if (eventName === "done") finalRecord = data as ChatResponse;
  }

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
    const events = buffer.split(/\n\n/);
    buffer = events.pop() || "";
    for (const rawEvent of events) consumeEvent(rawEvent);
    if (done) break;
  }
  if (buffer.trim()) consumeEvent(buffer);
  if (!finalRecord) throw new Error("流式问答未返回完整结果");
  return finalRecord;
}
