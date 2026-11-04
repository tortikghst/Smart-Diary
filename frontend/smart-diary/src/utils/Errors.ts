// src/utils/errors.ts

/** Формат ошибки бэкенда: {"detail": "Текст"} */
export interface ApiErrorBody {
  detail: string;
}

/** Базовая ошибка API с HTTP-статусом и телом ответа */
export class ApiError extends Error {
  readonly status: number;
  readonly body: ApiErrorBody | null;

  constructor(status: number, message: string, body: ApiErrorBody | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }

  get isUnauthorized() { return this.status === 401; }
  get isForbidden()    { return this.status === 403; }
  get isNotFound()     { return this.status === 404; }
  get isConflict()     { return this.status === 409; }
  get isValidation()   { return this.status === 422; }
}

/** Ошибка сети (fetch упал, нет интернета, CORS) */
export class NetworkError extends Error {
  constructor(message = "Сервер недоступен. Проверьте интернет.") {
    super(message);
    this.name = "NetworkError";
  }
}

/** Ответ пришёл, но это не JSON, хотя мы ожидали JSON */
export class UnexpectedResponseError extends Error {
  constructor(message = "Неожиданный ответ от сервера") {
    super(message);
    this.name = "UnexpectedResponseError";
  }
}

/**
 * Безопасно достаёт строку ошибки из ответа бэкенда.
 * Поддерживает:
 *  - {"detail": "строка"}
 *  - {"detail": [{msg: "...", loc: [...]}, ...]} (валидация Pydantic)
 */
function extractDetail(body: unknown): string | null {
  if (!body || typeof body !== "object") return null;

  const detail = (body as Record<string, unknown>).detail;

  if (typeof detail === "string") return detail;

  if (Array.isArray(detail)) {
    const first = detail[0];
    if (first && typeof first === "object" && "msg" in first) {
      const loc = Array.isArray((first as any).loc)
        ? (first as any).loc.filter((p: unknown) => p !== "body").join(".")
        : "";
      const msg = String((first as any).msg);
      return loc ? `Ошибка валидации (${loc}): ${msg}` : `Ошибка валидации: ${msg}`;
    }
    return "Ошибка валидации";
  }

  return null;
}

/**
 * Превращает HTTP-ответ с ошибкой (response.ok === false) в ApiError.
 * Никогда не бросает — возвращает валидный объект ошибки в любом случае.
 */
export async function parseApiError(response: Response): Promise<ApiError> {
  let body: ApiErrorBody | null = null;
  let message = `Ошибка ${response.status}`;

  try {
    const text = await response.text();
    if (text) {
      try {
        const json = JSON.parse(text);
        const detail = extractDetail(json);
        if (detail) {
          message = detail;
          body = { detail };
        }
      } catch {
        // тело — не JSON, показываем как текст (обрезанный)
        message = text.slice(0, 200);
      }
    }
  } catch {
    // совсем не удалось прочитать тело — оставляем дефолтное сообщение
  }

  return new ApiError(response.status, message, body);
}

/**
 * Универсальный человекочитаемый текст для любого выброшенного значения.
 * Используется в UI (тосты, плашки, тексты ошибок на странице).
 */
export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof NetworkError) return error.message;
  if (error instanceof UnexpectedResponseError) return error.message;
  if (error instanceof Error) return error.message;
  if (typeof error === "string") return error;
  return "Неизвестная ошибка";
}