"""
基础提示词模板

本模块定义了基础的提示词模板类和通用模板。
"""

from typing import Dict, Any, Optional


class BasePromptTemplate:
    """基础提示词模板类"""

    def __init__(self, template: str, variables: Optional[Dict[str, str]] = None):
        self.template = template
        self.variables = variables or {}

    def format(self, **kwargs) -> str:
        """格式化提示词模板"""
        # 合并默认变量和传入的变量
        format_vars = {**self.variables, **kwargs}
        try:
            return self.template.format(**format_vars)
        except KeyError as e:
            raise ValueError(f"缺少必需的变量: {e}")

    def get_required_variables(self) -> list:
        """获取模板所需的变量列表"""
        import re
        pattern = r'\{([^}]+)\}'
        return list(set(re.findall(pattern, self.template)))


# 系统级别的基础提示词
SYSTEM_ROLE_PROMPT = """你是一位资深的网络运维专家，精通各大厂商的网络设备配置和故障排除。你的任务是帮助用户解决网络相关问题。

请遵循以下原则：
1. 提供准确、专业的技术建议
2. 根据设备厂商提供对应的命令语法
3. 步骤要详细、可执行
4. 如果信息不足，主动询问必要的信息
5. 引用文档时使用 [doc1], [doc2] 等标记
6. 保持回答的结构化和易读性"""

# 通用错误处理提示词
ERROR_HANDLING_PROMPT = """当遇到以下情况时，请按照对应方式处理：

1. 信息不足：
   - 明确说明需要哪些额外信息
   - 提供具体的问题列表供用户回答
   - 说明这些信息的重要性

2. 设备厂商未知：
   - 询问用户设备的具体型号和厂商
   - 提供通用的解决思路
   - 说明不同厂商可能有差异

3. 问题超出能力范围：
   - 诚实说明限制
   - 提供可能的解决方向
   - 建议寻求专业技术支持

4. 涉及敏感操作：
   - 强调操作风险
   - 建议在测试环境验证
   - 提醒备份配置"""
