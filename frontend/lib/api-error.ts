export type ApiValidationError = {
  path: string;
  message: string;
  type?: string;
};

type ApiErrorInit = {
  status: number;
  statusText?: string;
  code?: string;
  backendMessage?: string;
  backendDetail?: unknown;
  validationErrors?: ApiValidationError[];
  path?: string;
  operation?: string;
  responseBody?: unknown;
  rawBody?: string;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function stringValue(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value.trim() : undefined;
}

function formatValidationPath(value: unknown): string {
  if (Array.isArray(value)) {
    const parts = value
      .map((part) => String(part))
      .filter((part) => part && part !== "body");
    return parts.join(".") || "request";
  }

  return stringValue(value) ?? "request";
}

function normalizeValidationErrors(value: unknown): ApiValidationError[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.flatMap((item) => {
    if (!isRecord(item)) {
      return [];
    }

    const message = stringValue(item.msg) ?? stringValue(item.message);
    if (!message) {
      return [];
    }

    return [
      {
        path: formatValidationPath(item.loc ?? item.path),
        message,
        type: stringValue(item.type),
      },
    ];
  });
}

function buildApiErrorMessage(init: ApiErrorInit): string {
  const prefix = init.operation ? `${init.operation}: ` : "";
  const validationErrors = init.validationErrors ?? [];

  if (validationErrors.length > 0) {
    const summary = validationErrors
      .slice(0, 3)
      .map((error) => `${error.path}: ${error.message}`)
      .join("; ");
    const suffix = validationErrors.length > 3 ? "..." : "";
    return `${prefix}${init.backendMessage ?? "Validation failed"}: ${summary}${suffix}`;
  }

  if (init.backendMessage) {
    return `${prefix}${init.backendMessage}`;
  }

  if (typeof init.backendDetail === "string" && init.backendDetail.trim()) {
    return `${prefix}${init.backendDetail.trim()}`;
  }

  if (init.status === 401) {
    return `${prefix}Authentication is required.`;
  }

  if (init.status === 403) {
    return `${prefix}You do not have access to this resource.`;
  }

  if (init.status === 404) {
    return `${prefix}The requested resource was not found.`;
  }

  if (init.status >= 500) {
    return `${prefix}The server could not complete the request.`;
  }

  return `${prefix}Request failed: ${init.status}`;
}

export class ApiError extends Error {
  readonly status: number;
  readonly statusText?: string;
  readonly code?: string;
  readonly backendMessage?: string;
  readonly backendDetail?: unknown;
  readonly validationErrors: ApiValidationError[];
  readonly path?: string;
  readonly operation?: string;
  readonly responseBody?: unknown;
  readonly rawBody?: string;

  constructor(init: ApiErrorInit) {
    super(buildApiErrorMessage(init));
    this.name = "ApiError";
    this.status = init.status;
    this.statusText = init.statusText;
    this.code = init.code;
    this.backendMessage = init.backendMessage;
    this.backendDetail = init.backendDetail;
    this.validationErrors = init.validationErrors ?? [];
    this.path = init.path;
    this.operation = init.operation;
    this.responseBody = init.responseBody;
    this.rawBody = init.rawBody;
  }
}

async function readErrorBody(response: Response): Promise<{
  responseBody?: unknown;
  rawBody?: string;
}> {
  const rawBody = await response.text();
  if (!rawBody.trim()) {
    return {};
  }

  const contentType = response.headers.get("content-type") ?? "";
  const maybeJson =
    contentType.includes("application/json") ||
    rawBody.trimStart().startsWith("{") ||
    rawBody.trimStart().startsWith("[");

  if (!maybeJson) {
    return { rawBody };
  }

  try {
    return { responseBody: JSON.parse(rawBody), rawBody };
  } catch {
    return { rawBody };
  }
}

export async function createApiError(
  response: Response,
  options: { path?: string; operation?: string } = {}
): Promise<ApiError> {
  const { responseBody, rawBody } = await readErrorBody(response);
  let code: string | undefined;
  let backendMessage: string | undefined;
  let backendDetail: unknown;
  let validationErrors: ApiValidationError[] = [];

  if (isRecord(responseBody)) {
    const backendError = isRecord(responseBody.error) ? responseBody.error : undefined;
    code = stringValue(backendError?.code) ?? stringValue(responseBody.code);
    backendMessage =
      stringValue(backendError?.message) ??
      stringValue(responseBody.message) ??
      stringValue(responseBody.detail);
    backendDetail = backendError?.details ?? responseBody.detail;
    validationErrors = [
      ...normalizeValidationErrors(responseBody.detail),
      ...normalizeValidationErrors(backendError?.details),
    ];
  }

  return new ApiError({
    status: response.status,
    statusText: response.statusText,
    code,
    backendMessage,
    backendDetail,
    validationErrors,
    path: options.path,
    operation: options.operation,
    responseBody,
    rawBody,
  });
}

export function getApiErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    return error.message;
  }

  if (error instanceof Error && error.message) {
    return error.message;
  }

  return fallback;
}
