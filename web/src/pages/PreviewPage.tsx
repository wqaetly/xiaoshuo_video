import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import {
  Card,
  Row,
  Col,
  Button,
  Typography,
  Space,
  Image,
  Spin,
  Empty,
  message,
  Slider,
  List,
  Tag,
} from 'antd'
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  StepBackwardOutlined,
  StepForwardOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import { sceneApi } from '../api/scenes'
import { editorApi } from '../api/editor'
import { showApiError } from '../api/client'
import type { Scene, MediaInfo } from '../types'

const { Title, Text } = Typography

function PreviewPage() {
  const { projectName } = useParams<{ projectName: string }>()
  const [scenes, setScenes] = useState<Scene[]>([])
  const [, setVideos] = useState<MediaInfo[]>([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [loading, setLoading] = useState(true)
  const [playing, setPlaying] = useState(false)

  const fetchData = async () => {
    if (!projectName) return
    try {
      setLoading(true)
      const [sceneData, materialData] = await Promise.all([
        sceneApi.list(projectName),
        editorApi.listMaterials(projectName),
      ])
      setScenes(sceneData.scenes)
      setVideos(materialData.videos)
    } catch (error) {
      showApiError(error, '加载预览数据失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [projectName])

  const currentScene = scenes[currentIndex]

  const handlePrev = () => {
    setCurrentIndex((prev) => Math.max(0, prev - 1))
    setPlaying(false)
  }

  const handleNext = () => {
    setCurrentIndex((prev) => Math.min(scenes.length - 1, prev + 1))
    setPlaying(false)
  }

  const togglePlay = () => {
    setPlaying(!playing)
  }

  // 自动播放
  useEffect(() => {
    if (!playing) return
    const timer = setInterval(() => {
      setCurrentIndex((prev) => {
        if (prev >= scenes.length - 1) {
          setPlaying(false)
          return prev
        }
        return prev + 1
      })
    }, 3000)
    return () => clearInterval(timer)
  }, [playing, scenes.length])

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 50 }}>
        <Spin size="large" />
      </div>
    )
  }

  return (
    <div>
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={3} style={{ margin: 0 }}>预览 - {projectName}</Title>
        <Button icon={<ReloadOutlined />} onClick={fetchData}>刷新</Button>
      </div>

      {scenes.length === 0 ? (
        <Empty description="暂无可预览的场景" />
      ) : (
        <Row gutter={24}>
          {/* 主预览区域 */}
          <Col xs={24} lg={16}>
            <Card>
              {/* 预览画面 */}
              <div style={{
                background: '#000',
                borderRadius: 8,
                overflow: 'hidden',
                aspectRatio: '16/9',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: 16,
              }}>
                {currentScene?.video_url ? (
                  <video
                    src={currentScene.video_url}
                    style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                    controls
                  />
                ) : currentScene?.image_url ? (
                  <Image
                    src={currentScene.image_url}
                    style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }}
                    preview={false}
                  />
                ) : (
                  <Text style={{ color: '#fff' }}>暂无预览</Text>
                )}
              </div>

              {/* 控制条 */}
              <Space style={{ width: '100%', justifyContent: 'center', marginBottom: 16 }}>
                <Button icon={<StepBackwardOutlined />} onClick={handlePrev} disabled={currentIndex === 0} />
                <Button
                  type="primary"
                  icon={playing ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
                  onClick={togglePlay}
                  size="large"
                />
                <Button icon={<StepForwardOutlined />} onClick={handleNext} disabled={currentIndex === scenes.length - 1} />
              </Space>

              {/* 进度条 */}
              <Slider
                min={0}
                max={scenes.length - 1}
                value={currentIndex}
                onChange={setCurrentIndex}
                marks={{ 0: '1', [scenes.length - 1]: String(scenes.length) }}
              />

              {/* 当前场景信息 */}
              <Card size="small" style={{ marginTop: 16 }}>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Text strong>场景 #{currentScene?.scene_number}</Text>
                  <Text type="secondary">{currentScene?.description || currentScene?.narration || '无描述'}</Text>
                </Space>
              </Card>
            </Card>
          </Col>

          {/* 场景列表 */}
          <Col xs={24} lg={8}>
            <Card title="场景列表" style={{ maxHeight: 600, overflow: 'auto' }}>
              <List
                size="small"
                dataSource={scenes}
                renderItem={(scene, index) => (
                  <List.Item
                    style={{
                      cursor: 'pointer',
                      background: index === currentIndex ? '#e6f7ff' : undefined,
                      padding: '8px 12px',
                      borderRadius: 4,
                    }}
                    onClick={() => { setCurrentIndex(index); setPlaying(false) }}
                  >
                    <Space>
                      <Text strong>#{scene.scene_number}</Text>
                      {scene.video_url && <Tag color="blue">视频</Tag>}
                      {scene.image_url && !scene.video_url && <Tag color="green">图片</Tag>}
                    </Space>
                  </List.Item>
                )}
              />
            </Card>
          </Col>
        </Row>
      )}
    </div>
  )
}

export default PreviewPage

