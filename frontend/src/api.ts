export interface Worker {
  id: number
  client_id: string
  hostname: string
  ip_address: string
  os: string
  capabilities: string[]
  status: 'online' | 'busy' | 'offline'
  last_heartbeat: string | null
}

export interface Task {
  id: number
  type: 'robot_run' | 'run_command'
  status: 'pending' | 'assigned' | 'running' | 'completed' | 'failed' | 'cancelled'
  payload: Record<string, unknown>
  worker_id: number | null
  worker_client_id: string | null
  returncode: number | null
  error: string
  created_at: string
  started_at: string | null
  finished_at: string | null
  output?: string
}

export interface TestResult {
  id: number
  task_id: number | null
  suite_name: string
  total: number
  passed: number
  failed: number
  skipped: number
  elapsed_ms: number
  has_artifacts: boolean
  created_at: string
}

export interface Me {
  username: string
  auth_source: string
  roles: string[]
  permissions: string[]
}

export interface AdminUser {
  id: number
  username: string
  auth_source: string
  is_active: boolean
  roles: string[]
}

export interface Role {
  id: number
  name: string
  description: string
  permissions: string[]
}

export function getToken(): string | null {
  return localStorage.getItem('qahq_token')
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem('qahq_token', token)
  else localStorage.removeItem('qahq_token')
}

export class ApiError extends Error {
  status: number
  constructor(status: number, detail: string) {
    super(detail)
    this.status = status
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { ...(options.headers as Record<string, string>) }
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`
  if (options.body && typeof options.body === 'string') headers['Content-Type'] = 'application/json'

  const res = await fetch(path, { ...options, headers })
  if (res.status === 401) {
    setToken(null)
    window.location.href = '/login'
    throw new ApiError(401, 'Unauthorized')
  }
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch { /* keep statusText */ }
    throw new ApiError(res.status, detail)
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

export const api = {
  login: async (username: string, password: string) => {
    const body = new URLSearchParams({ username, password })
    const res = await fetch('/api/auth/token', { method: 'POST', body })
    if (!res.ok) throw new ApiError(res.status, 'Incorrect username or password')
    const data = await res.json()
    setToken(data.access_token)
  },
  me: () => request<Me>('/api/auth/me'),

  workers: () => request<Worker[]>('/api/workers'),
  registerWorker: (client_id: string) =>
    request<{ worker: Worker; token: string }>('/api/workers', {
      method: 'POST',
      body: JSON.stringify({ client_id }),
    }),
  regenerateToken: (id: number) =>
    request<{ token: string }>(`/api/workers/${id}/token`, { method: 'POST' }),
  deleteWorker: (id: number) => request<void>(`/api/workers/${id}`, { method: 'DELETE' }),

  tasks: (params: { status?: string; limit?: number } = {}) => {
    const q = new URLSearchParams()
    if (params.status) q.set('status', params.status)
    if (params.limit) q.set('limit', String(params.limit))
    return request<{ total: number; tasks: Task[] }>(`/api/tasks?${q}`)
  },
  task: (id: number) => request<Task>(`/api/tasks/${id}`),
  createTask: (body: Record<string, unknown>) =>
    request<Task>('/api/tasks', { method: 'POST', body: JSON.stringify(body) }),
  cancelTask: (id: number) => request<Task>(`/api/tasks/${id}/cancel`, { method: 'POST' }),

  results: () => request<{ total: number; results: TestResult[] }>('/api/results'),
  artifacts: (id: number) => request<{ artifacts: string[] }>(`/api/results/${id}/artifacts`),

  users: () => request<AdminUser[]>('/api/admin/users'),
  createUser: (body: { username: string; password: string; roles: string[] }) =>
    request<AdminUser>('/api/admin/users', { method: 'POST', body: JSON.stringify(body) }),
  updateUser: (id: number, body: Partial<{ password: string; is_active: boolean; roles: string[] }>) =>
    request<AdminUser>(`/api/admin/users/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  deleteUser: (id: number) => request<void>(`/api/admin/users/${id}`, { method: 'DELETE' }),

  roles: () => request<Role[]>('/api/admin/roles'),
  permissions: () => request<string[]>('/api/admin/permissions'),
  createRole: (body: { name: string; description: string; permissions: string[] }) =>
    request<Role>('/api/admin/roles', { method: 'POST', body: JSON.stringify(body) }),
  updateRole: (id: number, body: Partial<{ description: string; permissions: string[] }>) =>
    request<Role>(`/api/admin/roles/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  deleteRole: (id: number) => request<void>(`/api/admin/roles/${id}`, { method: 'DELETE' }),
}

export function artifactUrl(resultId: number, filename: string): string {
  return `/api/results/${resultId}/artifacts/${encodeURIComponent(filename)}`
}
