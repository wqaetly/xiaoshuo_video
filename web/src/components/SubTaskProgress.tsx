/**
 * 子任务进度组件 - 展示各阶段的详细子任务进度
 */
import { useMemo } from 'react'
import {
  Collapse,
  Progress,
  Tag,
  Space,
  Typography,
  Badge,
  Tooltip,
  List,
  Row,
  Col,
} from 'antd'
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  ClockCircleOutlined,
  MinusCircleOutlined,
  RightOutlined,
  DownOutlined,
} from '@ant-design/icons'
import type { PhaseProgress, SubTaskStatus } from '../api/generation'

const { Text } = Typography

interface SubTaskProgressProps {
  phasesDetail: PhaseProgress[]
  currentPhaseId?: string
  isRunning?: boolean
}

// 状态图标映射
const StatusIcon = ({ status }: { status: string }) => {
  switch (status) {
    case 'completed':
      return <CheckCircleOutlined style={{ color: '#52c41a' }} />
    case 'running':
      return <LoadingOutlined style={{ color: '#1890ff' }} spin />
    case 'failed':
      return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
    case 'skipped':
      return <MinusCircleOutlined style={{ color: '#d9d9d9' }} />
    default:
      return <ClockCircleOutlined style={{ color: '#d9d9d9' }} />
  }
}

// 状态标签
const StatusTag = ({ status }: { status: string }) => {
  const config: Record<string, { color: string; text: string }> = {
    completed: { color: 'success', text: '完成' },
    running: { color: 'processing', text: '运行中' },
    failed: { color: 'error', text: '失败' },
    skipped: { color: 'default', text: '跳过' },
    pending: { color: 'default', text: '等待' },
  }
  const { color, text } = config[status] || config.pending
  return <Tag color={color}>{text}</Tag>
}

// 单个子任务项
const SubTaskItem = ({ task }: { task: SubTaskStatus }) => (
  <List.Item style={{ padding: '8px 0' }}>
    <Row align="middle" style={{ width: '100%' }} gutter={12}>
      <Col flex="24px">
        <StatusIcon status={task.status} />
      </Col>
      <Col flex="auto">
        <Space direction="vertical" size={0} style={{ width: '100%' }}>
          <Text ellipsis style={{ maxWidth: 200 }}>{task.name}</Text>
          {task.message && (
            <Text type="secondary" style={{ fontSize: 12 }}>{task.message}</Text>
          )}
          {task.error && (
            <Tooltip title={task.error}>
              <Text type="danger" style={{ fontSize: 12 }} ellipsis>
                {task.error}
              </Text>
            </Tooltip>
          )}
        </Space>
      </Col>
      <Col flex="60px" style={{ textAlign: 'right' }}>
        {task.status === 'running' && (
          <Progress
            type="circle"
            percent={Math.round(task.progress * 100)}
            size={28}
            strokeWidth={8}
          />
        )}
      </Col>
    </Row>
  </List.Item>
)

// 阶段面板
const PhasePanel = ({ phase }: { phase: PhaseProgress }) => {
  const { completed_items, total_items, failed_items } = phase
  const progressPercent = total_items > 0 ? Math.round((completed_items / total_items) * 100) : 0

  return (
    <div style={{ padding: '12px 0' }}>
      <Row align="middle" justify="space-between" style={{ marginBottom: 8 }}>
        <Col>
          <Space>
            <StatusTag status={phase.status} />
            <Text strong>{phase.phase_name}</Text>
          </Space>
        </Col>
        <Col>
          <Space size="small">
            {total_items > 0 && (
              <Text type="secondary" style={{ fontSize: 12 }}>
                {completed_items}/{total_items}
                {failed_items > 0 && (
                  <Text type="danger" style={{ marginLeft: 4 }}>
                    ({failed_items}失败)
                  </Text>
                )}
              </Text>
            )}
            <Progress
              percent={progressPercent}
              size="small"
              style={{ width: 80, marginBottom: 0 }}
              showInfo={false}
              status={phase.status === 'failed' ? 'exception' : undefined}
            />
          </Space>
        </Col>
      </Row>

      {/* 子任务列表 */}
      {phase.sub_tasks.length > 0 && (
        <List
          size="small"
          dataSource={phase.sub_tasks}
          renderItem={(task) => <SubTaskItem task={task} />}
          style={{
            maxHeight: 300,
            overflow: 'auto',
            background: '#fafafa',
            borderRadius: 8,
            padding: '0 12px',
          }}
        />
      )}
    </div>
  )
}

export default function SubTaskProgress({
  phasesDetail,
  currentPhaseId,
  isRunning,
}: SubTaskProgressProps) {
  // 默认展开当前运行的阶段
  const defaultActiveKey = useMemo(() => {
    if (currentPhaseId && isRunning) {
      return [currentPhaseId]
    }
    return []
  }, [currentPhaseId, isRunning])

  if (!phasesDetail || phasesDetail.length === 0) {
    return null
  }

  // 只显示有子任务的阶段
  const phasesWithTasks = phasesDetail.filter(p => p.total_items > 0)

  if (phasesWithTasks.length === 0) {
    return null
  }

  return (
    <Collapse
      defaultActiveKey={defaultActiveKey}
      expandIcon={({ isActive }) => isActive ? <DownOutlined /> : <RightOutlined />}
      items={phasesWithTasks.map(phase => ({
        key: phase.phase_id,
        label: (
          <Space>
            <StatusIcon status={phase.status} />
            <span>{phase.phase_name}</span>
            <Badge
              count={phase.completed_items}
              showZero
              style={{ backgroundColor: '#52c41a' }}
            />
            {phase.failed_items > 0 && (
              <Badge count={phase.failed_items} style={{ backgroundColor: '#ff4d4f' }} />
            )}
          </Space>
        ),
        children: <PhasePanel phase={phase} />,
      }))}
    />
  )
}

