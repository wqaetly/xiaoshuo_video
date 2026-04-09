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

// 子任务状态
export interface SubTaskStatus {
  id: string
  name: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped'
  progress: number
  message: string
  started_at?: string
  completed_at?: string
  error?: string
}

// 阶段详细进度
export interface PhaseProgress {
  phase_id: string
  phase_name: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: number
  total_items: number
  completed_items: number
  failed_items: number
  current_item: string
  sub_tasks: SubTaskStatus[]
}

export interface GenerationProgress {
  phase: string
  phase_index: number
  total_phases: number
  task: string
  progress: number  // 整体进度 0.0 - 1.0
  message: string
  is_running: boolean
  // 当前阶段详细进度
  phase_progress: number  // 当前阶段进度 0.0 - 1.0
  current_item: string    // 当前处理项（如角色名、场景ID）
  current_item_index: number  // 当前处理第几个
  current_item_total: number  // 当前阶段总数
  // 场景进度
  current_scene_index: number
  total_scenes: number
  completed_tasks: CompletedTasks
  failed_scenes: FailedScene[]
  error_count: number
  // 各阶段详细进度（新增）
  phases_detail: PhaseProgress[]
}

export const generationApi = {
  // 检查服务状态
  checkServices: (): Promise<ServiceStatus> => {
    return apiClient.get('/generation/services')
  },

  // 获取生成进度
  getProgress: (projectName: string): Promise<GenerationProgress> => {
    return apiClient.get(`/generation/progress/${projectName}`)
  },

  // 开始生成
  start: (projectName: string, options?: {
    phase?: string
    resume?: boolean
  }): Promise<{ task_id: string }> => {
    return apiClient.post('/generation/start', {
      project_name: projectName,
      phase: options?.phase || 'full',
      resume: options?.resume ?? true,
    })
  },

  // 停止生成
  stop: (projectName: string): Promise<void> => {
    return apiClient.post('/generation/stop', {
      project_name: projectName,
    })
  },

  // 获取微任务列表
  getMicroTasks: (projectName: string, activeOnly: boolean = false): Promise<{
    tasks: MicroTaskInfo[]
    count: number
  }> => {
    return apiClient.get(`/generation/micro-tasks/${projectName}`, {
      params: { active_only: activeOnly }
    })
  },
}

// 微任务信息类型
export interface MicroTaskInfo {
  task_id: string
  project_name: string
  task_type: string
  target_ids: string[]
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: number
  message: string
  created_at: string
  started_at?: string
  completed_at?: string
  error?: string
}

