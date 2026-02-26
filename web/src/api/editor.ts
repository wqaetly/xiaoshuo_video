import apiClient from './client'
import type { Timeline, MediaInfo } from '../types'

export interface MaterialListResponse {
  videos: MediaInfo[]
  audios: MediaInfo[]
  images: string[]
}

export interface TransitionType {
  id: string
  name: string
}

export const editorApi = {
  // 获取素材列表
  listMaterials: (projectName: string): Promise<MaterialListResponse> => {
    return apiClient.get(`/editor/${projectName}/materials`)
  },

  // 获取时间轴
  getTimeline: (projectName: string): Promise<Timeline> => {
    return apiClient.get(`/editor/${projectName}/timeline`)
  },

  // 保存时间轴
  saveTimeline: (projectName: string, timeline: Timeline): Promise<Timeline> => {
    return apiClient.put(`/editor/${projectName}/timeline`, timeline)
  },

  // 获取转场效果列表
  getTransitions: (): Promise<TransitionType[]> => {
    return apiClient.get('/editor/transitions')
  },

  // 获取媒体信息
  getMediaInfo: (path: string): Promise<MediaInfo> => {
    return apiClient.get('/editor/media/info', { params: { path } })
  },

  // 裁剪视频
  trim: (projectName: string, data: {
    source: string
    start_time: number
    end_time: number
    output_name?: string
  }): Promise<MediaInfo> => {
    return apiClient.post(`/editor/${projectName}/trim`, data)
  },

  // 拼接视频
  concat: (projectName: string, data: {
    clips: { source: string; start_time?: number; end_time?: number }[]
    output_name?: string
  }): Promise<MediaInfo> => {
    return apiClient.post(`/editor/${projectName}/concat`, data)
  },

  // 调整速度
  adjustSpeed: (projectName: string, data: {
    source: string
    speed: number
    output_name?: string
  }): Promise<MediaInfo> => {
    return apiClient.post(`/editor/${projectName}/speed`, data)
  },

  // 调整音量
  adjustVolume: (projectName: string, data: {
    source: string
    volume: number
    output_name?: string
  }): Promise<MediaInfo> => {
    return apiClient.post(`/editor/${projectName}/volume`, data)
  },

  // 导出视频
  export: (projectName: string, options?: {
    format?: string
    quality?: string
  }): Promise<{ task_id: string }> => {
    return apiClient.post(`/editor/${projectName}/export`, options)
  },

  // 获取导出进度
  getExportProgress: (projectName: string, taskId: string): Promise<{
    task_id: string
    progress: number
    status: string
    message?: string
    output_path?: string
  }> => {
    return apiClient.get(`/editor/${projectName}/export/${taskId}`)
  },
}

