// src/utils/api.ts
import {
  ApiError,
  NetworkError,
  UnexpectedResponseError,
  parseApiError,
} from "./errors";

const BASE_URL = "/api/v1";
const TOKEN_KEY = "access_token";

export const auth = {
  getToken: () => localStorage.getItem(TOKEN_KEY),
  setToken: (token: string) => localStorage.setItem(TOKEN_KEY, token),
  clearToken: () => localStorage.removeItem(TOKEN_KEY),
};

interface FetchOptions extends Omit<RequestInit, "body" | "headers"> {
  json?: unknown;
  headers?: Record<string, string>;
  skipAuth?: boolean;
}

export async function apiFetch<T = unknown>(
  path: string,
  options: FetchOptions = {},
): Promise<T> {
  const { json, headers = {}, skipAuth, ...rest } = options;
  const token = auth.getToken();

  const finalHeaders: Record<string, string> = {
    ...(json !== undefined ? { "Content-Type": "application/json" } : {}),
    ...(token && !skipAuth ? { Authorization: `Bearer ${token}` } : {}),
    ...headers,
  };

  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      ...rest,
      headers: finalHeaders,
      body: json !== undefined ? JSON.stringify(json) : undefined,
    });
  } catch {
    throw new NetworkError();
  }

  if (!response.ok) {
    const error: ApiError = await parseApiError(response);

    if (error.isUnauthorized && !path.includes("/auth/login")) {
      auth.clearToken();
      window.location.href = "/";
    }
    throw error;
  }

  if (response.status === 204) return undefined as T;

  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    return (await response.blob()) as unknown as T;
  }

  try {
    return (await response.json()) as T;
  } catch {
    throw new UnexpectedResponseError();
  }
}