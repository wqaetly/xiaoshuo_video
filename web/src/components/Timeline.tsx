import { useRef, useMemo } from 'react'
import { Typography } from 'antd'
import type { TimelineTrack } from '../types'

const { Text } = Typography

export interface TimelineProps {
  tracks: TimelineTrack[]
  duration: number
  currentTime: number
  zoom: number
  onSeek: (time: number) => void
  onClipSelect?: (trackIndex: number, clipIndex: number) => void
  onClipMove?: (trackIndex: number, clipIndex: number, newStart: number) => void
  selectedClip?: { trackIndex: number; clipIndex: number } | null
}

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  const ms = Math.floor((seconds % 1) * 100)
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(2, '0')}`
}

function Timeline({
  tracks,
  duration,
  currentTime,
  zoom,
  onSeek,
  onClipSelect,
  selectedClip,
}: TimelineProps) {
  const containerRef = useRef<HTMLDivElement>(null)

  // 每秒对应的像素宽度
  const pixelsPerSecond = zoom * 50

  // 时间轴总宽度
  const timelineWidth = Math.max(duration * pixelsPerSecond, 800)

  // 时间刻度
  const timeMarkers = useMemo(() => {
    const markers: number[] = []
    const interval = zoom >= 1 ? 1 : zoom >= 0.5 ? 5 : 10
    for (let t = 0; t <= duration; t += interval) {
      markers.push(t)
    }
    return markers
  }, [duration, zoom])

  // 播放头位置
  const playheadPosition = currentTime * pixelsPerSecond

  const handleTimelineClick = (e: React.MouseEvent) => {
    if (!containerRef.current) return
    const rect = containerRef.current.getBoundingClientRect()
    const scrollLeft = containerRef.current.scrollLeft
    const x = e.clientX - rect.left + scrollLeft
    const time = Math.max(0, Math.min(duration, x / pixelsPerSecond))
    onSeek(time)
  }

  // 轨道颜色
  const trackColors: Record<string, string> = {
    video: '#1890ff',
    audio: '#52c41a',
    subtitle: '#faad14',
  }

  return (
    <div style={{ background: '#1e1e1e', borderRadius: 8, padding: 16 }}>
      {/* 时间显示 */}
      <div style={{ marginBottom: 8, display: 'flex', justifyContent: 'space-between' }}>
        <Text style={{ color: '#fff', fontFamily: 'monospace' }}>{formatTime(currentTime)}</Text>
        <Text style={{ color: '#888', fontFamily: 'monospace' }}>/ {formatTime(duration)}</Text>
      </div>

      {/* 时间轴容器 */}
      <div
        ref={containerRef}
        style={{
          overflowX: 'auto',
          overflowY: 'hidden',
          position: 'relative',
        }}
      >
        {/* 时间刻度 */}
        <div
          style={{
            width: timelineWidth,
            height: 24,
            position: 'relative',
            borderBottom: '1px solid #333',
          }}
          onClick={handleTimelineClick}
        >
          {timeMarkers.map((t) => (
            <div
              key={t}
              style={{
                position: 'absolute',
                left: t * pixelsPerSecond,
                height: '100%',
                borderLeft: '1px solid #444',
                paddingLeft: 4,
              }}
            >
              <Text style={{ color: '#888', fontSize: 10 }}>{formatTime(t)}</Text>
            </div>
          ))}
        </div>

        {/* 轨道 */}
        <div style={{ width: timelineWidth, position: 'relative' }}>
          {tracks.map((track, trackIndex) => (
            <div
              key={track.id}
              style={{
                height: 48,
                position: 'relative',
                borderBottom: '1px solid #333',
                background: '#2a2a2a',
              }}
            >
              {/* 轨道标签 */}
              <div style={{
                position: 'absolute',
                left: 0,
                top: 0,
                width: 60,
                height: '100%',
                background: '#333',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 10,
              }}>
                <Text style={{ color: trackColors[track.type] || '#fff', fontSize: 12 }}>
                  {track.name}
                </Text>
              </div>

              {/* 片段 */}
              {track.clips.map((clip, clipIndex) => {
                const clipStart = clip.start * pixelsPerSecond + 60
                const clipWidth = (clip.end - clip.start) * pixelsPerSecond
                const isSelected = selectedClip?.trackIndex === trackIndex && selectedClip?.clipIndex === clipIndex

                return (
                  <div
                    key={clip.id}
                    onClick={() => onClipSelect?.(trackIndex, clipIndex)}
                    style={{
                      position: 'absolute',
                      left: clipStart,
                      top: 4,
                      width: clipWidth,
                      height: 40,
                      background: trackColors[track.type] || '#666',
                      borderRadius: 4,
                      border: isSelected ? '2px solid #fff' : 'none',
                      cursor: 'pointer',
                      overflow: 'hidden',
                      display: 'flex',
                      alignItems: 'center',
                      paddingLeft: 8,
                    }}
                  >
                    <Text style={{ color: '#fff', fontSize: 11, whiteSpace: 'nowrap' }}>
                      {clip.name || `片段 ${clipIndex + 1}`}
                    </Text>
                  </div>
                )
              })}
            </div>
          ))}

          {/* 播放头 */}
          <div
            style={{
              position: 'absolute',
              left: playheadPosition + 60,
              top: 0,
              width: 2,
              height: '100%',
              background: '#ff4d4f',
              zIndex: 20,
              pointerEvents: 'none',
            }}
          >
            <div style={{
              width: 0,
              height: 0,
              borderLeft: '6px solid transparent',
              borderRight: '6px solid transparent',
              borderTop: '8px solid #ff4d4f',
              position: 'absolute',
              top: -8,
              left: -5,
            }} />
          </div>
        </div>
      </div>
    </div>
  )
}

export default Timeline

