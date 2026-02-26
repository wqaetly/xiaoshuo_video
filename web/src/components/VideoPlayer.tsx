import { useRef, useEffect, forwardRef, useImperativeHandle } from 'react'
import videojs from 'video.js'
import type Player from 'video.js/dist/types/player'
import 'video.js/dist/video-js.css'

export interface VideoPlayerRef {
  player: () => Player | null
  play: () => void
  pause: () => void
  seek: (time: number) => void
  getCurrentTime: () => number
  getDuration: () => number
  setPlaybackRate: (rate: number) => void
}

export interface VideoPlayerProps {
  src: string
  poster?: string
  autoplay?: boolean
  onTimeUpdate?: (time: number) => void
  onDurationChange?: (duration: number) => void
  onPlay?: () => void
  onPause?: () => void
  onEnded?: () => void
  onReady?: (player: Player) => void
  style?: React.CSSProperties
}

const VideoPlayer = forwardRef<VideoPlayerRef, VideoPlayerProps>(
  ({ src, poster, autoplay = false, onTimeUpdate, onDurationChange, onPlay, onPause, onEnded, onReady, style }, ref) => {
    const videoRef = useRef<HTMLDivElement>(null)
    const playerRef = useRef<Player | null>(null)

    useImperativeHandle(ref, () => ({
      player: () => playerRef.current,
      play: () => playerRef.current?.play(),
      pause: () => playerRef.current?.pause(),
      seek: (time: number) => playerRef.current?.currentTime(time),
      getCurrentTime: () => playerRef.current?.currentTime() || 0,
      getDuration: () => playerRef.current?.duration() || 0,
      setPlaybackRate: (rate: number) => playerRef.current?.playbackRate(rate),
    }))

    useEffect(() => {
      if (!videoRef.current) return

      // 创建 video 元素
      const videoElement = document.createElement('video-js')
      videoElement.classList.add('vjs-big-play-centered')
      videoRef.current.appendChild(videoElement)

      // 初始化播放器
      const player = videojs(videoElement, {
        controls: true,
        fluid: true,
        autoplay,
        preload: 'auto',
        playbackRates: [0.5, 1, 1.5, 2],
        sources: src ? [{ src, type: 'video/mp4' }] : [],
        poster,
      })

      playerRef.current = player

      // 事件绑定
      player.ready(() => {
        onReady?.(player)
      })

      player.on('timeupdate', () => {
        onTimeUpdate?.(player.currentTime() || 0)
      })

      player.on('durationchange', () => {
        onDurationChange?.(player.duration() || 0)
      })

      player.on('play', () => onPlay?.())
      player.on('pause', () => onPause?.())
      player.on('ended', () => onEnded?.())

      return () => {
        if (playerRef.current && !playerRef.current.isDisposed()) {
          playerRef.current.dispose()
          playerRef.current = null
        }
      }
    }, [])

    // 更新视频源
    useEffect(() => {
      if (playerRef.current && src) {
        playerRef.current.src({ src, type: 'video/mp4' })
        if (poster) {
          playerRef.current.poster(poster)
        }
      }
    }, [src, poster])

    return (
      <div data-vjs-player style={style}>
        <div ref={videoRef} />
      </div>
    )
  }
)

VideoPlayer.displayName = 'VideoPlayer'

export default VideoPlayer

