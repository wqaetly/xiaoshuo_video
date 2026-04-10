import {
  Card,
  Row,
  Col,
  Button,
  Typography,
  Space,
  Progress,
  Tag,
  Statistic,
  Steps,
  List,
  Collapse,
  Dropdown,
  Modal,
  Alert,
  message,
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
  RightOutlined,
  UndoOutlined,
  CaretRightOutlined,
  StopOutlined,
} from '@ant-design/icons'
import { generationApi, type ServiceStatus, type GenerationProgress } from '../../api/generation'
import { showApiError } from '../../api/client'
import { GENERATION_PHASES, REGENERATE_PHASE, type PhaseInfo } from '../../types'
import SubTaskProgress from '../../components/SubTaskProgress'
import ServiceStatusCard from './ServiceStatusCard'
import { useState } from 'react'

const { Text } = Typography

interface PipelinePanelProps {
  projectName: string
  progress: GenerationProgress | null
  serviceStatus: ServiceStatus | null
  onRefreshProgress: () => void
  onRefreshStatus: () => void
}

export default function PipelinePanel({
  projectName,
  progress,
  serviceStatus,
  onRefreshProgress,
  onRefreshStatus,
}: PipelinePanelProps) {
  const [starting, setStarting] = useState(false)
  const [stopping, setStopping] = useState(false)

  const isRunning = progress?.is_running ?? false
  const currentPhaseIndex = progress?.phase_index ?? 0
  const isDone = progress?.phase === 'done'
  const hasErrors = (progress?.error_count ?? 0) > 0
  const isRegenerateTask = progress?.phase === 'regenerate'
  const isInit = !progress || progress.phase === 'init'
  // 判断是否处于"已中断"状态：非运行中、非完成、非初始化、有进度
  const isInterrupted = !isRunning && !isDone && !isInit && progress?.phase !== 'error'
  const isFailed = !isRunning && progress?.phase === 'error'

  // --- 操作处理 ---
  const handleStart = async () => {
    try {
      setStarting(true)
      await generationApi.start(projectName)
      message.success('生成任务已启动')
      onRefreshProgress()
    } catch (error) {
      showApiError(error, '启动生成任务失败')
    } finally {
      setStarting(false)
    }
  }

  const handleStop = async () => {
    Modal.confirm({
      title: '中断执行',
      content: '确认中断当前正在执行的全流程任务？当前场景处理完成后会安全停止，下次可从中断处继续。',
      okText: '确认中断',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          setStopping(true)
          await generationApi.stop(projectName)
          message.success('已发送中断请求，等待当前场景处理完成...')
          onRefreshProgress()
        } catch (error) {
          showApiError(error, '中断任务失败')
        } finally {
          setStopping(false)
        }
      },
    })
  }

  const handleResume = async () => {
    try {
      setStarting(true)
      await generationApi.start(projectName, { resume: true })
      message.success('已从中断处继续执行')
      onRefreshProgress()
    } catch (error) {
      showApiError(error, '继续执行失败')
    } finally {
      setStarting(false)
    }
  }

  const handleStartFrom = async (phaseId: string, phaseName: string) => {
    Modal.confirm({
      title: '从指定阶段重试',
      content: `确认从「${phaseName}」阶段开始，执行后续所有阶段？之前该阶段及后续阶段的产物会被重新生成。`,
      okText: '确认开始',
      cancelText: '取消',
      onOk: async () => {
        try {
          setStarting(true)
          await generationApi.start(projectName, { start_from: phaseId })
          message.success(`已从「${phaseName}」阶段开始生成`)
          onRefreshProgress()
        } catch (error) {
          showApiError(error, '启动生成任务失败')
        } finally {
          setStarting(false)
        }
      },
    })
  }

  const handleRestart = async () => {
    Modal.confirm({
      title: '重新开始',
      content: '确认从头开始执行全流程？所有已生成的产物将被重新生成。',
      okText: '确认重新开始',
      okButtonProps: { danger: true },
      cancelText: '取消',
      onOk: async () => {
        try {
          setStarting(true)
          await generationApi.start(projectName, { resume: false })
          message.success('已重新开始全流程')
          onRefreshProgress()
        } catch (error) {
          showApiError(error, '启动失败')
        } finally {
          setStarting(false)
        }
      },
    })
  }

  // --- 工具函数 ---
  const getFailedPhaseInfo = (): PhaseInfo | null => {
    if (!progress) return null
    if (progress.phases_detail?.length) {
      const failedPhase = progress.phases_detail.find(p => p.status === 'failed')
      if (failedPhase) {
        return GENERATION_PHASES.find(p => p.id === failedPhase.phase_id) || null
      }
    }
    if (progress.failed_scenes?.length) {
      const phaseId = progress.failed_scenes[0].phase
      return GENERATION_PHASES.find(p => p.id === phaseId) || null
    }
    if (progress.phase && progress.phase !== 'error' && progress.phase !== 'done' && progress.phase !== 'init') {
      return GENERATION_PHASES.find(p => p.id === progress.phase) || null
    }
    return null
  }

  const failedPhaseInfo = getFailedPhaseInfo()

  // 获取当前停止的阶段信息
  const getStoppedPhaseInfo = (): PhaseInfo | null => {
    if (!progress?.phase) return null
    if (progress.phase === 'regenerate') return REGENERATE_PHASE
    return GENERATION_PHASES.find(p => p.id === progress.phase) || null
  }
  const stoppedPhaseInfo = getStoppedPhaseInfo()

  const getStepStatus = (index: number): 'wait' | 'process' | 'finish' | 'error' => {
    if (progress?.phase === 'error') return index === currentPhaseIndex ? 'error' : index < currentPhaseIndex ? 'finish' : 'wait'
    if (isDone) return 'finish'
    if (index < currentPhaseIndex) return 'finish'
    if (index === currentPhaseIndex) return isRunning ? 'process' : 'wait'
    return 'wait'
  }

  const getCurrentPhaseName = () => {
    if (isRegenerateTask) return REGENERATE_PHASE.name
    return GENERATION_PHASES[currentPhaseIndex]?.name || '处理中'
  }

  // --- 渲染 ---

  // 流水线状态标识
  const renderStatusBanner = () => {
    if (isRunning) return null // 运行中用独立的卡片显示

    if (isInit) {
      return (
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 24, borderRadius: 8 }}
          message="等待开始"
          description="项目已就绪，点击下方「开始生成」启动全流程自动化任务。"
        />
      )
    }

    if (isDone) {
      return (
        <Alert
          type="success"
          showIcon
          icon={<CheckCircleOutlined />}
          style={{ marginBottom: 24, borderRadius: 8 }}
          message="全流程已完成"
          description={
            <Space>
              <span>所有阶段均已完成。</span>
              <Button size="small" onClick={handleRestart} loading={starting}>重新生成</Button>
            </Space>
          }
        />
      )
    }

    // 中断或失败 - 统一的重试控制栏
    if (isInterrupted || isFailed || hasErrors) {
      const statusIcon = isFailed ? <CloseCircleOutlined /> : <ExclamationCircleOutlined />
      const statusTitle = isFailed
        ? `执行失败${failedPhaseInfo ? ` - 停止于「${failedPhaseInfo.name}」阶段` : ''}`
        : `已中断${stoppedPhaseInfo ? ` - 停止于「${stoppedPhaseInfo.name}」阶段` : ''}`

      const completedInfo = progress?.current_item_total
        ? `已完成 ${progress.current_item_index}/${progress.current_item_total} 项`
        : null
      const errorInfo = (progress?.error_count ?? 0) > 0 ? `${progress!.error_count} 个错误` : null
      const statusDesc = [completedInfo, errorInfo].filter(Boolean).join('，')

      return (
        <Card
          style={{
            marginBottom: 24,
            borderRadius: 8,
            border: isFailed ? '1px solid #ffccc7' : '1px solid #ffe58f',
            background: isFailed ? '#fff2f0' : '#fffbe6',
          }}
        >
          <Row align="middle" gutter={[16, 16]}>
            <Col flex="auto">
              <Space direction="vertical" size={4}>
                <Space>
                  <span style={{ fontSize: 20, color: isFailed ? '#ff4d4f' : '#faad14' }}>
                    {statusIcon}
                  </span>
                  <Text strong style={{ fontSize: 16 }}>{statusTitle}</Text>
                </Space>
                {statusDesc && <Text type="secondary">{statusDesc}</Text>}
              </Space>
            </Col>
            <Col>
              <Space wrap>
                <Button
                  type="primary"
                  icon={<CaretRightOutlined />}
                  onClick={handleResume}
                  loading={starting}
                >
                  继续执行
                </Button>
                {failedPhaseInfo && (
                  <Button
                    icon={<ReloadOutlined />}
                    onClick={() => handleStartFrom(failedPhaseInfo.id, failedPhaseInfo.name)}
                    loading={starting}
                  >
                    从此阶段重试
                  </Button>
                )}
                <Dropdown
                  menu={{
                    items: GENERATION_PHASES
                      .filter(p => p.id !== 'init')
                      .map(p => ({
                        key: p.id,
                        label: `从「${p.name}」开始`,
                        icon: <RightOutlined />,
                      })),
                    onClick: ({ key }) => {
                      const phase = GENERATION_PHASES.find(p => p.id === key)
                      if (phase) handleStartFrom(phase.id, phase.name)
                    },
                  }}
                >
                  <Button icon={<UndoOutlined />}>从指定阶段...</Button>
                </Dropdown>
                <Button
                  danger
                  icon={<ReloadOutlined />}
                  onClick={handleRestart}
                  loading={starting}
                >
                  重新开始
                </Button>
              </Space>
            </Col>
          </Row>
        </Card>
      )
    }

    return null
  }

  return (
    <div>
      {/* 服务状态 */}
      <ServiceStatusCard serviceStatus={serviceStatus} onRefresh={onRefreshStatus} />

      {/* 状态横幅 / 重试控制栏 */}
      {renderStatusBanner()}

      {/* 阶段步骤条 */}
      <Card
        title="生成阶段"
        style={{ marginBottom: 24 }}
        extra={
          !isRunning && !isInit && (
            <Dropdown
              menu={{
                items: GENERATION_PHASES
                  .filter(p => p.id !== 'init')
                  .map(p => ({
                    key: p.id,
                    label: `从「${p.name}」开始`,
                    icon: <RightOutlined />,
                  })),
                onClick: ({ key }) => {
                  const phase = GENERATION_PHASES.find(p => p.id === key)
                  if (phase) handleStartFrom(phase.id, phase.name)
                },
              }}
            >
              <Button size="small" icon={<ReloadOutlined />}>从指定阶段重试</Button>
            </Dropdown>
          )
        }
      >
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

      {/* 当前运行状态卡片 */}
      {isRunning && (
        <Card
          style={{
            marginBottom: 24,
            background: isRegenerateTask
              ? 'linear-gradient(135deg, #52c41a 0%, #389e0d 100%)'
              : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            border: 'none',
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
                    : progress?.message || '处理中...'}
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
                fontWeight: 'bold',
              }}>
                {Math.round((progress?.progress || 0) * 100)}%
              </div>
            </Col>
            <Col>
              <Button
                type="default"
                danger
                icon={<StopOutlined />}
                onClick={handleStop}
                loading={stopping}
                size="large"
                style={{
                  background: 'rgba(255,255,255,0.15)',
                  borderColor: 'rgba(255,255,255,0.4)',
                  color: 'white',
                }}
              >
                中断
              </Button>
            </Col>
          </Row>
        </Card>
      )}

      {/* 子任务详细进度 */}
      {progress?.phases_detail && progress.phases_detail.some(p => p.total_items > 0) && (
        <Card title="任务详情" style={{ marginBottom: 24 }}>
          <SubTaskProgress
            phasesDetail={progress.phases_detail}
            currentPhaseId={progress.phase}
            isRunning={isRunning}
          />
        </Card>
      )}

      {/* 详细进度 */}
      <Card title="详细进度" style={{ marginBottom: 24 }}>
        <Row gutter={[24, 24]}>
          <Col span={24}>
            <Space size="large" align="center">
              <Tag
                color={isRunning ? 'processing' : isDone ? 'success' : hasErrors ? 'error' : 'default'}
                style={{ fontSize: 14, padding: '4px 12px' }}
              >
                {isRunning && <LoadingOutlined style={{ marginRight: 8 }} />}
                {isDone ? '已完成' : hasErrors ? '有错误' : isRunning ? '运行中' : progress?.message || '等待开始'}
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

          <Col span={24}>
            <Text type="secondary" style={{ marginBottom: 8, display: 'block' }}>整体进度</Text>
            <Progress
              percent={Math.round((progress?.progress || 0) * 100)}
              status={isRunning ? 'active' : hasErrors ? 'exception' : isDone ? 'success' : undefined}
              format={(percent) => `${percent}%`}
            />
          </Col>

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

      {/* 底部控制按钮 */}
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
              中断执行
            </Button>
          ) : (
            <>
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={isInit ? handleStart : handleResume}
                loading={starting}
                size="large"
              >
                {isInit ? '开始生成' : isDone ? '重新生成' : '继续执行'}
              </Button>
              {!isInit && !isDone && (
                <Button icon={<ReloadOutlined />} onClick={handleRestart} loading={starting}>
                  重新开始
                </Button>
              )}
            </>
          )}
          <Button icon={<ReloadOutlined />} onClick={onRefreshProgress}>
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
