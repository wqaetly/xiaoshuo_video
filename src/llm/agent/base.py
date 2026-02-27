"""Agent 基础类定义

实现 Tool-Calling 模式的 Agent 基类，支持：
- 工具注册和调用
- 对话记忆管理
- ReAct 循环执行
"""
import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional, Callable, TypeVar, Generic
from ..client import OllamaClient
from ...utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


class AgentState(Enum):
    """Agent 执行状态"""
    IDLE = "idle"
    THINKING = "thinking"
    TOOL_CALLING = "tool_calling"
    OBSERVING = "observing"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class AgentMessage:
    """Agent 对话消息"""
    role: str  # "system" | "user" | "assistant" | "tool"
    content: str
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    tool_result: Optional[Any] = None


@dataclass
class AgentTool:
    """Agent 工具定义"""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema 格式
    func: Callable[..., Any]
    
    def to_schema(self) -> Dict[str, Any]:
        """转换为 JSON Schema 格式 (用于提示词)"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }
    
    def execute(self, **kwargs) -> Any:
        """执行工具"""
        try:
            return self.func(**kwargs)
        except Exception as e:
            logger.error(f"工具 {self.name} 执行失败: {e}")
            raise


class AgentToolkit:
    """工具集合管理"""
    
    def __init__(self):
        self._tools: Dict[str, AgentTool] = {}
    
    def register(self, tool: AgentTool) -> None:
        """注册工具"""
        self._tools[tool.name] = tool
        logger.debug(f"注册工具: {tool.name}")
    
    def get(self, name: str) -> Optional[AgentTool]:
        """获取工具"""
        return self._tools.get(name)
    
    def list_tools(self) -> List[AgentTool]:
        """列出所有工具"""
        return list(self._tools.values())
    
    def get_tools_schema(self) -> str:
        """生成工具列表的 JSON Schema 描述"""
        schemas = [t.to_schema() for t in self._tools.values()]
        return json.dumps(schemas, ensure_ascii=False, indent=2)
    
    def execute(self, tool_name: str, **kwargs) -> Any:
        """执行指定工具"""
        tool = self.get(tool_name)
        if tool is None:
            raise ValueError(f"工具不存在: {tool_name}")
        return tool.execute(**kwargs)


@dataclass
class AgentContext(Generic[T]):
    """Agent 执行上下文"""
    state: AgentState = AgentState.IDLE
    messages: List[AgentMessage] = field(default_factory=list)
    result: Optional[T] = None
    iteration: int = 0
    max_iterations: int = 20
    errors: List[str] = field(default_factory=list)
    
    def add_message(self, message: AgentMessage) -> None:
        """添加消息"""
        self.messages.append(message)
    
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """获取对话历史 (用于 LLM 输入)"""
        history = []
        for msg in self.messages:
            if msg.role == "tool":
                # 工具结果作为助手消息的一部分
                content = f"[工具调用结果] {msg.tool_name}:\n{json.dumps(msg.tool_result, ensure_ascii=False, indent=2)}"
                history.append({"role": "assistant", "content": content})
            else:
                history.append({"role": msg.role, "content": msg.content})
        return history


class BaseAgent(ABC, Generic[T]):
    """Agent 基类"""
    
    def __init__(
        self,
        llm_client: OllamaClient,
        toolkit: Optional[AgentToolkit] = None,
        max_iterations: int = 20
    ):
        self.llm = llm_client
        self.toolkit = toolkit or AgentToolkit()
        self.max_iterations = max_iterations
        self._setup_tools()
    
    @abstractmethod
    def _setup_tools(self) -> None:
        """子类实现: 注册工具"""
        pass
    
    @abstractmethod
    def _get_system_prompt(self) -> str:
        """子类实现: 获取系统提示词"""
        pass
    
    @abstractmethod
    def _parse_final_result(self, context: AgentContext[T]) -> T:
        """子类实现: 解析最终结果"""
        pass

    def run(self, user_input: str) -> T:
        """执行 Agent ReAct 循环"""
        context = AgentContext[T](max_iterations=self.max_iterations)

        # 添加系统消息
        context.add_message(AgentMessage(role="system", content=self._get_system_prompt()))
        # 添加用户输入
        context.add_message(AgentMessage(role="user", content=user_input))

        context.state = AgentState.THINKING

        while context.iteration < context.max_iterations:
            context.iteration += 1
            logger.info(f"Agent 迭代 {context.iteration}/{context.max_iterations}")

            try:
                # 1. 推理阶段 - 获取 LLM 响应
                response = self._think(context)

                # 2. 解析响应 - 判断是工具调用还是最终答案
                action = self._parse_response(response)

                if action["type"] == "final_answer":
                    context.state = AgentState.COMPLETED
                    context.result = self._parse_final_result(context)
                    logger.info("Agent 完成执行")
                    return context.result

                elif action["type"] == "tool_call":
                    context.state = AgentState.TOOL_CALLING
                    tool_name = action["tool_name"]
                    tool_args = action["tool_args"]

                    logger.info(f"调用工具: {tool_name}")

                    # 3. 执行工具
                    try:
                        tool_result = self.toolkit.execute(tool_name, **tool_args)

                        # 记录工具调用和结果
                        context.add_message(AgentMessage(
                            role="tool",
                            content="",
                            tool_name=tool_name,
                            tool_args=tool_args,
                            tool_result=tool_result
                        ))
                        context.state = AgentState.OBSERVING

                    except Exception as e:
                        error_msg = f"工具 {tool_name} 执行错误: {str(e)}"
                        context.errors.append(error_msg)
                        context.add_message(AgentMessage(
                            role="tool",
                            content="",
                            tool_name=tool_name,
                            tool_args=tool_args,
                            tool_result={"error": error_msg}
                        ))

                else:
                    # 未识别的响应，记录并继续
                    logger.warning(f"未识别的响应类型: {action}")
                    context.add_message(AgentMessage(
                        role="assistant",
                        content=response
                    ))

                context.state = AgentState.THINKING

            except Exception as e:
                logger.error(f"Agent 执行错误: {e}")
                context.errors.append(str(e))
                context.state = AgentState.ERROR
                raise

        # 达到最大迭代次数
        logger.warning(f"Agent 达到最大迭代次数 {self.max_iterations}")
        context.result = self._parse_final_result(context)
        return context.result

    def _think(self, context: AgentContext[T]) -> str:
        """推理阶段 - 调用 LLM"""
        messages = context.get_conversation_history()
        return self.llm.chat_messages(messages, temperature=0.5, max_tokens=4096)

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """解析 LLM 响应，提取工具调用或最终答案"""
        # 尝试提取工具调用
        tool_call = self._extract_tool_call(response)
        if tool_call:
            return {"type": "tool_call", **tool_call}

        # 检查是否是最终答案
        if self._is_final_answer(response):
            return {"type": "final_answer", "content": response}

        # 默认继续思考
        return {"type": "continue", "content": response}

    def _extract_tool_call(self, response: str) -> Optional[Dict[str, Any]]:
        """从响应中提取工具调用"""
        # 匹配格式: <tool_call>{"name": "xxx", "arguments": {...}}</tool_call>
        pattern = r'<tool_call>\s*(\{.*?\})\s*</tool_call>'
        match = re.search(pattern, response, re.DOTALL)

        if match:
            try:
                call_data = json.loads(match.group(1))
                return {
                    "tool_name": call_data.get("name"),
                    "tool_args": call_data.get("arguments", {})
                }
            except json.JSONDecodeError:
                logger.warning("工具调用 JSON 解析失败")

        return None

    def _is_final_answer(self, response: str) -> bool:
        """判断是否是最终答案"""
        # 检查是否包含结束标记
        return "<final_answer>" in response or "TASK_COMPLETE" in response

