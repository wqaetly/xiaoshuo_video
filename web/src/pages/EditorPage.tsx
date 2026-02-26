import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import {
  Card,
  Row,
  Col,
  Button,
  Typography,
  Space,
  Slider,
  Select,
  message,
  Spin,
  Empty,
  Divider,
  List,
  Modal,
} from 'antd'
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  StepBackwardOutlined,
  StepForwardOutlined,
  DeleteOutlined,
  DownloadOutlined,
  ZoomInOutlined,
  ZoomOutOutlined,
  SaveOutlined,
} from '@ant-design/icons'
import VideoPlayer, { VideoPlayerRef } from '../components/VideoPlayer'
import Timeline from '../components/Timeline'
import { editorApi } from '../api/editor'
import type { TimelineTrack, MediaInfo } from '../types'

const { Title, Text } = Typography

function EditorPage() {
  const { projectName } = useParams<{ projectName: string }>()
  const playerRef = useRef<VideoPlayerRef>(null)

  // 状态
  const [loading, setLoading] = useState(true)
  const [materials, setMaterials] = useState<{ videos: MediaInfo[]; audios: MediaInfo[] }>({ videos: [], audios: [] })
  const [tracks, setTracks] = useState<TimelineTrack[]>([])
  const [duration, setDuration] = useState(0)
  const [currentTime, setCurrentTime] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)
  const [zoom, setZoom] = useState(1)
  const [selectedClip, setSelectedClip] = useState<{ trackIndex: number; clipIndex: number } | null>(null)
  const [currentVideoSrc, setCurrentVideoSrc] = useState<string>('')
  const [exporting, setExporting] = useState(false)
  const [exportModalVisible, setExportModalVisible] = useState(false)

  // 加载素材和时间轴
  const fetchData = useCallback(async () => {
    if (!projectName) return
    try {
      setLoading(true)
      const [materialData, timelineData] = await Promise.all([
        editorApi.listMaterials(projectName),
        editorApi.getTimeline(projectName),
      ])
      setMaterials({ videos: materialData.videos, audios: materialData.audios })

      // 转换时间轴数据为轨道格式
      const videoTrack: TimelineTrack = {
        id: 'video-1',
        name: '视频',
        type: 'video',
        clips: timelineData.video_clips.map((clip, i) => ({
          id: clip.id,
          name: `视频 ${i + 1}`,
          source: clip.source,
          start: clip.timeline_start,
          end: clip.timeline_start + clip.duration,
          sourceStart: clip.start_time,
          sourceEnd: clip.end_time,
        })),
      }

      const audioTrack: TimelineTrack = {
        id: 'audio-1',
        name: '音频',
        type: 'audio',
        clips: timelineData.audio_clips.map((clip, i) => ({
          id: clip.id,
          name: `音频 ${i + 1}`,
          source: clip.source,
          start: clip.timeline_start,
          end: clip.timeline_start + clip.duration,
          sourceStart: clip.start_time,
          sourceEnd: clip.end_time,
        })),
      }

      const subtitleTrack: TimelineTrack = {
        id: 'subtitle-1',
        name: '字幕',
        type: 'subtitle',
        clips: timelineData.subtitle_clips.map((clip) => ({
          id: clip.id,
          name: clip.text.slice(0, 10),
          start: clip.start_time,
          end: clip.end_time,
        })),
      }

      setTracks([videoTrack, audioTrack, subtitleTrack])
      setDuration(timelineData.total_duration || 60)

      // 设置第一个视频作为预览
      if (materialData.videos.length > 0) {
        setCurrentVideoSrc(`/api/files/${projectName}/${materialData.videos[0].path}`)
      }
    } catch (error) {
      console.error('加载编辑器数据失败:', error)
    } finally {
      setLoading(false)
    }
  }, [projectName])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  // 播放控制
  const handlePlayPause = () => {
    if (isPlaying) {
      playerRef.current?.pause()
    } else {
      playerRef.current?.play()
    }
    setIsPlaying(!isPlaying)
  }

  const handleSeek = (time: number) => {
    setCurrentTime(time)
    playerRef.current?.seek(time)
  }

  const handleTimeUpdate = (time: number) => {
    setCurrentTime(time)
  }

  // 片段选择
  const handleClipSelect = (trackIndex: number, clipIndex: number) => {
    setSelectedClip({ trackIndex, clipIndex })
    const clip = tracks[trackIndex]?.clips[clipIndex]
    if (clip?.source && tracks[trackIndex].type === 'video') {
      setCurrentVideoSrc(`/api/files/${projectName}/${clip.source}`)
    }
  }

  // 删除选中片段
  const handleDeleteClip = () => {
    if (!selectedClip) return
    const newTracks = [...tracks]
    newTracks[selectedClip.trackIndex].clips.splice(selectedClip.clipIndex, 1)
    setTracks(newTracks)
    setSelectedClip(null)
    message.success('片段已删除')
  }

  // 保存时间轴
  const handleSave = async () => {
    if (!projectName) return
    try {
      const timeline = {
        video_clips: tracks.find(t => t.type === 'video')?.clips.map(c => ({
          id: c.id,
          source: c.source || '',
          start_time: c.sourceStart || 0,
          end_time: c.sourceEnd || c.end - c.start,
          timeline_start: c.start,
          duration: c.end - c.start,
        })) || [],
        audio_clips: tracks.find(t => t.type === 'audio')?.clips.map(c => ({
          id: c.id,
          source: c.source || '',
          start_time: c.sourceStart || 0,
          end_time: c.sourceEnd || c.end - c.start,
          timeline_start: c.start,
          duration: c.end - c.start,
        })) || [],
        subtitle_clips: tracks.find(t => t.type === 'subtitle')?.clips.map(c => ({
          id: c.id,
          text: c.name || '',
          start_time: c.start,
          end_time: c.end,
        })) || [],
        total_duration: duration,
      }
      await editorApi.saveTimeline(projectName, timeline)
      message.success('时间轴已保存')
    } catch (error) {
      message.error('保存失败')
    }
  }

  // 导出视频
  const handleExport = async () => {
    if (!projectName) return
    try {
      setExporting(true)
      await editorApi.export(projectName)
      message.success('导出任务已启动')
      setExportModalVisible(false)
    } catch (error) {
      message.error('导出失败')
    } finally {
      setExporting(false)
    }
  }

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 50 }}>
        <Spin size="large" />
      </div>
    )
  }

  return (
    <div style={{ height: 'calc(100vh - 180px)', display: 'flex', flexDirection: 'column' }}>
      {/* 顶部工具栏 */}
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={4} style={{ margin: 0 }}>视频编辑器 - {projectName}</Title>
        <Space>
          <Button icon={<SaveOutlined />} onClick={handleSave}>保存</Button>
          <Button type="primary" icon={<DownloadOutlined />} onClick={() => setExportModalVisible(true)}>
            导出视频
          </Button>
        </Space>
      </div>

      {/* 主编辑区域 */}
      <Row gutter={16} style={{ flex: 1, minHeight: 0 }}>
        {/* 左侧素材面板 */}
        <Col span={4}>
          <Card title="素材库" size="small" style={{ height: '100%', overflow: 'auto' }}>
            <Text type="secondary" style={{ fontSize: 12 }}>视频 ({materials.videos.length})</Text>
            <List
              size="small"
              dataSource={materials.videos}
              renderItem={(item) => (
                <List.Item style={{ padding: '4px 0', cursor: 'pointer' }}>
                  <Text ellipsis style={{ fontSize: 12 }}>{item.path}</Text>
                </List.Item>
              )}
            />
            <Divider style={{ margin: '8px 0' }} />
            <Text type="secondary" style={{ fontSize: 12 }}>音频 ({materials.audios.length})</Text>
            <List
              size="small"
              dataSource={materials.audios}
              renderItem={(item) => (
                <List.Item style={{ padding: '4px 0', cursor: 'pointer' }}>
                  <Text ellipsis style={{ fontSize: 12 }}>{item.path}</Text>
                </List.Item>
              )}
            />
          </Card>
        </Col>

        {/* 中间预览区域 */}
        <Col span={14}>
          <Card size="small" style={{ height: '100%' }} bodyStyle={{ padding: 8 }}>
            <div style={{ background: '#000', borderRadius: 4, marginBottom: 8 }}>
              <VideoPlayer
                ref={playerRef}
                src={currentVideoSrc}
                onTimeUpdate={handleTimeUpdate}
                onPlay={() => setIsPlaying(true)}
                onPause={() => setIsPlaying(false)}
              />
            </div>

            {/* 播放控制 */}
            <Space style={{ width: '100%', justifyContent: 'center' }}>
              <Button icon={<StepBackwardOutlined />} onClick={() => handleSeek(currentTime - 5)} />
              <Button
                type="primary"
                icon={isPlaying ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
                onClick={handlePlayPause}
                size="large"
              />
              <Button icon={<StepForwardOutlined />} onClick={() => handleSeek(currentTime + 5)} />
            </Space>
          </Card>
        </Col>

        {/* 右侧属性面板 */}
        <Col span={6}>
          <Card title="属性" size="small" style={{ height: '100%' }}>
            {selectedClip ? (
              <Space direction="vertical" style={{ width: '100%' }}>
                <Text>选中片段: {tracks[selectedClip.trackIndex]?.clips[selectedClip.clipIndex]?.name}</Text>
                <Button danger icon={<DeleteOutlined />} onClick={handleDeleteClip} block>
                  删除片段
                </Button>
              </Space>
            ) : (
              <Empty description="选择一个片段查看属性" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </Card>
        </Col>
      </Row>

      {/* 底部时间轴 */}
      <div style={{ marginTop: 16 }}>
        {/* 缩放控制 */}
        <div style={{ marginBottom: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
          <Button icon={<ZoomOutOutlined />} onClick={() => setZoom(z => Math.max(0.25, z - 0.25))} size="small" />
          <Slider
            min={0.25}
            max={4}
            step={0.25}
            value={zoom}
            onChange={setZoom}
            style={{ width: 100 }}
          />
          <Button icon={<ZoomInOutlined />} onClick={() => setZoom(z => Math.min(4, z + 0.25))} size="small" />
          <Text type="secondary" style={{ fontSize: 12 }}>{Math.round(zoom * 100)}%</Text>
        </div>

        <Timeline
          tracks={tracks}
          duration={duration}
          currentTime={currentTime}
          zoom={zoom}
          onSeek={handleSeek}
          onClipSelect={handleClipSelect}
          selectedClip={selectedClip}
        />
      </div>

      {/* 导出弹窗 */}
      <Modal
        title="导出视频"
        open={exportModalVisible}
        onCancel={() => setExportModalVisible(false)}
        onOk={handleExport}
        confirmLoading={exporting}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <div>
            <Text>输出格式:</Text>
            <Select defaultValue="mp4" style={{ width: '100%', marginTop: 8 }}>
              <Select.Option value="mp4">MP4 (H.264)</Select.Option>
              <Select.Option value="webm">WebM (VP9)</Select.Option>
            </Select>
          </div>
          <div>
            <Text>输出质量:</Text>
            <Select defaultValue="high" style={{ width: '100%', marginTop: 8 }}>
              <Select.Option value="low">低质量 (快速)</Select.Option>
              <Select.Option value="medium">中等质量</Select.Option>
              <Select.Option value="high">高质量</Select.Option>
            </Select>
          </div>
        </Space>
      </Modal>
    </div>
  )
}

export default EditorPage

