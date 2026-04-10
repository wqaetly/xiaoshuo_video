import { useMemo } from 'react'
import {
  Card,
  Row,
  Col,
  Typography,
  Space,
  Progress,
  Tag,
  List,
  Empty,
  Segmented,
  Badge,
} from 'antd'
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  SyncOutlined,
  PictureOutlined,
  SoundOutlined,
  VideoCameraOutlined,
  UserOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons'
import type { MicroTask } from '../../api/websocket'
import { useState } from 'react'

const { Text } = Typography

interface MicroTaskPanelProps {
  microTasks: MicroTask[]
}

// 任务类型元数据
const TASK_TYPE_META: Record<string, { icon: React.ReactNode; color: string; label: string }> = {
  image: { icon: <PictureOutlined />, color: '#52c41a', label: '图像生成' },
  audio: { icon: <SoundOutlined />, color: '#722ed1', label: '音频生成' },
  video: { icon: <VideoCameraOutlined />, color: '#fa8c16', label: '视频生成' },
  character: { icon: <UserOutlined />, color: '#1890ff', label: '角色设计' },
}

const DEFAULT_META = { icon: <SyncOutlined />, color: '#eb2f96', label: '增量更新' }

function getTaskMeta(taskType: string) {
  return TASK_TYPE_META[taskType] || DEFAULT_META
}

function getStatusTag(status: string) {
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

type FilterType = 'all' | 'active' | 'completed' | 'failed'

export default function MicroTaskPanel({ microTasks }: MicroTaskPanelProps) {
  const [filter, setFilter] = useState<FilterType>('all')

  const counts = useMemo(() => ({
    active: microTasks.filter(t => ['pending', 'running'].includes(t.status)).length,
    completed: microTasks.filter(t => t.status === 'completed').length,
    failed: microTasks.filter(t => t.status === 'failed').length,
  }), [microTasks])

  const filteredTasks = useMemo(() => {
    let tasks = [...microTasks]

    // 筛选
    switch (filter) {
      case 'active':
        tasks = tasks.filter(t => ['pending', 'running'].includes(t.status))
        break
      case 'completed':
        tasks = tasks.filter(t => t.status === 'completed')
        break
      case 'failed':
        tasks = tasks.filter(t => t.status === 'failed')
        break
    }

    // 排序：活跃 > 失败 > 已完成，同级按时间倒序
    tasks.sort((a, b) => {
      const order: Record<string, number> = { running: 0, pending: 1, failed: 2, completed: 3 }
      const oa = order[a.status] ?? 3
      const ob = order[b.status] ?? 3
      if (oa !== ob) return oa - ob
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    })

    return tasks
  }, [microTasks, filter])

  if (microTasks.length === 0) {
    return (
      <Card>
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={
            <Space direction="vertical" size={8} align="center">
              <Text type="secondary">暂无单独执行的任务</Text>
              <Text type="secondary" style={{ fontSize: 12 }}>
                <InfoCircleOutlined style={{ marginRight: 4 }} />
                可在「分镜管理」页面中对单个场景重新生成图像/音频/视频，
                或在「角色管理」页面中重新设计角色立绘。
              </Text>
            </Space>
          }
        />
      </Card>
    )
  }

  return (
    <div>
      {/* 筛选栏 */}
      <Card style={{ marginBottom: 16 }}>
        <Row align="middle" justify="space-between">
          <Col>
            <Segmented
              value={filter}
              onChange={(val) => setFilter(val as FilterType)}
              options={[
                { label: `全部 (${microTasks.length})`, value: 'all' },
                {
                  label: (
                    <Space size={4}>
                      <span>进行中</span>
                      {counts.active > 0 && <Badge count={counts.active} size="small" style={{ backgroundColor: '#1890ff' }} />}
                    </Space>
                  ),
                  value: 'active',
                },
                {
                  label: (
                    <Space size={4}>
                      <span>已完成</span>
                      {counts.completed > 0 && <Badge count={counts.completed} size="small" style={{ backgroundColor: '#52c41a' }} />}
                    </Space>
                  ),
                  value: 'completed',
                },
                {
                  label: (
                    <Space size={4}>
                      <span>失败</span>
                      {counts.failed > 0 && <Badge count={counts.failed} size="small" />}
                    </Space>
                  ),
                  value: 'failed',
                },
              ]}
            />
          </Col>
          <Col>
            <Text type="secondary" style={{ fontSize: 12 }}>
              共 {microTasks.length} 个任务
            </Text>
          </Col>
        </Row>
      </Card>

      {/* 任务列表 */}
      <List
        dataSource={filteredTasks}
        locale={{
          emptyText: <Empty description={`没有${filter === 'active' ? '进行中的' : filter === 'completed' ? '已完成的' : filter === 'failed' ? '失败的' : ''}任务`} />,
        }}
        renderItem={(task) => {
          const meta = getTaskMeta(task.task_type)
          const isActive = ['pending', 'running'].includes(task.status)

          return (
            <Card
              size="small"
              style={{
                marginBottom: 12,
                borderLeft: `3px solid ${meta.color}`,
                background: isActive ? '#fafafa' : undefined,
              }}
            >
              <Row align="middle" gutter={[16, 8]}>
                <Col flex="auto">
                  <Space>
                    <span style={{ color: meta.color, fontSize: 18 }}>{meta.icon}</span>
                    <Text strong>{meta.label}</Text>
                    {task.target_ids.length > 0 && (
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {task.target_ids.length === 1
                          ? task.target_ids[0]
                          : `${task.target_ids.length} 个场景`}
                      </Text>
                    )}
                  </Space>
                </Col>
                <Col>{getStatusTag(task.status)}</Col>
              </Row>

              {/* 运行进度 */}
              {isActive && (
                <div style={{ marginTop: 8 }}>
                  <Progress
                    percent={Math.round(task.progress * 100)}
                    size="small"
                    status={task.status === 'running' ? 'active' : undefined}
                    strokeColor={meta.color}
                  />
                  {task.message && (
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {task.message}
                    </Text>
                  )}
                </div>
              )}

              {/* 完成信息 */}
              {task.status === 'completed' && task.completed_at && (
                <div style={{ marginTop: 4 }}>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    完成时间: {new Date(task.completed_at).toLocaleString()}
                  </Text>
                </div>
              )}

              {/* 失败信息 */}
              {task.status === 'failed' && task.error && (
                <div style={{ marginTop: 4 }}>
                  <Text type="danger" style={{ fontSize: 12 }}>{task.error}</Text>
                </div>
              )}
            </Card>
          )
        }}
      />
    </div>
  )
}
