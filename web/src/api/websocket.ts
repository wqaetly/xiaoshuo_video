/**
 * WebSocket 连接管理 - 用于实时进度推送
 */

export type WSMessageType = 'connected' | 'progress' | 'log' | 'task_update' | 'heartbeat' | 'pong'

export interface WSMessage {
  type: WSMessageType
  timestamp?: string
  // progress 消息字段
  phase?: string
  task?: string
  progress?: number
  message?: string
  // log 消息字段
  level?: string
  module?: string
  // task_update 消息字段
  task_id?: string
  status?: string
  // connected 消息字段
  project?: string
}

export interface WSOptions {
  onMessage?: (message: WSMessage) => void
  onConnect?: () => void
  onDisconnect?: () => void
  onError?: (error: Event) => void
  reconnectInterval?: number
  maxReconnectAttempts?: number
}

/**
 * 创建 WebSocket 连接
 */
export function createWebSocket(
  endpoint: string,
  options: WSOptions = {}
): {
  connect: () => void
  disconnect: () => void
  send: (data: string) => void
  isConnected: () => boolean
} {
  const {
    onMessage,
    onConnect,
    onDisconnect,
    onError,
    reconnectInterval = 3000,
    maxReconnectAttempts = 5,
  } = options

  let ws: WebSocket | null = null
  let reconnectAttempts = 0
  let reconnectTimer: number | null = null
  let pingTimer: number | null = null

  // 获取 WebSocket URL
  const getWsUrl = () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    return `${protocol}//${host}/api/ws${endpoint}`
  }

  const connect = () => {
    if (ws?.readyState === WebSocket.OPEN) return

    try {
      ws = new WebSocket(getWsUrl())

      ws.onopen = () => {
        console.log(`[WS] Connected to ${endpoint}`)
        reconnectAttempts = 0
        onConnect?.()
        // 启动心跳
        startPing()
      }

      ws.onmessage = (event) => {
        try {
          const message: WSMessage = JSON.parse(event.data)
          if (message.type === 'heartbeat') {
            // 响应心跳
            ws?.send('ping')
          } else {
            onMessage?.(message)
          }
        } catch (e) {
          console.error('[WS] Failed to parse message:', e)
        }
      }

      ws.onclose = () => {
        console.log(`[WS] Disconnected from ${endpoint}`)
        stopPing()
        onDisconnect?.()
        // 尝试重连
        attemptReconnect()
      }

      ws.onerror = (error) => {
        console.error('[WS] Error:', error)
        onError?.(error)
      }
    } catch (e) {
      console.error('[WS] Failed to connect:', e)
      attemptReconnect()
    }
  }

  const disconnect = () => {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    stopPing()
    reconnectAttempts = maxReconnectAttempts // 防止自动重连
    ws?.close()
    ws = null
  }

  const send = (data: string) => {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(data)
    }
  }

  const isConnected = () => ws?.readyState === WebSocket.OPEN

  const attemptReconnect = () => {
    if (reconnectAttempts >= maxReconnectAttempts) {
      console.log('[WS] Max reconnect attempts reached')
      return
    }
    reconnectAttempts++
    console.log(`[WS] Reconnecting... (${reconnectAttempts}/${maxReconnectAttempts})`)
    reconnectTimer = window.setTimeout(connect, reconnectInterval)
  }

  const startPing = () => {
    pingTimer = window.setInterval(() => {
      if (ws?.readyState === WebSocket.OPEN) {
        ws.send('ping')
      }
    }, 25000)
  }

  const stopPing = () => {
    if (pingTimer) {
      clearInterval(pingTimer)
      pingTimer = null
    }
  }

  return { connect, disconnect, send, isConnected }
}

