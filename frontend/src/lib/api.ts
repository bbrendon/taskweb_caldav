import type { AppConfig, Task, TaskPatch } from './types'

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
  }
}

let onUnauthorized: () => void = () => {}
export function setUnauthorizedHandler(fn: () => void) {
  onUnauthorized = fn
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  let res: Response
  try {
    res = await fetch(path, {
      method,
      credentials: 'same-origin',
      headers: {
        'X-Requested-With': 'taskweb',
        ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new ApiError(0, 'No connection. Check your network and try again.')
  }
  if (res.status === 401 && path !== '/api/login') onUnauthorized()
  if (!res.ok) {
    let detail = `Request failed (${res.status})`
    try {
      const data = await res.json()
      if (typeof data.detail === 'string') detail = data.detail
      else if (Array.isArray(data.detail)) detail = data.detail.map((d: { msg: string }) => d.msg).join('; ')
    } catch { /* not JSON */ }
    throw new ApiError(res.status, detail)
  }
  return res.json() as Promise<T>
}

export const api = {
  session: () => request<{ authenticated: boolean }>('GET', '/api/session'),
  login: (password: string) => request<{ ok: boolean }>('POST', '/api/login', { password }),
  logout: () => request<{ ok: boolean }>('POST', '/api/logout'),
  config: () => request<AppConfig>('GET', '/api/config'),
  tasks: (since?: number) =>
    request<{ version: number; tasks?: Task[]; unchanged?: boolean }>(
      'GET', since === undefined ? '/api/tasks' : `/api/tasks?since=${since}`),
  create: (patch: TaskPatch) => request<Task>('POST', '/api/tasks', patch),
  update: (uid: string, patch: TaskPatch) => request<Task>('PATCH', `/api/tasks/${encodeURIComponent(uid)}`, patch),
  remove: (uid: string, children: 'orphan' | 'delete') =>
    request<{ deleted: string[] }>('DELETE', `/api/tasks/${encodeURIComponent(uid)}?children=${children}`),
  complete: (uid: string) => request<Task>('POST', `/api/tasks/${encodeURIComponent(uid)}/complete`),
  reopen: (uid: string) => request<Task>('POST', `/api/tasks/${encodeURIComponent(uid)}/reopen`),
  skip: (uid: string) => request<Task>('POST', `/api/tasks/${encodeURIComponent(uid)}/skip`),
  settings: () => request<Record<string, unknown>>('GET', '/api/settings'),
  saveSettings: (doc: Record<string, unknown>) => request<Record<string, unknown>>('PUT', '/api/settings', doc),
}
