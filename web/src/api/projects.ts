import apiClient from './client'
import type { Project, ProjectListResponse, ProjectStatus, ProjectStats } from '../types'

export interface QuickCreateResponse {
  name: string
  created_at?: string
  style: string
  novel_file?: string
  generation_started: boolean
  generation_message: string
}

export const projectApi = {
  // 获取项目列表
  list: (): Promise<ProjectListResponse> => {
    return apiClient.get('/projects')
  },

  // 获取项目详情
  get: (projectName: string): Promise<Project> => {
    return apiClient.get(`/projects/${projectName}`)
  },

  // 获取项目状态
  getStatus: (projectName: string): Promise<ProjectStatus> => {
    return apiClient.get(`/projects/${projectName}/status`)
  },

  // 获取项目统计
  getStats: (projectName: string): Promise<ProjectStats> => {
    return apiClient.get(`/projects/${projectName}/stats`)
  },

  // 创建项目（带文件上传）
  create: (name: string, novelFile: File, style: string = 'anime'): Promise<Project> => {
    const formData = new FormData()
    formData.append('name', name)
    formData.append('style', style)
    formData.append('novel_file', novelFile)
    return apiClient.postFormData('/projects', formData)
  },

  // 快速创建并启动生成
  quickCreate: (name: string, novelFile: File, style: string = 'anime'): Promise<QuickCreateResponse> => {
    const formData = new FormData()
    formData.append('name', name)
    formData.append('style', style)
    formData.append('novel_file', novelFile)
    return apiClient.postFormData('/projects/quick-create', formData)
  },

  // 删除项目
  delete: (projectName: string): Promise<void> => {
    return apiClient.delete(`/projects/${projectName}`)
  },

  // 更换小说文件
  updateNovel: (projectName: string, novelFile: File): Promise<{
    success: boolean
    message: string
    name: string
    novel_file: string
    updated_at: string
    reset_storyboard: boolean
  }> => {
    const formData = new FormData()
    formData.append('novel_file', novelFile)
    return apiClient.putFormData(`/projects/${projectName}/novel`, formData)
  },

  // 获取小说内容
  getNovelContent: (projectName: string): Promise<{ content: string }> => {
    return apiClient.get(`/projects/${projectName}/novel`)
  },
}

