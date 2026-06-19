import { afterEach, describe, expect, it, vi } from "vitest";
import { apiGet, apiPost } from "../api";
import type { ChatResponse, LocationResolveResponse, OperationsOverview } from "../types";

function mockFetchJson(payload: unknown, status = 200) {
  const fetchMock = vi.fn<(input: RequestInfo | URL, init?: RequestInit) => Promise<Response>>(
    async () => new Response(JSON.stringify(payload), { status, headers: { "Content-Type": "application/json" } })
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("api demo flows", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("sends the admin token for management dashboard requests", async () => {
    const fetchMock = mockFetchJson({ available: true, metrics: [] });

    await apiGet<OperationsOverview>("/api/admin/operations/overview", "unit-admin-token");

    const [, init] = fetchMock.mock.calls[0];
    const headers = init?.headers as Headers;
    expect(fetchMock.mock.calls[0][0]).toBe("http://127.0.0.1:8000/api/admin/operations/overview");
    expect(headers.get("X-Admin-Token")).toBe("unit-admin-token");
  });

  it("requests location resolution for scanned spot codes", async () => {
    const fetchMock = mockFetchJson({ ok: true, anchor: { id: 12, name: "LS-012" }, confidence: "high", message: "ok" });

    const result = await apiGet<LocationResolveResponse>(`/api/location/resolve?code=${encodeURIComponent("LS-012")}`);

    expect(result.ok).toBe(true);
    expect(result.confidence).toBe("high");
    expect(String(fetchMock.mock.calls[0][0])).toContain("/api/location/resolve?code=LS-012");
  });

  it("posts visitor questions as JSON for the QA flow", async () => {
    const fetchMock = mockFetchJson({
      id: "chat-1",
      question: "景区几点开放？",
      answer: "9:00 开放",
      relatedSpots: [],
      sourceRefs: [],
      intent: "开放时间",
      confidence: 0.9,
      sentiment: "neutral"
    });

    const result = await apiPost<ChatResponse>("/api/chat", { question: "景区几点开放？" });

    const [, init] = fetchMock.mock.calls[0];
    const headers = init?.headers as Headers;
    expect(init?.method).toBe("POST");
    expect(headers.get("Content-Type")).toBe("application/json");
    expect(JSON.parse(String(init?.body))).toEqual({ question: "景区几点开放？" });
    expect(result.answer).toContain("开放");
  });
});
