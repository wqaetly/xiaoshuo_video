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
  Steps,
  List,
  Collapse,
} from 'antd'
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  PictureOutlined,
  SoundOutlined,
  VideoCameraOutlined,
  UserOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons'
import { generationApi, ServiceStatus, GenerationProgress } from '../api/generation'
import { createWebSocket, WSMessage } from '../api/websocket'
import { showApiError } from '../api/client'
import { GENERATION_PHASES } from '../types'

const { Title, Text } = Typography

function GenerationPage() {
  const { projectName } = useParams<{ projectName: string }>()
  const [serviceStatus, setServiceStatus] = useState<ServiceStatus | null>(null)
  const [progress, setProgress] = useState<GenerationProgress | null>(null)
  const [loading, setLoading] = useState(true)
  const [starting, setStarting] = useState(false)
  const [stopping, setStopping] = useState(false)
  const [wsConnected, setWsConnected] = useState(false)

  const fetchStatus = useCallback(async () => {
    try {
      const status = await generationApi.checkServices()
      setServiceStatus(status)
    } catch (error) {
      showApiError(error, '获取服务状态失败')
    }
  }, [])

  const fetchProgress = useCallback(async () => {
    if (!projectName) return
    try {
      const prog = await generationApi.getProgress(projectName)
      setProgress(prog)
    } catch (error) {
      // 只在控制台记录，不频繁弹出提示（因为会轮询）
      console.error('获取进度失败', error)
    }
  }, [projectName])

  // WebSocket 连接处理进度更新
  useEffect(() => {
    if (!projectName) return

    const ws = createWebSocket(`/progress/${projectName}`, {
      onConnect: () => {
        setWsConnected(true)
        console.log('[GenerationPage] WebSocket 已连接')
      },
      onDisconnect: () => {
        setWsConnected(false)
        console.log('[GenerationPage] WebSocket 已断开')
      },
      onMessage: (message: WSMessage) => {
        if (message.type === 'progress') {
          // 收到进度更新时，刷新完整进度数据
          fetchProgress()
        }
      },
    })

    ws.connect()

    return () => {
      ws.disconnect()
    }
  }, [projectName, fetchProgress])

  // 初始化加载和降级轮询
  useEffect(() => {
    const init = async () => {
      setLoading(true)
      await Promise.all([fetchStatus(), fetchProgress()])
      setLoading(false)
    }
    init()

    // 降级轮询: 当 WebSocket 未连接时使用轮询
    const interval = setInterval(() => {
      if (!wsConnected) {
        fetchProgress()
      }
    }, 5000)

    return () => clearInterval(interval)
  }, [fetchStatus, fetchProgress, wsConnected])

  const handleStart = async () => {
    if (!projectName) return
    try {
      setStarting(true)
      await generationApi.start(projectName)
      message.success('生成任务已启动')
      fetchProgress()
    } catch (error) {
      showApiError(error, '启动生成任务失败')
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
      showApiError(error, '停止任务失败')
    } finally {
      setStopping(false)
    }
  }

  // 服务排查建议
  const getServiceTip = (name: string): string => {
    switch (name) {
      case 'Ollama':
        return '请检查 Ollama 是否已启动 (默认端口 11434)。可运行 "ollama serve" 启动服务。'
      case 'ComfyUI':
        return '请检查 ComfyUI 是否已启动 (默认端口 8188)。确保 ComfyUI 的 API 端点正常运行。'
      case 'CosyVoice':
        return '请检查 CosyVoice 服务是否已启动 (默认端口 9880)。如不需要语音合成可忽略。'
      default:
        return '请检查服务是否正常运行。'
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
            {!available && (
              <>
                <br />
                <Text type="danger" style={{ fontSize: 11 }}>
                  {getServiceTip(name)}
                </Text>
              </>
            )}
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

  const isRunning = progress?.is_running ?? false
  const currentPhaseIndex = progress?.phase_index ?? 0
  const isDone = progress?.phase === 'done'
  const hasErrors = (progress?.error_count ?? 0) > 0

  // 获取步骤条状态
  const getStepStatus = (index: number): 'wait' | 'process' | 'finish' | 'error' => {
    if (progress?.phase === 'error') return index === currentPhaseIndex ? 'error' : 'wait'
    if (isDone) return 'finish'
    if (index < currentPhaseIndex) return 'finish'
    if (index === currentPhaseIndex) return isRunning ? 'process' : 'wait'
    return 'wait'
  }

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

      {/* 阶段步骤条 */}
      <Card title="生成阶段" style={{ marginBottom: 24 }}>
        <Steps
          current={currentPhaseIndex}
          size="small"
          items={GENERATION_PHASES.map((phase, index) => ({
            title: phase.name,
            description: index === currentPhaseIndex && isRunning ? (
              <span>
                <LoadingOutlined style={{ marginRight: 4 }} />
                {progress?.message || phase.description}
              </span>
            ) : phase.description,
            status: getStepStatus(index),
          }))}
        />
      </Card>

      {/* 详细进度 */}
      <Card title="详细进度" style={{ marginBottom: 24 }}>
        <Row gutter={[24, 24]}>
          {/* 当前状态 */}
          <Col span={24}>
            <Space size="large" align="center">
              <Tag
                color={isRunning ? 'processing' : isDone ? 'success' : hasErrors ? 'error' : 'default'}
                style={{ fontSize: 14, padding: '4px 12px' }}
              >
                {isRunning && <LoadingOutlined style={{ marginRight: 8 }} />}
                {isDone ? '✅ 已完成' : hasErrors ? '⚠️ 有错误' : progress?.message || '等待开始'}
              </Tag>
            </Space>
          </Col>

          {/* 整体进度条 */}
          <Col span={24}>
            <Text type="secondary" style={{ marginBottom: 8, display: 'block' }}>整体进度</Text>
            <Progress
              percent={Math.round((progress?.progress || 0) * 100)}
              status={isRunning ? 'active' : hasErrors ? 'exception' : undefined}
            />
          </Col>

          {/* 统计数据 */}
          <Col xs={12} sm={6}>
            <Statistic
              title={<><UserOutlined /> 角色</>}
              value={progress?.completed_tasks?.character || 0}
              valueStyle={{ color: '#1890ff' }}
            />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic
              title={<><PictureOutlined /> 图像</>}
              value={progress?.completed_tasks?.image || 0}
              suffix={progress?.total_scenes ? `/ ${progress.total_scenes}` : ''}
              valueStyle={{ color: '#52c41a' }}
            />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic
              title={<><SoundOutlined /> 音频</>}
              value={progress?.completed_tasks?.audio || 0}
              suffix={progress?.total_scenes ? `/ ${progress.total_scenes}` : ''}
              valueStyle={{ color: '#722ed1' }}
            />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic
              title={<><VideoCameraOutlined /> 视频</>}
              value={progress?.completed_tasks?.video || 0}
              suffix={progress?.total_scenes ? `/ ${progress.total_scenes}` : ''}
              valueStyle={{ color: '#fa8c16' }}
            />
          </Col>

          {/* 当前场景进度 */}
          {isRunning && progress && progress.total_scenes && progress.total_scenes > 0 && (
            <Col span={24}>
              <Text type="secondary">当前场景: </Text>
              <Text strong>
                {progress.current_scene_index} / {progress.total_scenes}
              </Text>
              <Progress
                percent={Math.round((progress.current_scene_index / progress.total_scenes) * 100)}
                size="small"
                style={{ marginTop: 8 }}
              />
            </Col>
          )}
        </Row>
      </Card>

      {/* 失败场景列表 */}
      {hasErrors && progress?.failed_scenes && progress.failed_scenes.length > 0 && (
        <Card
          title={
            <Space>
              <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />
              <span>失败场景 ({progress.failed_scenes.length})</span>
            </Space>
          }
          style={{ marginBottom: 24 }}
        >
          <Collapse
            items={[{
              key: 'errors',
              label: `查看 ${progress.failed_scenes.length} 个失败场景`,
              children: (
                <List
                  size="small"
                  dataSource={progress.failed_scenes}
                  renderItem={(item) => (
                    <List.Item>
                      <List.Item.Meta
                        avatar={<CloseCircleOutlined style={{ color: '#ff4d4f' }} />}
                        title={<Text code>{item.scene_id}</Text>}
                        description={
                          <Space direction="vertical" size={0}>
                            <Text type="secondary">阶段: {item.phase}</Text>
                            <Text type="danger">{item.message}</Text>
                          </Space>
                        }
                      />
                    </List.Item>
                  )}
                />
              ),
            }]}
          />
        </Card>
      )}

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
              {isDone ? '重新生成' : '开始生成'}
            </Button>
          )}
          <Button icon={<ReloadOutlined />} onClick={fetchProgress}>
            刷新状态
          </Button>
        </Space>

        {(!serviceStatus?.ollama.available || !serviceStatus?.comfyui.available) && (
          <Alert
            style={{ marginTop: 16 }}
            type="warning"
            message="部分服务不可用，生成功能可能受限"
            description={
              <div>
                <p style={{ margin: '8px 0' }}>请检查以下服务状态后再开始生成：</p>
                <ul style={{ margin: 0, paddingLeft: 20 }}>
                  {!serviceStatus?.ollama.available && (
                    <li><strong>Ollama</strong>：负责分镜生成和角色分析。请运行 <code>ollama serve</code> 启动服务 (端口 11434)。</li>
                  )}
                  {!serviceStatus?.comfyui.available && (
                    <li><strong>ComfyUI</strong>：负责图像生成。请启动 ComfyUI 并确保 API 端点可用 (端口 8188)。</li>
                  )}
                  {!serviceStatus?.cosyvoice.available && (
                    <li><strong>CosyVoice</strong>：负责语音合成 (可选)。请启动 CosyVoice 服务 (端口 9880)。</li>
                  )}
                </ul>
                <p style={{ margin: '8px 0 0 0', fontSize: 12, color: '#666' }}>
                  提示：服务地址可在「设置」页面中配置。
                </p>
              </div>
            }
          />
        )}
      </Card>
    </div>
  )
}

export default GenerationPage

