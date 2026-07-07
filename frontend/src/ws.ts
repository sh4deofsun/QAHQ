import { useEffect } from 'react'
import { getToken } from './api'

export type UIEvent =
  | { event: 'worker_status'; worker: { id: number; client_id: string; status: string; capabilities: string[] } }
  | { event: 'task_update'; task: Record<string, unknown> & { id: number; status: string } }
  | { event: 'task_output'; task_id: number; data: string }
  | { event: 'result_created'; task_id: number }

type Handler = (event: UIEvent) => void

const handlers = new Set<Handler>()
let socket: WebSocket | null = null
let retry = 1000

function connect() {
  const token = getToken()
  if (!token) return
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
  socket = new WebSocket(`${proto}://${window.location.host}/ws/ui?token=${token}`)
  socket.onmessage = (msg) => {
    const event = JSON.parse(msg.data) as UIEvent
    handlers.forEach((h) => h(event))
  }
  socket.onclose = () => {
    socket = null
    if (getToken()) {
      setTimeout(connect, retry)
      retry = Math.min(retry * 2, 15000)
    }
  }
  socket.onopen = () => {
    retry = 1000
  }
}

export function disconnect() {
  socket?.close()
  socket = null
}

/** Subscribe to live UI events. Opens the shared socket on first use. */
export function useUIEvents(handler: Handler) {
  useEffect(() => {
    if (!socket) connect()
    handlers.add(handler)
    return () => {
      handlers.delete(handler)
    }
  }, [handler])
}
