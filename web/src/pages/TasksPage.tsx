import { useState, useEffect, useCallback, useMemo } from 'react'
import {
  Card,
  Table,
  Button,
  Typography,
  Space,
  Tag,
  Progress,
  Popconfirm,
  message,
  Tabs,
  List,
  Badge,
  Tooltip,
} from 'antd'
import {
  DeleteOutlined,
  StopOutlined,
  ReloadOutlined,
  ClearOutlined,
  LinkOutlined,
  DisconnectOutlined,
} from '@ant-design/icons'
import { taskApi, LogEntry } from '../api/tasks'
import { showApiError } from '../api/client'
import { useTaskEvents, TaskEvent } from '../hooks'
import type { Task } from '../types'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'

const { Title, Text } = Typography

function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [loading, setLoading] = useState(true)

  // SSE 事件处理
  const handleTaskEvent = useCallback((event: TaskEvent) => {
    // 根据事件类型更新任务状态
    setTasks(prevTasks => {
      const taskIndex = prevTasks.findIndex(t => t.id === event.task_id)

      if (event.event_type === 'task_created') {
        // 新任务创建 - 添加到列表
        if (taskIndex === -1) {
          return [{
            id: event.task_id,
            type: 'unknown',
            project_name: '',
            status: event.status,
            progress: event.progress,
            created_at: event.timestamp,
            ...event.data,
          } as Task, ...prevTasks]
        }
      } else if (taskIndex !== -1) {
        // 更新现有任务
        const updated = [...prevTasks]
        updated[taskIndex] = {
          ...updated[taskIndex],
          status: event.status,
          progress: event.progress,
        }
        return updated
      }
      return prevTasks
    })
  }, [])

  // 使用 SSE Hook
  const { isConnected, events: sseEvents, connect: connectSSE } = useTaskEvents({
    autoConnect: true,
    onEvent: handleTaskEvent,
    onConnect: () => {
      message.success('实时连接已建立')
    },
    onDisconnect: () => {
      message.warning('实时连接断开，将自动重连')
    },
  })

  const fetchTasks = useCallback(async () => {
    try {
      setLoading(true)
      const data = await taskApi.list()
      setTasks(data.tasks)
    } catch (error) {
      showApiError(error, '获取任务列表失败')
    } finally {
      setLoading(false)
    }
  }, [])

  const fetchLogs = useCallback(async () => {
    try {
      const data = await taskApi.getLogs(100)
      setLogs(data)
    } catch (error) {
      showApiError(error, '获取日志失败')
    }
  }, [])

  useEffect(() => {
    fetchTasks()
    fetchLogs()
    // SSE 已启用，降低轮询频率作为后备
    const interval = setInterval(() => {
      if (!isConnected) {
        fetchTasks()
      }
      fetchLogs()
    }, 10000)
    return () => clearInterval(interval)
  }, [fetchTasks, fetchLogs, isConnected])

  const handleCancel = async (taskId: string) => {
    try {
      await taskApi.cancel(taskId)
      message.success('任务已取消')
      fetchTasks()
    } catch (error) {
      showApiError(error, '取消任务失败')
    }
  }

  const handleCancelAll = async () => {
    try {
      await taskApi.cancelAll()
      message.success('所有任务已取消')
      fetchTasks()
    } catch (error) {
      showApiError(error, '取消任务失败')
    }
  }

  const handleClearCompleted = async () => {
    try {
      await taskApi.clearCompleted()
      message.success('已清理完成的任务')
      fetchTasks()
    } catch (error) {
      showApiError(error, '清理任务失败')
    }
  }

  const handleClearLogs = async () => {
    try {
      await taskApi.clearLogs()
      message.success('日志已清除')
      setLogs([])
    } catch (error) {
      showApiError(error, '清除日志失败')
    }
  }

  const getStatusTag = (status: string) => {
    switch (status) {
      case 'completed':
        return <Tag color="success">已完成</Tag>
      case 'running':
        return <Tag color="processing">运行中</Tag>
      case 'pending':
        return <Tag color="default">等待中</Tag>
      case 'failed':
        return <Tag color="error">失败</Tag>
      case 'cancelled':
        return <Tag color="warning">已取消</Tag>
      default:
        return <Tag>{status}</Tag>
    }
  }

  const columns: ColumnsType<Task> = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 100, ellipsis: true },
    { title: '类型', dataIndex: 'type', key: 'type', width: 120 },
    { title: '项目', dataIndex: 'project_name', key: 'project_name', width: 120 },
    { title: '状态', dataIndex: 'status', key: 'status', width: 100, render: (status) => getStatusTag(status) },
    {
      title: '进度', dataIndex: 'progress', key: 'progress', width: 150,
      render: (progress) => <Progress percent={Math.round((progress || 0) * 100)} size="small" />
    },
    {
      title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 160,
      render: (time) => time ? dayjs(time).format('MM-DD HH:mm:ss') : '-'
    },
    {
      title: '操作', key: 'action', width: 80,
      render: (_, record) => (
        record.status === 'running' || record.status === 'pending' ? (
          <Popconfirm title="确定取消?" onConfirm={() => handleCancel(record.id)}>
            <Button type="link" danger size="small" icon={<StopOutlined />} />
          </Popconfirm>
        ) : null
      )
    },
  ]

  const getLogLevelColor = (level: string) => {
    switch (level.toLowerCase()) {
      case 'error': return '#ff4d4f'
      case 'warning': return '#faad14'
      case 'info': return '#1890ff'
      default: return '#666'
    }
  }

  const tabItems = [
    {
      key: 'tasks',
      label: '任务列表',
      children: (
        <>
          <div style={{ marginBottom: 16 }}>
            <Space>
              <Button icon={<ReloadOutlined />} onClick={fetchTasks}>刷新</Button>
              <Popconfirm title="取消所有运行中的任务?" onConfirm={handleCancelAll}>
                <Button danger icon={<StopOutlined />}>取消全部</Button>
              </Popconfirm>
              <Button icon={<ClearOutlined />} onClick={handleClearCompleted}>清理已完成</Button>
            </Space>
          </div>
          <Table
            columns={columns}
            dataSource={tasks}
            rowKey="id"
            loading={loading}
            pagination={{ pageSize: 10 }}
            size="small"
          />
        </>
      ),
    },
    {
      key: 'logs',
      label: '实时日志',
      children: (
        <>
          <div style={{ marginBottom: 16 }}>
            <Space>
              <Button icon={<ReloadOutlined />} onClick={fetchLogs}>刷新</Button>
              <Button icon={<DeleteOutlined />} onClick={handleClearLogs}>清除日志</Button>
            </Space>
          </div>
          <Card style={{ maxHeight: 500, overflow: 'auto', background: '#1e1e1e' }}>
            <List
              size="small"
              dataSource={logs}
              renderItem={(log) => (
                <List.Item style={{ padding: '4px 0', borderBottom: '1px solid #333' }}>
                  <Text style={{ color: '#888', marginRight: 8, fontFamily: 'monospace', fontSize: 12 }}>
                    {log.timestamp}
                  </Text>
                  <Tag color={getLogLevelColor(log.level)} style={{ marginRight: 8 }}>
                    {log.level.toUpperCase()}
                  </Tag>
                  <Text style={{ color: '#fff', fontFamily: 'monospace', fontSize: 12 }}>
                    {log.message}
                  </Text>
                </List.Item>
              )}
            />
          </Card>
        </>
      ),
    },
  ]

  // SSE 连接状态徽章
  const connectionStatus = useMemo(() => (
    <Tooltip title={isConnected ? '实时连接已建立' : '实时连接断开'}>
      <Badge
        status={isConnected ? 'success' : 'error'}
        text={
          <Space size={4}>
            {isConnected ? <LinkOutlined /> : <DisconnectOutlined />}
            <span style={{ fontSize: 12 }}>{isConnected ? '实时同步' : '离线'}</span>
          </Space>
        }
      />
    </Tooltip>
  ), [isConnected])

  return (
    <div>
      <div style={{ marginBottom: 24, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Title level={3} style={{ margin: 0 }}>任务队列</Title>
        <Space>
          {connectionStatus}
          {!isConnected && (
            <Button size="small" onClick={connectSSE}>重新连接</Button>
          )}
        </Space>
      </div>
      <Card>
        <Tabs items={tabItems} />
      </Card>
    </div>
  )
}

export default TasksPage

