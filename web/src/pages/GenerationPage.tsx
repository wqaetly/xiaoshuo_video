import { useState, useEffect, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import {
  Card,
  Row,
  Col,
  Button,
  Typography,
  Space,
  Progress,
  Tag,
  Spin,
  message,
  Alert,
  Statistic,
} from 'antd'
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
} from '@ant-design/icons'
import { generationApi, ServiceStatus, GenerationProgress } from '../api/generation'

const { Title, Text } = Typography

function GenerationPage() {
  const { projectName } = useParams<{ projectName: string }>()
  const [serviceStatus, setServiceStatus] = useState<ServiceStatus | null>(null)
  const [progress, setProgress] = useState<GenerationProgress | null>(null)
  const [loading, setLoading] = useState(true)
  const [starting, setStarting] = useState(false)
  const [stopping, setStopping] = useState(false)

  const fetchStatus = useCallback(async () => {
    try {
      const status = await generationApi.checkServices()
      setServiceStatus(status)
    } catch (error) {
      console.error('获取服务状态失败')
    }
  }, [])

  const fetchProgress = useCallback(async () => {
    if (!projectName) return
    try {
      const prog = await generationApi.getProgress(projectName)
      setProgress(prog)
    } catch (error) {
      console.error('获取进度失败')
    }
  }, [projectName])

  useEffect(() => {
    const init = async () => {
      setLoading(true)
      await Promise.all([fetchStatus(), fetchProgress()])
      setLoading(false)
    }
    init()

    // 轮询进度
    const interval = setInterval(fetchProgress, 3000)
    return () => clearInterval(interval)
  }, [fetchStatus, fetchProgress])

  const handleStart = async () => {
    if (!projectName) return
    try {
      setStarting(true)
      await generationApi.start(projectName)
      message.success('生成任务已启动')
      fetchProgress()
    } catch (error) {
      message.error('启动失败')
    } finally {
      setStarting(false)
    }
  }

  const handleStop = async () => {
    if (!projectName) return
    try {
      setStopping(true)
      await generationApi.stop(projectName)
      message.success('生成任务已停止')
      fetchProgress()
    } catch (error) {
      message.error('停止失败')
    } finally {
      setStopping(false)
    }
  }

  const renderServiceStatus = (name: string, available: boolean, extra?: string) => (
    <Col xs={12} sm={8} md={6} key={name}>
      <Card size="small">
        <Space>
          {available ? (
            <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 20 }} />
          ) : (
            <CloseCircleOutlined style={{ color: '#ff4d4f', fontSize: 20 }} />
          )}
          <div>
            <Text strong>{name}</Text>
            <br />
            <Text type="secondary" style={{ fontSize: 12 }}>
              {available ? extra || '在线' : '离线'}
            </Text>
          </div>
        </Space>
      </Card>
    </Col>
  )

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 50 }}>
        <Spin size="large" />
      </div>
    )
  }

  const isRunning = progress?.phase !== 'DONE' && progress?.phase !== 'INIT'

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Title level={3} style={{ margin: 0 }}>生成控制 - {projectName}</Title>
      </div>

      {/* 服务状态 */}
      <Card title="服务状态" style={{ marginBottom: 24 }} extra={
        <Button icon={<ReloadOutlined />} onClick={fetchStatus} size="small">刷新</Button>
      }>
        <Row gutter={[16, 16]}>
          {serviceStatus && (
            <>
              {renderServiceStatus('Ollama', serviceStatus.ollama.available, serviceStatus.ollama.model)}
              {renderServiceStatus('ComfyUI', serviceStatus.comfyui.available, `队列: ${serviceStatus.comfyui.queue_size}`)}
              {renderServiceStatus('CosyVoice', serviceStatus.cosyvoice.available)}
            </>
          )}
        </Row>
      </Card>

      {/* 生成进度 */}
      <Card title="生成进度" style={{ marginBottom: 24 }}>
        <Row gutter={[24, 24]}>
          <Col span={24}>
            <Space size="large" align="center">
              <Tag color={isRunning ? 'processing' : 'default'} style={{ fontSize: 14, padding: '4px 12px' }}>
                {isRunning && <LoadingOutlined style={{ marginRight: 8 }} />}
                {progress?.phase || 'INIT'}
              </Tag>
              {progress?.current_task && (
                <Text type="secondary">{progress.current_task}</Text>
              )}
            </Space>
          </Col>
          <Col span={24}>
            <Progress
              percent={Math.round((progress?.progress || 0) * 100)}
              status={isRunning ? 'active' : undefined}
            />
          </Col>
          <Col xs={12} sm={8}>
            <Statistic
              title="已完成场景"
              value={progress?.completed_scenes || 0}
              suffix={`/ ${progress?.total_scenes || 0}`}
            />
          </Col>
        </Row>
      </Card>

      {/* 控制按钮 */}
      <Card>
        <Space size="large">
          {isRunning ? (
            <Button
              type="primary"
              danger
              icon={<PauseCircleOutlined />}
              onClick={handleStop}
              loading={stopping}
              size="large"
            >
              停止生成
            </Button>
          ) : (
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={handleStart}
              loading={starting}
              size="large"
            >
              开始生成
            </Button>
          )}
        </Space>

        {(!serviceStatus?.ollama.available || !serviceStatus?.comfyui.available) && (
          <Alert
            style={{ marginTop: 16 }}
            type="warning"
            message="部分服务不可用"
            description="请确保 Ollama 和 ComfyUI 服务已启动后再开始生成。"
          />
        )}
      </Card>
    </div>
  )
}

export default GenerationPage

