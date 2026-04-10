/**
 * 子任务进度组件 - 展示各阶段的详细子任务进度
 */
import { useState, useMemo, useEffect } from 'react'
import {
  Collapse,
  Progress,
  Tag,
  Space,
  Typography,
  Badge,
  Tooltip,
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

// 子任务行背景色
const getSubTaskBg = (status: string): string | undefined => {
  switch (status) {
    case 'running':
      return '#e6f4ff'   // 浅蓝
    case 'failed':
      return '#fff2f0'   // 浅红
    default:
      return undefined
  }
}

// 状态排序权重（running 排最前，pending 排最后）
const statusOrder: Record<string, number> = {
  running: 0,
  failed: 1,
  pending: 3,
  completed: 2,
  skipped: 4,
}

// 单个子任务项
const SubTaskItem = ({ task, index, total }: { task: SubTaskStatus; index: number; total: number }) => (
  <div
    style={{
      padding: '6px 12px',
      background: getSubTaskBg(task.status),
      borderRadius: 6,
      marginBottom: 4,
      transition: 'background 0.3s',
    }}
  >
    <Row align="middle" style={{ width: '100%' }} gutter={8}>
      <Col flex="24px">
        <StatusIcon status={task.status} />
      </Col>
      <Col flex="auto" style={{ minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Text type="secondary" style={{ fontSize: 11, flexShrink: 0 }}>
            {index + 1}/{total}
          </Text>
          <Text
            ellipsis
            style={{
              fontWeight: task.status === 'running' ? 600 : undefined,
              color: task.status === 'running' ? '#1890ff' : undefined,
            }}
          >
            {task.name}
          </Text>
        </div>
        {task.status === 'running' && task.message && (
          <Text type="secondary" style={{ fontSize: 12 }}>
            <LoadingOutlined style={{ marginRight: 4 }} />
            {task.message}
          </Text>
        )}
        {task.error && (
          <Tooltip title={task.error}>
            <Text type="danger" style={{ fontSize: 12 }} ellipsis>
              {task.error}
            </Text>
          </Tooltip>
        )}
      </Col>
      <Col flex="40px" style={{ textAlign: 'right' }}>
        {task.status === 'running' && (
          <LoadingOutlined style={{ color: '#1890ff', fontSize: 16 }} spin />
        )}
        {task.status === 'completed' && (
          <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 14 }} />
        )}
        {task.status === 'failed' && (
          <CloseCircleOutlined style={{ color: '#ff4d4f', fontSize: 14 }} />
        )}
      </Col>
    </Row>
  </div>
)

// 阶段面板
const PhasePanel = ({ phase }: { phase: PhaseProgress }) => {
  const { completed_items, total_items, failed_items } = phase
  const progressPercent = total_items > 0 ? Math.round((completed_items / total_items) * 100) : 0

  // 对子任务排序：running > failed > completed > pending
  const sortedTasks = useMemo(() => {
    // 保留原始索引以显示序号
    const indexed = phase.sub_tasks.map((t, i) => ({ task: t, originalIndex: i }))
    return indexed.sort((a, b) => {
      const oa = statusOrder[a.task.status] ?? 3
      const ob = statusOrder[b.task.status] ?? 3
      if (oa !== ob) return oa - ob
      return a.originalIndex - b.originalIndex
    })
  }, [phase.sub_tasks])

  return (
    <div>
      {/* 阶段进度摘要 */}
      <Row align="middle" justify="space-between" style={{ marginBottom: 8, padding: '0 4px' }}>
        <Col>
          <Space size="small">
            <Text type="secondary" style={{ fontSize: 13 }}>
              {completed_items}/{total_items} 完成
            </Text>
            {failed_items > 0 && (
              <Text type="danger" style={{ fontSize: 13 }}>
                {failed_items} 失败
              </Text>
            )}
          </Space>
        </Col>
        <Col style={{ width: 120 }}>
          <Progress
            percent={progressPercent}
            size="small"
            status={phase.status === 'failed' ? 'exception' : phase.status === 'running' ? 'active' : undefined}
          />
        </Col>
      </Row>

      {/* 子任务列表 */}
      {sortedTasks.length > 0 && (
        <div
          style={{
            maxHeight: 360,
            overflow: 'auto',
            borderRadius: 8,
            border: '1px solid #f0f0f0',
            padding: 4,
          }}
        >
          {sortedTasks.map(({ task, originalIndex }) => (
            <SubTaskItem
              key={task.id}
              task={task}
              index={originalIndex}
              total={total_items}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export default function SubTaskProgress({
  phasesDetail,
  currentPhaseId,
  isRunning,
}: SubTaskProgressProps) {
  // 动态控制展开的面板（运行中的阶段 + 有失败的阶段自动展开）
  const computeActiveKeys = useMemo(() => {
    const keys: string[] = []
    for (const phase of phasesDetail) {
      if (phase.status === 'running') {
        keys.push(phase.phase_id)
      } else if (phase.failed_items > 0) {
        keys.push(phase.phase_id)
      }
    }
    // 如果没有运行中的和失败的，展开最近有数据的阶段
    if (keys.length === 0 && currentPhaseId) {
      keys.push(currentPhaseId)
    }
    return keys
  }, [phasesDetail, currentPhaseId])

  const [activeKeys, setActiveKeys] = useState<string[]>(computeActiveKeys)

  // 当运行状态或阶段变化时，自动更新展开
  useEffect(() => {
    setActiveKeys(computeActiveKeys)
  }, [computeActiveKeys])

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
      activeKey={activeKeys}
      onChange={(keys) => setActiveKeys(keys as string[])}
      expandIcon={({ isActive }) => isActive ? <DownOutlined /> : <RightOutlined />}
      items={phasesWithTasks.map(phase => ({
        key: phase.phase_id,
        label: (
          <Row align="middle" style={{ width: '100%' }}>
            <Col flex="auto">
              <Space>
                <StatusIcon status={phase.status} />
                <Text strong={phase.status === 'running'}>
                  {phase.phase_name}
                </Text>
                {phase.total_items > 0 && (
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {phase.completed_items}/{phase.total_items}
                  </Text>
                )}
              </Space>
            </Col>
            <Col>
              <Space size={4}>
                {phase.status === 'running' && (
                  <Tag color="processing" style={{ margin: 0 }}>
                    <LoadingOutlined style={{ marginRight: 4 }} />运行中
                  </Tag>
                )}
                {phase.status === 'completed' && (
                  <Badge count={phase.completed_items} showZero style={{ backgroundColor: '#52c41a' }} />
                )}
                {phase.failed_items > 0 && (
                  <Badge count={phase.failed_items} style={{ backgroundColor: '#ff4d4f' }} />
                )}
              </Space>
            </Col>
          </Row>
        ),
        children: <PhasePanel phase={phase} />,
        style: phase.status === 'running'
          ? { background: '#f0f7ff', borderColor: '#91caff' }
          : phase.failed_items > 0
            ? { background: '#fff7f5', borderColor: '#ffccc7' }
            : undefined,
      }))}
    />
  )
}
