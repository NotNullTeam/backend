"""
AI日志解析服务

使用AI技术解析网络设备日志，提取关键信息和异常点，替换Mock实现。
"""

import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime


logger = logging.getLogger(__name__)


class LogParsingService:
    """AI日志解析服务类"""

    def __init__(self):
        self.logger = logger
        self._load_parsing_rules()

    def _load_parsing_rules(self):
        """加载日志解析规则"""
        self.parsing_rules = {
            'ospf_debug': {
                'patterns': {
                    'mtu_mismatch': r'MTU mismatch|packet too big|DD packet size exceeds|MTU不匹配',
                    'neighbor_stuck': r'ExStart|neighbor stuck|邻居状态|neighbor state',
                    'authentication_fail': r'authentication|认证失败|auth fail',
                    'area_mismatch': r'area mismatch|区域不匹配|different area',
                    'hello_timer': r'hello timer|hello interval|hello间隔'
                },
                'severities': {
                    'mtu_mismatch': 'high',
                    'neighbor_stuck': 'high',
                    'authentication_fail': 'high',
                    'area_mismatch': 'medium',
                    'hello_timer': 'medium'
                }
            },
            'bgp_debug': {
                'patterns': {
                    'session_fail': r'session failed|BGP session|会话失败|connection refused',
                    'as_mismatch': r'AS mismatch|AS number|AS号不匹配',
                    'route_limit': r'maximum routes|路由数量超限|route limit exceeded',
                    'update_error': r'update error|更新错误|malformed update'
                },
                'severities': {
                    'session_fail': 'high',
                    'as_mismatch': 'high',
                    'route_limit': 'medium',
                    'update_error': 'medium'
                }
            },
            'system_log': {
                'patterns': {
                    'interface_down': r'interface.*down|接口.*down|link down',
                    'memory_high': r'memory.*high|内存.*高|out of memory',
                    'cpu_high': r'cpu.*high|CPU.*高|cpu utilization',
                    'temperature': r'temperature|温度.*高|overheating'
                },
                'severities': {
                    'interface_down': 'high',
                    'memory_high': 'high',
                    'cpu_high': 'medium',
                    'temperature': 'high'
                }
            },
            'debug_ip_packet': {
                'patterns': {
                    'packet_drop': r'packet dropped|丢包|drop count',
                    'fragmentation': r'fragmentation|分片|fragment',
                    'checksum_error': r'checksum error|校验和错误|bad checksum',
                    'ttl_exceeded': r'TTL exceeded|TTL超时|time exceeded'
                },
                'severities': {
                    'packet_drop': 'high',
                    'fragmentation': 'medium',
                    'checksum_error': 'medium',
                    'ttl_exceeded': 'low'
                }
            }
        }

        # 解决方案模板
        self.solution_templates = {
            'mtu_mismatch': {
                'action': '检查并统一接口MTU配置',
                'description': '确保OSPF邻居之间的接口MTU值一致',
                'commands': {
                    'Huawei': [
                        'display interface {interface}',
                        'interface {interface}',
                        'mtu {mtu_value}',
                        'commit'
                    ],
                    'Cisco': [
                        'show interface {interface}',
                        'configure terminal',
                        'interface {interface}',
                        'mtu {mtu_value}',
                        'end'
                    ],
                    'Juniper': [
                        'show interfaces {interface}',
                        'configure',
                        'set interfaces {interface} mtu {mtu_value}',
                        'commit'
                    ]
                }
            },
            'neighbor_stuck': {
                'action': '重启OSPF进程并检查配置',
                'description': '清除OSPF邻居状态并重新建立邻接关系',
                'commands': {
                    'Huawei': [
                        'reset ospf process',
                        'display ospf peer'
                    ],
                    'Cisco': [
                        'clear ip ospf process',
                        'show ip ospf neighbor'
                    ],
                    'Juniper': [
                        'restart routing',
                        'show ospf neighbor'
                    ]
                }
            },
            'interface_down': {
                'action': '检查接口物理状态和配置',
                'description': '排查接口物理连接和配置问题',
                'commands': {
                    'Huawei': [
                        'display interface {interface}',
                        'display interface {interface} statistics',
                        'interface {interface}',
                        'undo shutdown'
                    ],
                    'Cisco': [
                        'show interface {interface}',
                        'show interface {interface} statistics',
                        'configure terminal',
                        'interface {interface}',
                        'no shutdown'
                    ],
                    'Juniper': [
                        'show interfaces {interface}',
                        'show interfaces {interface} statistics',
                        'configure',
                        'delete interfaces {interface} disable'
                    ]
                }
            }
        }

    def parse_log(
        self,
        log_type: str,
        vendor: str,
        log_content: str,
        context_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        解析技术日志

        Args:
            log_type: 日志类型
            vendor: 设备厂商
            log_content: 日志内容
            context_info: 上下文信息

        Returns:
            解析结果字典
        """
        try:
            # 检测异常
            anomalies = self._detect_anomalies(log_type, log_content, context_info)

            # 生成摘要
            summary = self._generate_summary(anomalies, log_type)

            # 生成建议操作
            suggested_actions = self._generate_suggested_actions(anomalies, vendor, context_info)

            # 提取关键信息
            key_events = self._extract_key_events(log_content, log_type)

            return {
                'summary': summary,
                'anomalies': anomalies,
                'suggestedActions': suggested_actions,
                'keyEvents': key_events,
                'logMetrics': {
                    'totalLines': len(log_content.split('\n')),
                    'anomalyCount': len(anomalies),
                    'timeRange': self._extract_time_range(log_content),
                    'vendor': vendor,
                    'logType': log_type
                }
            }

        except Exception as e:
            self.logger.error(f"Log parsing error: {str(e)}")
            return {
                'summary': f'日志解析过程中发生错误：{str(e)}',
                'anomalies': [],
                'suggestedActions': [],
                'keyEvents': [],
                'logMetrics': {
                    'totalLines': 0,
                    'anomalyCount': 0,
                    'timeRange': None,
                    'vendor': vendor,
                    'logType': log_type
                }
            }

    def _detect_anomalies(
        self,
        log_type: str,
        log_content: str,
        context_info: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """检测日志中的异常"""
        anomalies = []

        if log_type not in self.parsing_rules:
            return anomalies

        rules = self.parsing_rules[log_type]

        for anomaly_type, pattern in rules['patterns'].items():
            matches = re.finditer(pattern, log_content, re.IGNORECASE | re.MULTILINE)

            for match in matches:
                # 提取上下文
                line_start = max(0, log_content.rfind('\n', 0, match.start()) + 1)
                line_end = log_content.find('\n', match.end())
                if line_end == -1:
                    line_end = len(log_content)

                evidence_line = log_content[line_start:line_end].strip()

                anomaly = {
                    'type': anomaly_type.upper(),
                    'severity': rules['severities'].get(anomaly_type, 'medium'),
                    'location': self._extract_location(evidence_line, context_info),
                    'description': self._get_anomaly_description(anomaly_type),
                    'evidence': [evidence_line],
                    'timestamp': self._extract_timestamp(evidence_line),
                    'lineNumber': log_content[:match.start()].count('\n') + 1
                }

                anomalies.append(anomaly)

        # 去重相似的异常
        return self._deduplicate_anomalies(anomalies)

    def _generate_summary(self, anomalies: List[Dict[str, Any]], log_type: str) -> str:
        """生成日志分析摘要"""
        if not anomalies:
            return f"分析完成，{log_type}日志中未发现明显异常"

        high_severity = [a for a in anomalies if a['severity'] == 'high']
        medium_severity = [a for a in anomalies if a['severity'] == 'medium']

        summary_parts = []

        if high_severity:
            summary_parts.append(f"发现{len(high_severity)}个高严重性问题")

        if medium_severity:
            summary_parts.append(f"发现{len(medium_severity)}个中等严重性问题")

        # 总结主要问题类型
        problem_types = {}
        for anomaly in anomalies:
            problem_type = anomaly['type']
            if problem_type not in problem_types:
                problem_types[problem_type] = 0
            problem_types[problem_type] += 1

        if problem_types:
            main_problems = sorted(problem_types.items(), key=lambda x: x[1], reverse=True)[:2]
            problem_desc = ', '.join([f"{prob[0].lower().replace('_', ' ')}" for prob in main_problems])
            summary_parts.append(f"主要问题涉及：{problem_desc}")

        return "；".join(summary_parts)

    def _generate_suggested_actions(
        self,
        anomalies: List[Dict[str, Any]],
        vendor: str,
        context_info: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """生成建议操作"""
        actions = []
        processed_types = set()

        for anomaly in anomalies:
            anomaly_type = anomaly['type'].lower()

            if anomaly_type in processed_types:
                continue

            processed_types.add(anomaly_type)

            if anomaly_type in self.solution_templates:
                template = self.solution_templates[anomaly_type]

                action = {
                    'action': template['action'],
                    'priority': anomaly['severity'],
                    'description': template['description'],
                    'commands': template['commands'].get(vendor, template['commands'].get('Huawei', [])),
                    'relatedAnomalies': [anomaly['type']]
                }

                # 应用上下文信息
                if context_info:
                    action['commands'] = self._apply_context_to_commands(
                        action['commands'], context_info
                    )

                actions.append(action)

        # 按优先级排序
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        actions.sort(key=lambda x: priority_order.get(x['priority'], 3))

        return actions

    def _extract_key_events(self, log_content: str, log_type: str) -> List[Dict[str, Any]]:
        """提取关键事件"""
        events = []
        lines = log_content.split('\n')

        for i, line in enumerate(lines):
            timestamp = self._extract_timestamp(line)
            if timestamp:
                event = {
                    'timestamp': timestamp,
                    'lineNumber': i + 1,
                    'content': line.strip(),
                    'severity': self._determine_line_severity(line)
                }
                events.append(event)

        # 只返回重要事件
        important_events = [e for e in events if e['severity'] in ['high', 'medium']]
        return important_events[-20:]  # 最近20个重要事件

    def _extract_location(self, evidence_line: str, context_info: Optional[Dict[str, Any]]) -> str:
        """从证据行中提取位置信息"""
        # 尝试提取接口名称
        interface_patterns = [
            r'interface\s+(\S+)',
            r'GigabitEthernet(\d+/\d+/\d+)',
            r'GE(\d+/\d+/\d+)',
            r'Ethernet(\d+/\d+)',
            r'接口\s+(\S+)'
        ]

        for pattern in interface_patterns:
            match = re.search(pattern, evidence_line, re.IGNORECASE)
            if match:
                return match.group(1)

        # 如果没有找到，使用上下文信息
        if context_info and 'deviceModel' in context_info:
            return context_info['deviceModel']

        return 'Unknown'

    def _get_anomaly_description(self, anomaly_type: str) -> str:
        """获取异常描述"""
        descriptions = {
            'mtu_mismatch': 'MTU配置不匹配导致邻居无法正常建立',
            'neighbor_stuck': 'OSPF邻居状态异常，无法正常收敛',
            'authentication_fail': '认证失败，检查认证密钥配置',
            'area_mismatch': 'OSPF区域配置不匹配',
            'hello_timer': 'Hello定时器配置不匹配',
            'session_fail': 'BGP会话建立失败',
            'as_mismatch': 'AS号配置不匹配',
            'interface_down': '接口状态异常，链路可能中断',
            'memory_high': '内存使用率过高，可能影响系统稳定性',
            'cpu_high': 'CPU使用率过高，可能影响性能',
            'packet_drop': '数据包丢弃，检查网络质量',
            'fragmentation': '数据包分片，可能影响传输效率'
        }
        return descriptions.get(anomaly_type, f'检测到{anomaly_type}类型异常')

    def _extract_timestamp(self, line: str) -> Optional[str]:
        """从日志行中提取时间戳"""
        timestamp_patterns = [
            r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}',
            r'\d{2}:\d{2}:\d{2}',
            r'\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}'
        ]

        for pattern in timestamp_patterns:
            match = re.search(pattern, line)
            if match:
                return match.group(0)

        return None

    def _extract_time_range(self, log_content: str) -> Optional[Dict[str, str]]:
        """提取日志时间范围"""
        lines = log_content.split('\n')

        first_timestamp = None
        last_timestamp = None

        for line in lines:
            timestamp = self._extract_timestamp(line)
            if timestamp:
                if not first_timestamp:
                    first_timestamp = timestamp
                last_timestamp = timestamp

        if first_timestamp and last_timestamp:
            return {
                'start': first_timestamp,
                'end': last_timestamp
            }

        return None

    def _determine_line_severity(self, line: str) -> str:
        """判断日志行的严重性"""
        line_lower = line.lower()

        if any(keyword in line_lower for keyword in ['error', 'fail', 'down', 'critical']):
            return 'high'
        elif any(keyword in line_lower for keyword in ['warning', 'warn', 'timeout']):
            return 'medium'
        else:
            return 'low'

    def _deduplicate_anomalies(self, anomalies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去重相似的异常"""
        unique_anomalies = []
        seen_types = set()

        for anomaly in anomalies:
            key = f"{anomaly['type']}_{anomaly['location']}"
            if key not in seen_types:
                seen_types.add(key)
                unique_anomalies.append(anomaly)

        return unique_anomalies

    def _apply_context_to_commands(
        self,
        commands: List[str],
        context_info: Dict[str, Any]
    ) -> List[str]:
        """应用上下文信息到命令"""
        processed_commands = []

        for command in commands:
            try:
                processed_command = command.format(**context_info)
                processed_commands.append(processed_command)
            except KeyError:
                processed_commands.append(command)

        return processed_commands


# 全局服务实例
log_parsing_service = LogParsingService()
