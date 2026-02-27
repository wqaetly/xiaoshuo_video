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

// 生成阶段定义
export interface PhaseInfo {
  id: string
  name: string
  description: string
  icon?: string
}

export const GENERATION_PHASES: PhaseInfo[] = [
  { id: 'init', name: '初始化', description: '准备环境' },
  { id: 'analyze', name: '分析', description: '分析小说生成分镜' },
  { id: 'character_design', name: '角色设计', description: '生成角色立绘' },
  { id: 'generate_images', name: '图像生成', description: '生成场景图像' },
  { id: 'generate_audio', name: '音频生成', description: '生成配音' },
  { id: 'generate_video', name: '视频生成', description: '生成场景视频' },
  { id: 'compose', name: '合成', description: '合成最终视频' },
]

export interface ProjectStats {
  total_scenes: number
  completed_scenes: number
  total_characters: number
  total_duration: number
}

// 场景相关类型 - 匹配后端 api/models/scene.py 的嵌套结构
export interface CameraInfo {
  type: string
  start_frame: string
  end_frame: string
}

export interface VisualInfo {
  description: string
  sd_prompt?: string
  style_tags?: string[]
  characters_in_scene?: string[]
  camera?: CameraInfo
}

export interface NarrationInfo {
  text: string
  emotion?: string
}

export interface DialogueInfo {
  character_id: string
  text: string
  emotion?: string
}

export interface AudioInfo {
  narration?: NarrationInfo
  dialogues?: DialogueInfo[]
  bgm?: string
  sfx?: string[]
}

export interface SubtitleInfo {
  text: string
  style?: string
  character?: string | null
}

export interface GenerationStatus {
  image: 'pending' | 'generating' | 'completed' | 'error'
  audio: 'pending' | 'generating' | 'completed' | 'error'
  video: 'pending' | 'generating' | 'completed' | 'error'
}

export interface Scene {
  id: string
  chapter: number
  sequence: number
  global_index: number
  duration: number
  visual: VisualInfo
  audio: AudioInfo
  subtitle: SubtitleInfo
  generation_status: GenerationStatus
  // 资源路径（由服务层添加）
  image_path?: string
  audio_path?: string
  video_path?: string
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

