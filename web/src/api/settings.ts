import apiClient from './client'
import type { AppSettings, LocalServicesConfig, APIServicesConfig, VideoOutputConfig } from '../types'

export interface SettingsResponse {
  settings: AppSettings
  message: string
}

export const settingsApi = {
  // 获取所有设置
  getAll: (): Promise<SettingsResponse> => {
    return apiClient.get('/settings')
  },

  // 更新设置
  update: (settings: Partial<{
    local: Partial<LocalServicesConfig>
    api: Partial<APIServicesConfig>
    video: Partial<VideoOutputConfig>
  }>): Promise<SettingsResponse> => {
    return apiClient.put('/settings', settings)
  },

  // 获取本地服务配置
  getLocal: (): Promise<LocalServicesConfig> => {
    return apiClient.get('/settings/local')
  },

  // 更新本地服务配置
  updateLocal: (config: LocalServicesConfig): Promise<LocalServicesConfig> => {
    return apiClient.put('/settings/local', config)
  },

  // 获取API服务配置
  getApi: (): Promise<APIServicesConfig> => {
    return apiClient.get('/settings/api')
  },

  // 更新API服务配置
  updateApi: (config: APIServicesConfig): Promise<APIServicesConfig> => {
    return apiClient.put('/settings/api', config)
  },

  // 获取视频输出配置
  getVideo: (): Promise<VideoOutputConfig> => {
    return apiClient.get('/settings/video')
  },

  // 更新视频输出配置
  updateVideo: (config: VideoOutputConfig): Promise<VideoOutputConfig> => {
    return apiClient.put('/settings/video', config)
  },

  // 重新加载配置
  reload: (): Promise<void> => {
    return apiClient.post('/settings/reload')
  },
}

