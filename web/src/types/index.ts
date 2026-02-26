// 项目相关类型
export interface Project {
  name: string
  description?: string
  created_at?: string
  scene_count?: number
  character_count?: number
  progress?: number
  phase?: string
}

export interface ProjectListResponse {
  projects: Project[]
  total: number
}

export interface ProjectStatus {
  phase: string
  progress: number
  is_running: boolean
  current_task?: string
}

export interface ProjectStats {
  total_scenes: number
  completed_scenes: number
  total_characters: number
  total_duration: number
}

// 场景相关类型
export interface Scene {
  id: string
  scene_number: number
  title?: string
  description?: string
  narration?: string
  dialogue?: string
  image_url?: string
  video_url?: string
  audio_url?: string
  duration?: number
  status?: 'pending' | 'generating' | 'completed' | 'error'
}

// 角色相关类型 - 匹配后端 api/models/character.py 的结构
export interface AppearanceInfo {
  gender?: string
  hair?: string
  eyes?: string
  clothing?: string
  features?: string
}

export interface VoiceConfig {
  provider?: string
  voice_id?: string
  speed?: number
  pitch?: number
}

export interface Character {
  id: string
  name: string
  aliases?: string[]
  appearance?: AppearanceInfo
  sd_prompt?: string
  sd_negative?: string
  voice?: VoiceConfig
  images?: string[]
}

// 任务相关类型
export interface Task {
  id: string
  type: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  progress: number
  message?: string
  created_at: string
  updated_at?: string
}

// 设置相关类型
export interface LocalServicesConfig {
  ollama_url: string
  ollama_model: string
  comfyui_url: string
  cosyvoice_url: string
}

export interface APIServicesConfig {
  video_provider: string
  video_api_key: string
  use_idle_time: boolean
}

export interface VideoOutputConfig {
  resolution: string
  fps: number
}

export interface AppSettings {
  local: LocalServicesConfig
  api: APIServicesConfig
  video: VideoOutputConfig
}

// 编辑器相关类型
export interface VideoClip {
  id: string
  source: string
  start_time: number
  end_time: number
  timeline_start: number
  duration: number
  volume?: number
  speed?: number
}

export interface AudioClip {
  id: string
  source: string
  start_time: number
  end_time: number
  timeline_start: number
  duration: number
  volume?: number
}

export interface SubtitleClip {
  id: string
  text: string
  start_time: number
  end_time: number
  style?: Record<string, string>
}

export interface Timeline {
  video_clips: VideoClip[]
  audio_clips: AudioClip[]
  subtitle_clips: SubtitleClip[]
  total_duration: number
}

// 媒体信息
export interface MediaInfo {
  path: string
  duration?: number
  width?: number
  height?: number
  codec?: string
  size?: number
}

// 时间轴轨道类型
export interface TimelineClip {
  id: string
  name?: string
  source?: string
  start: number  // 在时间轴上的开始时间
  end: number    // 在时间轴上的结束时间
  sourceStart?: number  // 源素材的开始时间
  sourceEnd?: number    // 源素材的结束时间
  volume?: number
  speed?: number
}

export interface TimelineTrack {
  id: string
  name: string
  type: 'video' | 'audio' | 'subtitle'
  clips: TimelineClip[]
  muted?: boolean
  locked?: boolean
}

