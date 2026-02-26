import apiClient from './client'
import type { Project, ProjectListResponse, ProjectStatus, ProjectStats } from '../types'

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

  // 创建项目
  create: (name: string, description?: string): Promise<Project> => {
    return apiClient.post('/projects', { name, description })
  },

  // 删除项目
  delete: (projectName: string): Promise<void> => {
    return apiClient.delete(`/projects/${projectName}`)
  },
}

