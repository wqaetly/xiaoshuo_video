"""
WebSocket 实时日志推送
"""
import asyncio
from typing import List, Set
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        """建立连接"""
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        """断开连接"""
        self.active_connections.discard(websocket)

    async def broadcast(self, message: dict):
        """广播消息给所有连接"""
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.add(connection)
        # 清理断开的连接
        self.active_connections -= disconnected

    async def send_log(self, level: str, message: str, module: str = None):
        """发送日志消息"""
        log_entry = {
            "type": "log",
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "module": module,
        }
        await self.broadcast(log_entry)

    async def send_progress(
        self, phase: str, task: str, progress: float, message: str = ""
    ):
        """发送进度更新"""
        progress_entry = {
            "type": "progress",
            "timestamp": datetime.now().isoformat(),
            "phase": phase,
            "task": task,
            "progress": progress,
            "message": message,
        }
        await self.broadcast(progress_entry)

    async def send_task_update(self, task_id: str, status: str, progress: float = 0.0):
        """发送任务状态更新"""
        task_entry = {
            "type": "task_update",
            "timestamp": datetime.now().isoformat(),
            "task_id": task_id,
            "status": status,
            "progress": progress,
        }
        await self.broadcast(task_entry)


# 全局连接管理器
manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    """获取连接管理器实例"""
    return manager


@router.websocket("/logs")
async def websocket_logs(websocket: WebSocket):
    """实时日志 WebSocket 端点"""
    await manager.connect(websocket)
    try:
        # 发送欢迎消息
        await websocket.send_json({
            "type": "connected",
            "message": "WebSocket 已连接",
            "timestamp": datetime.now().isoformat(),
        })
        # 保持连接，等待关闭
        while True:
            try:
                # 接收客户端消息（心跳等）
                data = await asyncio.wait_for(
                    websocket.receive_text(), timeout=30.0
                )
                if data == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                # 发送心跳检测
                await websocket.send_json({"type": "heartbeat"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.websocket("/progress/{project_name}")
async def websocket_progress(websocket: WebSocket, project_name: str):
    """项目进度 WebSocket 端点"""
    await manager.connect(websocket)
    try:
        await websocket.send_json({
            "type": "connected",
            "project": project_name,
            "timestamp": datetime.now().isoformat(),
        })
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(), timeout=30.0
                )
                if data == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "heartbeat"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)

