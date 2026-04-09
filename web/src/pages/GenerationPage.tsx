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
  Badge,
  Empty,
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
  ThunderboltOutlined,
  ClockCircleOutlined,
  SyncOutlined,
} from '@ant-design/icons'
import { generationApi, ServiceStatus, GenerationProgress } from '../api/generation'
import { createWebSocket, WSMessage, MicroTask } from '../api/websocket'
import { showApiError } from '../api/client'
import { GENERATION_PHASES, REGENERATE_PHASE } from '../types'
import SubTaskProgress from '../components/SubTaskProgress'

const { Title, Text } = Typography

function GenerationPage() {
  const { projectName } = useParams<{ projectName: string }>()
  const [serviceStatus, setServiceStatus] = useState<ServiceStatus | null>(null)
  const [progress, setProgress] = useState<GenerationProgress | null>(null)
  const [loading, setLoading] = useState(true)
  const [starting, setStarting] = useState(false)
  const [stopping, setStopping] = useState(false)
  const [wsConnected, setWsConnected] = useState(false)
  // 微任务状态 - 独立于全局流程的小任务（如单独重新生成某张图片）
  const [microTasks, setMicroTasks] = useState<MicroTask[]>([])

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

  // 获取微任务列表
  const fetchMicroTasks = useCallback(async () => {
    if (!projectName) return
    try {
      const result = await generationApi.getMicroTasks(projectName)
      setMicroTasks(result.tasks as MicroTask[])
    } catch (error) {
      console.error('获取微任务失败', error)
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
      onMessage: (wsMsg: WSMessage) => {
        if (wsMsg.type === 'progress') {
          // 收到全局进度更新时，刷新完整进度数据
          fetchProgress()
        } else if (wsMsg.type === 'micro_task_update' && wsMsg.micro_task) {
          // 收到微任务更新时，更新微任务列表
          const updatedTask = wsMsg.micro_task
          setMicroTasks(prev => {
            const index = prev.findIndex(t => t.task_id === updatedTask.task_id)
            if (index >= 0) {
              // 更新已有任务
              const newList = [...prev]
              newList[index] = updatedTask
              return newList
            } else {
              // 添加新任务
              return [...prev, updatedTask]
            }
          })
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
      // 先快速加载进度数据，服务状态在后台检查（避免超时阻塞页面）
      await Promise.all([fetchProgress(), fetchMicroTasks()])
      setLoading(false)
      // 服务状态异步加载，不阻塞页面显示
      fetchStatus()
    }
    init()

    // 降级轮询: 当 WebSocket 未连接时使用轮询
    const interval = setInterval(() => {
      if (!wsConnected) {
        fetchProgress()
        fetchMicroTasks()
      }
    }, 5000)

    return () => clearInterval(interval)
  }, [fetchStatus, fetchProgress, fetchMicroTasks, wsConnected])

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
  // 判断是否为增量更新（regenerate）任务
  const isRegenerateTask = progress?.phase === 'regenerate'

  // 获取步骤条状态
  const getStepStatus = (index: number): 'wait' | 'process' | 'finish' | 'error' => {
    if (progress?.phase === 'error') return index === currentPhaseIndex ? 'error' : 'wait'
    if (isDone) return 'finish'
    if (index < currentPhaseIndex) return 'finish'
    if (index === currentPhaseIndex) return isRunning ? 'process' : 'wait'
    return 'wait'
  }

  // 获取当前阶段名称（支持 regenerate）
  const getCurrentPhaseName = () => {
    if (isRegenerateTask) return REGENERATE_PHASE.name
    return GENERATION_PHASES[currentPhaseIndex]?.name || '处理中'
  }

  // 获取微任务类型的图标和颜色
  const getMicroTaskMeta = (taskType: string): { icon: React.ReactNode; color: string; label: string } => {
    switch (taskType) {
      case 'image':
        return { icon: <PictureOutlined />, color: '#52c41a', label: '图像生成' }
      case 'audio':
        return { icon: <SoundOutlined />, color: '#722ed1', label: '音频生成' }
      case 'video':
        return { icon: <VideoCameraOutlined />, color: '#fa8c16', label: '视频生成' }
      case 'character':
        return { icon: <UserOutlined />, color: '#1890ff', label: '角色设计' }
      case 'regenerate':
      case 'mixed':
      default:
        return { icon: <SyncOutlined />, color: '#eb2f96', label: '增量更新' }
    }
  }

  // 微任务状态标签
  const getMicroTaskStatusTag = (status: string) => {
    switch (status) {
      case 'pending':
        return <Tag icon={<ClockCircleOutlined />} color="default">等待中</Tag>
      case 'running':
        return <Tag icon={<SyncOutlined spin />} color="processing">运行中</Tag>
      case 'completed':
        return <Tag icon={<CheckCircleOutlined />} color="success">已完成</Tag>
      case 'failed':
        return <Tag icon={<CloseCircleOutlined />} color="error">失败</Tag>
      default:
        return <Tag color="default">{status}</Tag>
    }
  }

  // 过滤显示的微任务（活跃的排前面，最多显示最近10个）
  const displayMicroTasks = [...microTasks]
    .sort((a, b) => {
      // 活跃任务排前面
      const activeA = ['pending', 'running'].includes(a.status) ? 0 : 1
      const activeB = ['pending', 'running'].includes(b.status) ? 0 : 1
      if (activeA !== activeB) return activeA - activeB
      // 按创建时间倒序
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    })
    .slice(0, 10)

  const activeMicroTaskCount = microTasks.filter(t => ['pending', 'running'].includes(t.status)).length

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

      {/* 当前任务状态 - 新增醒目卡片 */}
      {isRunning && (
        <Card
          style={{
            marginBottom: 24,
            background: isRegenerateTask
              ? 'linear-gradient(135deg, #52c41a 0%, #389e0d 100%)'  // 绿色渐变用于增量更新
              : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            border: 'none'
          }}
        >
          <Row align="middle" gutter={[16, 16]}>
            <Col flex="auto">
              <div style={{ color: 'white' }}>
                <div style={{ fontSize: 12, opacity: 0.8, marginBottom: 4 }}>
                  {isRegenerateTask ? '增量更新中' : '当前阶段'}
                </div>
                <div style={{ fontSize: 20, fontWeight: 600, marginBottom: 8 }}>
                  {getCurrentPhaseName()}
                </div>
                <div style={{ fontSize: 14, opacity: 0.9 }}>
                  <LoadingOutlined style={{ marginRight: 8 }} />
                  {progress?.current_item
                    ? `正在处理: ${progress.current_item}`
                    : progress?.message || '处理中...'
                  }
                </div>
                {(progress?.current_item_total ?? 0) > 0 && progress && (
                  <div style={{ marginTop: 8 }}>
                    <Text style={{ color: 'rgba(255,255,255,0.9)', fontSize: 13 }}>
                      进度: {progress.current_item_index} / {progress.current_item_total}
                    </Text>
                    <Progress
                      percent={Math.round((progress?.phase_progress || 0) * 100)}
                      strokeColor="rgba(255,255,255,0.8)"
                      trailColor="rgba(255,255,255,0.2)"
                      showInfo={false}
                      size="small"
                      style={{ marginTop: 4 }}
                    />
                  </div>
                )}
              </div>
            </Col>
            <Col>
              <div style={{
                width: 80,
                height: 80,
                borderRadius: '50%',
                background: 'rgba(255,255,255,0.2)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'white',
                fontSize: 24,
                fontWeight: 'bold'
              }}>
                {Math.round((progress?.progress || 0) * 100)}%
              </div>
            </Col>
          </Row>
        </Card>
      )}

      {/* 详细进度 */}
      <Card title="详细进度" style={{ marginBottom: 24 }}>
        <Row gutter={[24, 24]}>
          {/* 当前状态标签 */}
          <Col span={24}>
            <Space size="large" align="center">
              <Tag
                color={isRunning ? 'processing' : isDone ? 'success' : hasErrors ? 'error' : 'default'}
                style={{ fontSize: 14, padding: '4px 12px' }}
              >
                {isRunning && <LoadingOutlined style={{ marginRight: 8 }} />}
                {isDone ? '✅ 已完成' : hasErrors ? '⚠️ 有错误' : isRunning ? '运行中' : progress?.message || '等待开始'}
              </Tag>
              {!isRunning && !isDone && progress?.phase && progress.phase !== 'init' && (
                <Text type="secondary">
                  上次停止于: {
                    progress.phase === 'regenerate'
                      ? REGENERATE_PHASE.name
                      : (GENERATION_PHASES.find(p => p.id === progress.phase)?.name || progress.phase)
                  }
                </Text>
              )}
            </Space>
          </Col>

          {/* 整体进度条 */}
          <Col span={24}>
            <Text type="secondary" style={{ marginBottom: 8, display: 'block' }}>整体进度</Text>
            <Progress
              percent={Math.round((progress?.progress || 0) * 100)}
              status={isRunning ? 'active' : hasErrors ? 'exception' : isDone ? 'success' : undefined}
              format={(percent) => `${percent}%`}
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

          {/* 场景总进度 */}
          {progress && progress.total_scenes > 0 && (
            <Col span={24}>
              <Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>
                场景总进度: {progress.current_scene_index} / {progress.total_scenes}
              </Text>
              <Progress
                percent={Math.round((progress.current_scene_index / progress.total_scenes) * 100)}
                size="small"
                strokeColor="#1890ff"
              />
            </Col>
          )}
        </Row>
      </Card>

      {/* 子任务详细进度 */}
      {progress?.phases_detail && progress.phases_detail.length > 0 && (
        <Card title="任务详情" style={{ marginBottom: 24 }}>
          <SubTaskProgress
            phasesDetail={progress.phases_detail}
            currentPhaseId={progress.phase}
            isRunning={isRunning}
          />
        </Card>
      )}

      {/* 手动任务进度（微任务）- 独立于全局流程 */}
      {displayMicroTasks.length > 0 && (
        <Card
          title={
            <Space>
              <ThunderboltOutlined style={{ color: '#eb2f96' }} />
              <span>手动任务</span>
              {activeMicroTaskCount > 0 && (
                <Badge count={activeMicroTaskCount} style={{ backgroundColor: '#eb2f96' }} />
              )}
            </Space>
          }
          extra={
            <Text type="secondary" style={{ fontSize: 12 }}>
              单独触发的重新生成任务（如重新生成某张图片）
            </Text>
          }
          style={{ marginBottom: 24 }}
        >
          <List
            size="small"
            dataSource={displayMicroTasks}
            renderItem={(task) => {
              const meta = getMicroTaskMeta(task.task_type)
              const isActive = ['pending', 'running'].includes(task.status)
              return (
                <List.Item
                  style={{
                    background: isActive ? '#fafafa' : undefined,
                    padding: '12px 16px',
                    borderRadius: 8,
                    marginBottom: 8,
                  }}
                >
                  <div style={{ width: '100%' }}>
                    <Row align="middle" gutter={[16, 8]}>
                      <Col flex="auto">
                        <Space>
                          <span style={{ color: meta.color, fontSize: 16 }}>{meta.icon}</span>
                          <Text strong>{meta.label}</Text>
                          {task.target_ids.length > 0 && (
                            <Text type="secondary" style={{ fontSize: 12 }}>
                              {task.target_ids.length === 1
                                ? task.target_ids[0]
                                : `${task.target_ids.length} 个场景`
                              }
                            </Text>
                          )}
                        </Space>
                      </Col>
                      <Col>
                        {getMicroTaskStatusTag(task.status)}
                      </Col>
                    </Row>
                    {isActive && (
                      <div style={{ marginTop: 8 }}>
                        <Progress
                          percent={Math.round(task.progress * 100)}
                          size="small"
                          status={task.status === 'running' ? 'active' : undefined}
                          strokeColor={meta.color}
                        />
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {task.message}
                        </Text>
                      </div>
                    )}
                    {task.status === 'failed' && task.error && (
                      <div style={{ marginTop: 4 }}>
                        <Text type="danger" style={{ fontSize: 12 }}>{task.error}</Text>
                      </div>
                    )}
                  </div>
                </List.Item>
              )
            }}
            locale={{ emptyText: <Empty description="暂无手动任务" /> }}
          />
        </Card>
      )}

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

