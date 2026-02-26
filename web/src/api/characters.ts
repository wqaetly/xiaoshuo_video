import apiClient from './client'
import type { Character } from '../types'

export interface CharacterListResponse {
  characters: Character[]
  total: number
}

export interface VoiceInfo {
  id: string
  name: string
  gender: string
  provider?: string
  sample_url?: string
}

// 后端返回的音色列表响应
interface VoiceListResponse {
  voices: VoiceInfo[]
}

export const characterApi = {
  // 获取角色列表
  list: (projectName: string): Promise<CharacterListResponse> => {
    return apiClient.get(`/characters/${projectName}`)
  },

  // 获取角色详情
  get: (projectName: string, characterId: string): Promise<Character> => {
    return apiClient.get(`/characters/${projectName}/${characterId}`)
  },

  // 创建角色
  create: (projectName: string, data: Partial<Character>): Promise<Character> => {
    return apiClient.post(`/characters/${projectName}`, data)
  },

  // 更新角色
  update: (projectName: string, characterId: string, data: Partial<Character>): Promise<Character> => {
    return apiClient.put(`/characters/${projectName}/${characterId}`, data)
  },

  // 删除角色
  delete: (projectName: string, characterId: string): Promise<void> => {
    return apiClient.delete(`/characters/${projectName}/${characterId}`)
  },

  // 获取可用音色列表
  getVoices: async (): Promise<VoiceInfo[]> => {
    const response: VoiceListResponse = await apiClient.get('/characters/voices')
    return response.voices
  },

  // 试听音色（需要 projectName 参数）
  previewVoice: (projectName: string, voiceId: string, text: string): Promise<{ audio_data: string | null; message: string }> => {
    return apiClient.post(`/characters/${projectName}/voice/preview`, { voice_id: voiceId, text })
  },

  // 重新生成角色立绘
  regeneratePortrait: (projectName: string, characterId: string): Promise<{ task_id: string }> => {
    return apiClient.post(`/characters/${projectName}/${characterId}/regenerate`)
  },
}

