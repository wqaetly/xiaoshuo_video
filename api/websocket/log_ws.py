"""
WebSocket 实时日志推送

支持按项目隔离连接，避免消息广播给不相关的项目。
"""
import asyncio
from typing import Dict, Optional, Set
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


class ConnectionManager:
    """WebSocket 连接管理器

    支持两种连接类型：
    1. 全局连接（日志）：接收所有消息
    2. 项目连接（进度）：只接收特定项目的消息
    """

    def __init__(self):
        # 全局连接（日志广播）
        self.global_connections: Set[WebSocket] = set()
        # 按项目分组的连接 {project_name: set of websockets}
        self.project_connections: Dict[str, Set[WebSocket]] = {}

    async def connect_global(self, websocket: WebSocket) -> None:
        """建立全局连接（用于日志广播）"""
        await websocket.accept()
        self.global_connections.add(websocket)

    async def connect_project(self, websocket: WebSocket, project_name: str) -> None:
        """建立项目连接（用于项目进度）"""
        await websocket.accept()
        if project_name not in self.project_connections:
            self.project_connections[project_name] = set()
        self.project_connections[project_name].add(websocket)

    def disconnect_global(self, websocket: WebSocket) -> None:
        """断开全局连接"""
        self.global_connections.discard(websocket)

    def disconnect_project(self, websocket: WebSocket, project_name: str) -> None:
        """断开项目连接"""
        if project_name in self.project_connections:
            self.project_connections[project_name].discard(websocket)
            # 清理空的项目集合
            if not self.project_connections[project_name]:
                del self.project_connections[project_name]

    async def _send_to_connections(
        self, connections: Set[WebSocket], message: dict
    ) -> Set[WebSocket]:
        """发送消息到连接集合，返回已断开的连接"""
        disconnected = set()
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.add(connection)
        return disconnected

    async def broadcast_global(self, message: dict) -> None:
        """广播消息给所有全局连接"""
        disconnected = await self._send_to_connections(self.global_connections, message)
        self.global_connections -= disconnected

    async def broadcast_project(self, project_name: str, message: dict) -> None:
        """广播消息给特定项目的连接"""
        if project_name not in self.project_connections:
            return
        connections = self.project_connections[project_name]
        disconnected = await self._send_to_connections(connections, message)
        self.project_connections[project_name] -= disconnected

    async def send_log(
        self, level: str, message: str, module: Optional[str] = None
    ) -> None:
        """发送日志消息（全局广播）"""
        log_entry = {
            "type": "log",
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "module": module,
        }
        await self.broadcast_global(log_entry)

    async def send_progress(
        self,
        project_name: str,
        phase: str,
        task: str,
        progress: float,
        message: str = "",
    ) -> None:
        """发送进度更新（按项目广播）"""
        progress_entry = {
            "type": "progress",
            "timestamp": datetime.now().isoformat(),
            "project": project_name,
            "phase": phase,
            "task": task,
            "progress": progress,
            "message": message,
        }
        await self.broadcast_project(project_name, progress_entry)

    async def send_task_update(
        self,
        task_id: str,
        status: str,
        progress: float = 0.0,
        project_name: Optional[str] = None,
    ) -> None:
        """发送任务状态更新"""
        task_entry = {
            "type": "task_update",
            "timestamp": datetime.now().isoformat(),
            "task_id": task_id,
            "status": status,
            "progress": progress,
        }
        if project_name:
            await self.broadcast_project(project_name, task_entry)
        else:
            await self.broadcast_global(task_entry)

    def get_connection_count(self, project_name: Optional[str] = None) -> int:
        """获取连接数量"""
        if project_name:
            return len(self.project_connections.get(project_name, set()))
        return len(self.global_connections)


# 全局连接管理器
manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    """获取连接管理器实例"""
    return manager


@router.websocket("/logs")
async def websocket_logs(websocket: WebSocket):
    """实时日志 WebSocket 端点（全局广播）"""
    await manager.connect_global(websocket)
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
        manager.disconnect_global(websocket)


@router.websocket("/progress/{project_name}")
async def websocket_progress(websocket: WebSocket, project_name: str):
    """项目进度 WebSocket 端点（按项目隔离）"""
    await manager.connect_project(websocket, project_name)
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
        manager.disconnect_project(websocket, project_name)

