/**
 * SSE (Server-Sent Events) Hook - 用于任务实时事件推送
 * 
 * 替代 WebSocket，使用更简单的 SSE 协议获取服务端推送的任务状态更新。
 */
import { useEffect, useRef, useCallback, useState } from 'react'

export type TaskEventType = 
  | 'connected'
  | 'task_created'
  | 'task_started'
  | 'task_progress'
  | 'task_completed'
  | 'task_failed'

export interface TaskEvent {
  event_type: TaskEventType
  task_id: string
  task_name: string
  status: string
  progress: number
  message: string
  timestamp: string
  data?: Record<string, unknown>
}

export interface UseTaskEventsOptions {
  /** 是否自动连接 */
  autoConnect?: boolean
  /** 事件回调 */
  onEvent?: (event: TaskEvent) => void
  /** 连接成功回调 */
  onConnect?: () => void
  /** 连接断开回调 */
  onDisconnect?: () => void
  /** 错误回调 */
  onError?: (error: Event) => void
  /** 重连间隔 (ms) */
  reconnectInterval?: number
  /** 最大重连次数 */
  maxReconnectAttempts?: number
}

export interface UseTaskEventsReturn {
  /** 是否已连接 */
  isConnected: boolean
  /** 最近的事件列表 */
  events: TaskEvent[]
  /** 手动连接 */
  connect: () => void
  /** 断开连接 */
  disconnect: () => void
  /** 清空事件缓存 */
  clearEvents: () => void
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const API_BASE = (import.meta as any).env?.VITE_API_BASE || ''
const SSE_ENDPOINT = `${API_BASE}/api/tasks/events/stream`

export function useTaskEvents(options: UseTaskEventsOptions = {}): UseTaskEventsReturn {
  const {
    autoConnect = true,
    onEvent,
    onConnect,
    onDisconnect,
    onError,
    reconnectInterval = 3000,
    maxReconnectAttempts = 10,
  } = options

  const [isConnected, setIsConnected] = useState(false)
  const [events, setEvents] = useState<TaskEvent[]>([])

  const eventSourceRef = useRef<EventSource | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const reconnectTimerRef = useRef<number | null>(null)

  // 使用 ref 存储回调函数，避免它们的变化触发 useEffect 重新执行
  const callbacksRef = useRef({ onEvent, onConnect, onDisconnect, onError })
  callbacksRef.current = { onEvent, onConnect, onDisconnect, onError }

  const connect = useCallback(() => {
    // 避免重复连接
    if (eventSourceRef.current?.readyState === EventSource.OPEN) {
      return
    }

    // 关闭已有连接（如 CONNECTING 状态）
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }

    try {
      const es = new EventSource(SSE_ENDPOINT)
      eventSourceRef.current = es

      es.onopen = () => {
        console.log('[SSE] Connected to task events stream')
        setIsConnected(true)
        reconnectAttemptsRef.current = 0
        callbacksRef.current.onConnect?.()
      }

      // 监听 connected 事件
      es.addEventListener('connected', () => {
        console.log('[SSE] Server confirmed connection')
      })

      // 监听各种任务事件
      const taskEventTypes: TaskEventType[] = [
        'task_created',
        'task_started',
        'task_progress',
        'task_completed',
        'task_failed',
      ]

      taskEventTypes.forEach(eventType => {
        es.addEventListener(eventType, (e) => {
          try {
            const event: TaskEvent = JSON.parse(e.data)
            setEvents(prev => [...prev.slice(-99), event]) // 保留最近100条
            callbacksRef.current.onEvent?.(event)
          } catch (err) {
            console.error(`[SSE] Failed to parse ${eventType} event:`, err)
          }
        })
      })

      es.onerror = (error) => {
        console.error('[SSE] Connection error:', error)
        setIsConnected(false)
        callbacksRef.current.onError?.(error)
        callbacksRef.current.onDisconnect?.()

        // 关闭连接以触发重连
        es.close()
        eventSourceRef.current = null

        // 尝试重连
        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current++
          console.log(`[SSE] Reconnecting... (${reconnectAttemptsRef.current}/${maxReconnectAttempts})`)
          reconnectTimerRef.current = window.setTimeout(connect, reconnectInterval)
        } else {
          console.log('[SSE] Max reconnect attempts reached')
        }
      }
    } catch (err) {
      console.error('[SSE] Failed to create EventSource:', err)
    }
  }, [reconnectInterval, maxReconnectAttempts])

  const disconnect = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current)
      reconnectTimerRef.current = null
    }
    reconnectAttemptsRef.current = maxReconnectAttempts // 防止自动重连
    eventSourceRef.current?.close()
    eventSourceRef.current = null
    setIsConnected(false)
  }, [maxReconnectAttempts])

  const clearEvents = useCallback(() => {
    setEvents([])
  }, [])

  // 仅在 autoConnect 变化时触发连接，不依赖 connect/disconnect 函数引用
  useEffect(() => {
    if (autoConnect) {
      connect()
    }
    return () => {
      disconnect()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoConnect])

  return {
    isConnected,
    events,
    connect,
    disconnect,
    clearEvents,
  }
}

export default useTaskEvents

