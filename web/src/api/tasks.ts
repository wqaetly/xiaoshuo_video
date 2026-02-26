import apiClient from './client'
import type { Task } from '../types'

export interface TaskListResponse {
  tasks: Task[]
  total: number
}

export interface LogEntry {
  timestamp: string
  level: string
  message: string
}

export const taskApi = {
  // 获取任务列表
  list: (status?: string): Promise<TaskListResponse> => {
    return apiClient.get('/tasks', { params: { status } })
  },

  // 获取任务详情
  get: (taskId: string): Promise<Task> => {
    return apiClient.get(`/tasks/${taskId}`)
  },

  // 取消任务
  cancel: (taskId: string): Promise<void> => {
    return apiClient.post(`/tasks/${taskId}/cancel`)
  },

  // 取消所有任务
  cancelAll: (): Promise<void> => {
    return apiClient.post('/tasks/cancel-all')
  },

  // 清理已完成任务
  clearCompleted: (): Promise<void> => {
    return apiClient.post('/tasks/clear-completed')
  },

  // 获取日志
  getLogs: (limit?: number): Promise<LogEntry[]> => {
    return apiClient.get('/tasks/logs', { params: { limit } })
  },

  // 清除日志
  clearLogs: (): Promise<void> => {
    return apiClient.post('/tasks/logs/clear')
  },
}

