import apiClient from './client'
import type { Scene } from '../types'

export interface SceneListResponse {
  scenes: Scene[]
  total: number
}

export const sceneApi = {
  // 获取场景列表
  list: (projectName: string): Promise<SceneListResponse> => {
    return apiClient.get(`/scenes/${projectName}`)
  },

  // 获取场景详情
  get: (projectName: string, sceneId: string): Promise<Scene> => {
    return apiClient.get(`/scenes/${projectName}/${sceneId}`)
  },

  // 创建场景
  create: (projectName: string, data: Partial<Scene>): Promise<Scene> => {
    return apiClient.post(`/scenes/${projectName}`, data)
  },

  // 更新场景
  update: (projectName: string, sceneId: string, data: Partial<Scene>): Promise<Scene> => {
    return apiClient.put(`/scenes/${projectName}/${sceneId}`, data)
  },

  // 删除场景
  delete: (projectName: string, sceneId: string): Promise<void> => {
    return apiClient.delete(`/scenes/${projectName}/${sceneId}`)
  },

  // 重新排序场景
  reorder: (projectName: string, sceneIds: string[]): Promise<void> => {
    return apiClient.post(`/scenes/${projectName}/reorder`, { scene_ids: sceneIds })
  },

  // 分析小说生成分镜
  analyze: (projectName: string): Promise<{ task_id: string }> => {
    return apiClient.post(`/scenes/${projectName}/analyze`)
  },
}

