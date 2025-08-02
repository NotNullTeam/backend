"""
提示词模板库 - 初始化模块

本模块定义了IP智慧解答专家系统所使用的各种提示词模板。
"""

from .analysis_prompt import (
    ANALYSIS_PROMPT,
    CLARIFICATION_PROMPT,
    SOLUTION_PROMPT,
    CONTINUE_CONVERSATION_PROMPT,
    FEEDBACK_PROCESSING_PROMPT
)
from .vendor_prompts import HUAWEI_PROMPT, CISCO_PROMPT, H3C_PROMPT, RUIJIE_PROMPT
from .base_prompt import BasePromptTemplate

__all__ = [
    'ANALYSIS_PROMPT',
    'CLARIFICATION_PROMPT',
    'SOLUTION_PROMPT',
    'CONTINUE_CONVERSATION_PROMPT',
    'FEEDBACK_PROCESSING_PROMPT',
    'HUAWEI_PROMPT',
    'CISCO_PROMPT',
    'H3C_PROMPT',
    'RUIJIE_PROMPT',
    'BasePromptTemplate'
]
