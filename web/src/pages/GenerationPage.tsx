import { useState, useEffect, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import { Tabs, Spin, Typography, Badge, Space } from 'antd'
import {
  ThunderboltOutlined,
  ToolOutlined,
  LoadingOutlined,
} from '@ant-design/icons'
import { generationApi, type ServiceStatus, type GenerationProgress } from '../api/generation'
import { createWebSocket, type WSMessage, type MicroTask } from '../api/websocket'
import { showApiError } from '../api/client'
import PipelinePanel from './generation/PipelinePanel'
import MicroTaskPanel from './generation/MicroTaskPanel'

const { Title } = Typography

function GenerationPage() {
  const { projectName } = useParams<{ projectName: string }>()
  const [serviceStatus, setServiceStatus] = useState<ServiceStatus | null>(null)
  const [progress, setProgress] = useState<GenerationProgress | null>(null)
  const [loading, setLoading] = useState(true)
  const [wsConnected, setWsConnected] = useState(false)
  const [microTasks, setMicroTasks] = useState<MicroTask[]>([])

  // --- 数据获取 ---
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
      console.error('获取进度失败', error)
    }
  }, [projectName])

  const fetchMicroTasks = useCallback(async () => {
    if (!projectName) return
    try {
      const result = await generationApi.getMicroTasks(projectName)
      setMicroTasks(result.tasks as MicroTask[])
    } catch (error) {
      console.error('获取微任务失败', error)
    }
  }, [projectName])

  // --- WebSocket ---
  useEffect(() => {
    if (!projectName) return

    const ws = createWebSocket(`/progress/${projectName}`, {
      onConnect: () => {
        setWsConnected(true)
      },
      onDisconnect: () => {
        setWsConnected(false)
      },
      onMessage: (wsMsg: WSMessage) => {
        if (wsMsg.type === 'progress') {
          fetchProgress()
        } else if (wsMsg.type === 'micro_task_update' && wsMsg.micro_task) {
          const updatedTask = wsMsg.micro_task
          setMicroTasks(prev => {
            const index = prev.findIndex(t => t.task_id === updatedTask.task_id)
            if (index >= 0) {
              const newList = [...prev]
              newList[index] = updatedTask
              return newList
            }
            return [...prev, updatedTask]
          })
        }
      },
    })

    ws.connect()
    return () => { ws.disconnect() }
  }, [projectName, fetchProgress])

  // --- 初始化和降级轮询 ---
  useEffect(() => {
    const init = async () => {
      setLoading(true)
      await Promise.all([fetchProgress(), fetchMicroTasks()])
      setLoading(false)
      fetchStatus()
    }
    init()

    const interval = setInterval(() => {
      if (!wsConnected) {
        fetchProgress()
        fetchMicroTasks()
      }
    }, 5000)

    return () => clearInterval(interval)
  }, [fetchStatus, fetchProgress, fetchMicroTasks, wsConnected])

  // --- 加载中 ---
  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 50 }}>
        <Spin size="large" />
      </div>
    )
  }

  const isRunning = progress?.is_running ?? false
  const activeMicroTaskCount = microTasks.filter(t => ['pending', 'running'].includes(t.status)).length

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Title level={3} style={{ margin: 0 }}>生成控制 - {projectName}</Title>
      </div>

      <Tabs
        defaultActiveKey="pipeline"
        type="card"
        size="large"
        items={[
          {
            key: 'pipeline',
            label: (
              <Space>
                <ThunderboltOutlined />
                <span>全流程自动化</span>
                {isRunning && (
                  <Badge
                    status="processing"
                    text={<span style={{ fontSize: 12, color: '#1890ff' }}><LoadingOutlined /> 运行中</span>}
                  />
                )}
              </Space>
            ),
            children: (
              <PipelinePanel
                projectName={projectName!}
                progress={progress}
                serviceStatus={serviceStatus}
                onRefreshProgress={fetchProgress}
                onRefreshStatus={fetchStatus}
              />
            ),
          },
          {
            key: 'micro',
            label: (
              <Space>
                <ToolOutlined />
                <span>单独任务</span>
                {activeMicroTaskCount > 0 && (
                  <Badge count={activeMicroTaskCount} size="small" style={{ backgroundColor: '#eb2f96' }} />
                )}
              </Space>
            ),
            children: <MicroTaskPanel microTasks={microTasks} />,
          },
        ]}
      />
    </div>
  )
}

export default GenerationPage
