import apiClient from './client'

export interface ServiceStatus {
  ollama: { available: boolean; model: string }
  comfyui: { available: boolean; queue_size: number }
  cosyvoice: { available: boolean }
}

export interface CompletedTasks {
  character: number
  image: number
  audio: number
  video: number
}

export interface FailedScene {
  scene_id: string
  phase: string
  message: string
  time: string
}

export interface GenerationProgress {
  phase: string
  phase_index: number
  total_phases: number
  task: string
  progress: number
  message: string
  is_running: boolean
  current_scene_index: number
  total_scenes: number
  completed_tasks: CompletedTasks
  failed_scenes: FailedScene[]
  error_count: number
}

export const generationApi = {
  // 检查服务状态
  checkServices: (): Promise<ServiceStatus> => {
    return apiClient.get('/generation/status')
  },

  // 获取生成进度
  getProgress: (projectName: string): Promise<GenerationProgress> => {
    return apiClient.get(`/generation/${projectName}/progress`)
  },

  // 开始生成
  start: (projectName: string, options?: {
    start_phase?: string
    resume?: boolean
  }): Promise<{ task_id: string }> => {
    return apiClient.post(`/generation/${projectName}/start`, options)
  },

  // 停止生成
  stop: (projectName: string): Promise<void> => {
    return apiClient.post(`/generation/${projectName}/stop`)
  },
}

