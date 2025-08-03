"""
Agent状态定义

定义多轮对话Agent的状态结构，用于langgraph状态机管理。
"""

from typing import TypedDict, List, Dict, Optional


class AgentState(TypedDict):
    """Agent状态结构"""
    messages: List[Dict]      # 对话历史
    context: List[Dict]       # 检索到的知识文档
    user_query: str          # 用户问题
    vendor: Optional[str]    # 设备厂商
    category: Optional[str]  # 问题分类
    need_more_info: bool     # 是否需要更多信息
    solution_ready: bool     # 是否可以给出解决方案
    case_id: str            # 案例ID
    current_node_id: str    # 当前节点ID

    # 扩展字段
    analysis_result: Optional[Dict]  # 分析结果
    clarification: Optional[Dict]    # 澄清信息
    solution: Optional[Dict]         # 解决方案
    error: Optional[str]             # 错误信息
    step: str                        # 当前处理步骤
