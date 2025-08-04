"""
厂商命令生成服务

根据节点内容和设备厂商生成相应的网络命令，替换Mock实现。
"""

import logging
from typing import List, Dict, Any, Optional
from app.models.case import Node


logger = logging.getLogger(__name__)


class VendorCommandService:
    """厂商命令生成服务类"""

    def __init__(self):
        self.logger = logger
        self._load_command_templates()

    def _load_command_templates(self):
        """加载命令模板"""
        self.command_templates = {
            'Huawei': {
                'basic_check': [
                    'display version',
                    'display device',
                    'display interface brief'
                ],
                'ospf_troubleshoot': [
                    'display ospf peer',
                    'display interface brief',
                    'display ospf interface',
                    'display ospf database',
                    'display ospf routing'
                ],
                'bgp_troubleshoot': [
                    'display bgp peer',
                    'display bgp routing-table',
                    'display ip routing-table bgp',
                    'display bgp network'
                ],
                'interface_check': [
                    'display interface {interface}',
                    'display interface {interface} statistics',
                    'ping -c 5 {target_ip}',
                    'tracert {target_ip}'
                ],
                'mtu_check': [
                    'display interface {interface}',
                    'ping -s 1472 -c 5 {target_ip}',
                    'ping -s 1500 -c 5 {target_ip}'
                ],
                'routing_check': [
                    'display ip routing-table',
                    'display ip routing-table {destination}',
                    'display arp all'
                ]
            },
            'Cisco': {
                'basic_check': [
                    'show version',
                    'show inventory',
                    'show interfaces brief'
                ],
                'ospf_troubleshoot': [
                    'show ip ospf neighbor',
                    'show interfaces brief',
                    'show ip ospf interface',
                    'show ip ospf database',
                    'show ip route ospf'
                ],
                'bgp_troubleshoot': [
                    'show bgp summary',
                    'show bgp',
                    'show ip route bgp',
                    'show bgp neighbors'
                ],
                'interface_check': [
                    'show interface {interface}',
                    'show interface {interface} statistics',
                    'ping {target_ip} repeat 5',
                    'traceroute {target_ip}'
                ],
                'mtu_check': [
                    'show interface {interface}',
                    'ping {target_ip} size 1472 repeat 5',
                    'ping {target_ip} size 1500 repeat 5'
                ],
                'routing_check': [
                    'show ip route',
                    'show ip route {destination}',
                    'show arp'
                ]
            },
            'Juniper': {
                'basic_check': [
                    'show version',
                    'show chassis hardware',
                    'show interfaces terse'
                ],
                'ospf_troubleshoot': [
                    'show ospf neighbor',
                    'show interfaces terse',
                    'show ospf interface',
                    'show ospf database',
                    'show route protocol ospf'
                ],
                'bgp_troubleshoot': [
                    'show bgp summary',
                    'show route protocol bgp',
                    'show bgp neighbor',
                    'show bgp group'
                ],
                'interface_check': [
                    'show interfaces {interface}',
                    'show interfaces {interface} statistics',
                    'ping {target_ip} count 5',
                    'traceroute {target_ip}'
                ],
                'mtu_check': [
                    'show interfaces {interface}',
                    'ping {target_ip} size 1472 count 5',
                    'ping {target_ip} size 1500 count 5'
                ],
                'routing_check': [
                    'show route',
                    'show route {destination}',
                    'show arp'
                ]
            },
            'H3C': {
                'basic_check': [
                    'display version',
                    'display device',
                    'display interface brief'
                ],
                'ospf_troubleshoot': [
                    'display ospf peer',
                    'display interface brief',
                    'display ospf interface',
                    'display ospf lsdb',
                    'display ip routing-table protocol ospf'
                ],
                'bgp_troubleshoot': [
                    'display bgp peer',
                    'display bgp routing-table',
                    'display ip routing-table protocol bgp',
                    'display bgp network'
                ],
                'interface_check': [
                    'display interface {interface}',
                    'display interface {interface} counters',
                    'ping -c 5 {target_ip}',
                    'tracert {target_ip}'
                ],
                'mtu_check': [
                    'display interface {interface}',
                    'ping -s 1472 -c 5 {target_ip}',
                    'ping -s 1500 -c 5 {target_ip}'
                ],
                'routing_check': [
                    'display ip routing-table',
                    'display ip routing-table {destination}',
                    'display arp all'
                ]
            }
        }

    def generate_commands(
        self,
        node: Node,
        vendor: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        根据节点内容和厂商生成相应命令

        Args:
            node: 节点对象
            vendor: 设备厂商
            context: 额外上下文信息，如接口名称、目标IP等

        Returns:
            命令列表
        """
        try:
            if vendor not in self.command_templates:
                self.logger.warning(f"Unsupported vendor: {vendor}")
                return []

            # 分析节点内容，确定问题类型
            problem_type = self._analyze_problem_type(node)

            # 获取基础命令模板
            template_key = self._map_problem_to_template(problem_type)
            commands = self.command_templates[vendor].get(template_key,
                                                         self.command_templates[vendor]['basic_check'])

            # 应用上下文参数
            if context:
                commands = self._apply_context(commands, context)

            return commands

        except Exception as e:
            self.logger.error(f"Command generation error: {str(e)}")
            # 返回基础检查命令作为兜底
            return self.command_templates.get(vendor, {}).get('basic_check', [])

    def _analyze_problem_type(self, node: Node) -> str:
        """分析节点内容，确定问题类型"""
        content_text = ""

        if node.content:
            if isinstance(node.content, dict):
                content_text = str(node.content.get('text', ''))
                if 'analysis' in node.content:
                    content_text += " " + str(node.content['analysis'])
                if 'answer' in node.content:
                    content_text += " " + str(node.content['answer'])
            else:
                content_text = str(node.content)

        content_text += " " + (node.title or "")
        content_lower = content_text.lower()

        # 基于关键词判断问题类型
        if any(keyword in content_lower for keyword in ['ospf', 'neighbor', 'exstart', 'lsa']):
            return 'ospf'
        elif any(keyword in content_lower for keyword in ['bgp', 'peer', 'session', 'as']):
            return 'bgp'
        elif any(keyword in content_lower for keyword in ['mtu', 'fragmentation', 'packet size']):
            return 'mtu'
        elif any(keyword in content_lower for keyword in ['interface', 'down', 'up', 'link']):
            return 'interface'
        elif any(keyword in content_lower for keyword in ['route', 'routing', 'destination', 'reachability']):
            return 'routing'
        else:
            return 'basic'

    def _map_problem_to_template(self, problem_type: str) -> str:
        """将问题类型映射到命令模板"""
        mapping = {
            'ospf': 'ospf_troubleshoot',
            'bgp': 'bgp_troubleshoot',
            'mtu': 'mtu_check',
            'interface': 'interface_check',
            'routing': 'routing_check',
            'basic': 'basic_check'
        }
        return mapping.get(problem_type, 'basic_check')

    def _apply_context(self, commands: List[str], context: Dict[str, Any]) -> List[str]:
        """应用上下文参数到命令模板"""
        processed_commands = []

        for command in commands:
            try:
                # 替换模板参数
                processed_command = command.format(**context)
                processed_commands.append(processed_command)
            except KeyError:
                # 如果缺少必要参数，保留原命令
                processed_commands.append(command)

        return processed_commands

    def get_supported_vendors(self) -> List[str]:
        """获取支持的厂商列表"""
        return list(self.command_templates.keys())

    def get_template_types(self, vendor: str) -> List[str]:
        """获取指定厂商的模板类型"""
        if vendor in self.command_templates:
            return list(self.command_templates[vendor].keys())
        return []


# 全局服务实例
vendor_command_service = VendorCommandService()
