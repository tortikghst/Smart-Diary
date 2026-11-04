export interface ApiErrorBody {
  detail: string | { msg: string; loc: string[] }[];
}

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

export class NetworkError extends Error {
  constructor(message = "Сервер недоступен. Проверьте интернет.") {
    super(message);
    this.name = "NetworkError";
  }
}

export class UnexpectedResponseError extends Error {
  constructor(message = "Неожиданный ответ от сервера") {
    super(message);
    this.name = "UnexpectedResponseError";
  }
}

export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof NetworkError) return error.message;
  if (error instanceof UnexpectedResponseError) return error.message;
  if (error instanceof Error) return error.message;
  if (typeof error === "string") return error;
  return "Неизвестная ошибка";
}