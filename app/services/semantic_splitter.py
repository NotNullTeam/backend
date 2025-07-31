"""
IP智慧解答专家系统 - 语义切分器

本模块基于IDP解析结果进行语义切分，将文档内容分解为有意义的块。
"""

import re
import logging
from typing import List, Dict, Any, Optional
from app.models.knowledge import KnowledgeDocument

logger = logging.getLogger(__name__)


class SemanticSplitter:
    """语义切分器"""

    def __init__(self, max_chunk_size: int = 1000, overlap: int = 100):
        """
        初始化语义切分器

        Args:
            max_chunk_size: 最大块大小
            overlap: 重叠字符数
        """
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap

    def split_document(self, idp_result: Dict[str, Any], document: KnowledgeDocument) -> List[Dict[str, Any]]:
        """
        基于IDP结果进行语义切分

        Args:
            idp_result: IDP解析结果
            document: 知识文档对象

        Returns:
            List[Dict]: 切分后的文档块列表
        """
        try:
            logger.info(f"开始对文档进行语义切分: {document.original_filename}")
            chunks = []

            # 解析新的IDP返回结构
            layouts = idp_result.get('layouts', [])
            doc_tree = idp_result.get('logics', {}).get('docTree', [])

            logger.info(f"文档布局元素数量: {len(layouts)}")

            # 按照文档层级树进行语义切分
            for i, layout in enumerate(layouts):
                try:
                    content = layout.get('text', '').strip()
                    if not content:  # 跳过空内容
                        continue

                    chunk = {
                        'content': content,
                        'title': self._extract_title(layout),
                        'type': layout.get('type', 'text'),
                        'subtype': layout.get('subType', ''),
                        'page_number': layout.get('pageNum', [0])[0] if layout.get('pageNum') else 0,
                        'unique_id': layout.get('uniqueId', f'chunk_{i}'),
                        'markdown_content': layout.get('markdownContent', ''),
                        'position': {
                            'x': layout.get('x', 0),
                            'y': layout.get('y', 0),
                            'width': layout.get('w', 0),
                            'height': layout.get('h', 0)
                        }
                    }

                    # 根据内容长度决定是否需要进一步切分
                    if len(chunk['content']) > self.max_chunk_size:
                        sub_chunks = self._split_large_content(chunk)
                        chunks.extend(sub_chunks)
                    else:
                        chunks.append(chunk)

                except Exception as e:
                    logger.warning(f"处理布局元素时出错: {str(e)}")
                    continue

            # 如果没有成功解析到布局，尝试从原始文本切分
            if not chunks and idp_result.get('markdown'):
                logger.warning("布局解析失败，尝试从Markdown内容切分")
                chunks = self._split_markdown_content(idp_result.get('markdown', ''))

            logger.info(f"文档切分完成，共生成 {len(chunks)} 个块")
            return chunks

        except Exception as e:
            logger.error(f"文档语义切分失败: {str(e)}")
            raise

    def _extract_title(self, layout: Dict[str, Any]) -> str:
        """
        从layout中提取标题

        Args:
            layout: 布局元素

        Returns:
            str: 提取的标题
        """
        layout_type = layout.get('type', '')
        layout_subtype = layout.get('subType', '')

        # 检查是否为标题类型
        if layout_type in ['title', 'para_title'] or 'title' in layout_subtype.lower():
            return layout.get('text', '').strip()

        # 检查文本是否符合标题特征
        text = layout.get('text', '').strip()
        if text and len(text) < 100:  # 标题通常较短
            # 检查是否为章节标题格式
            title_patterns = [
                r'^\d+\.\s*\S+',  # 1. 标题
                r'^第\d+章\s*\S+',  # 第1章 标题
                r'^第\d+节\s*\S+',  # 第1节 标题
                r'^[一二三四五六七八九十]+、\S+',  # 一、标题
                r'^\w+\s*:\s*\S+',  # 关键字: 内容
                r'^#+\s*\S+',  # # 标题（Markdown格式）
            ]

            for pattern in title_patterns:
                if re.match(pattern, text):
                    return text

        return ''

    def _split_large_content(self, chunk: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        切分过长的内容

        Args:
            chunk: 原始文档块

        Returns:
            List[Dict]: 切分后的子块列表
        """
        content = chunk['content']
        sub_chunks = []

        # 首先尝试按段落切分
        paragraphs = re.split(r'\n\s*\n', content)
        current_chunk = ''
        chunk_index = 0

        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            # 如果当前块加上新段落不超过限制，则继续累积
            if len(current_chunk) + len(paragraph) + 2 <= self.max_chunk_size:
                if current_chunk:
                    current_chunk += '\n\n' + paragraph
                else:
                    current_chunk = paragraph
            else:
                # 保存当前块
                if current_chunk:
                    sub_chunk = chunk.copy()
                    sub_chunk['content'] = current_chunk
                    sub_chunk['unique_id'] = f"{chunk['unique_id']}_{chunk_index}"
                    sub_chunks.append(sub_chunk)
                    chunk_index += 1

                # 开始新块
                current_chunk = paragraph

                # 如果单个段落仍然过长，按句子切分
                if len(current_chunk) > self.max_chunk_size:
                    sentence_chunks = self._split_by_sentences(current_chunk, chunk, chunk_index)
                    sub_chunks.extend(sentence_chunks)
                    chunk_index += len(sentence_chunks)
                    current_chunk = ''

        # 保存最后一个块
        if current_chunk:
            sub_chunk = chunk.copy()
            sub_chunk['content'] = current_chunk
            sub_chunk['unique_id'] = f"{chunk['unique_id']}_{chunk_index}"
            sub_chunks.append(sub_chunk)

        return sub_chunks

    def _split_by_sentences(self, content: str, base_chunk: Dict[str, Any], start_index: int) -> List[Dict[str, Any]]:
        """
        按句子切分过长的段落

        Args:
            content: 要切分的内容
            base_chunk: 基础块信息
            start_index: 起始索引

        Returns:
            List[Dict]: 切分后的句子块列表
        """
        # 按句子分割
        sentences = re.split(r'[。！？\.\!\?]\s*', content)
        chunks = []
        current_chunk = ''
        chunk_index = start_index

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # 如果当前块加上新句子不超过限制，则继续累积
            if len(current_chunk) + len(sentence) + 1 <= self.max_chunk_size:
                if current_chunk:
                    current_chunk += sentence
                else:
                    current_chunk = sentence
            else:
                # 保存当前块
                if current_chunk:
                    sub_chunk = base_chunk.copy()
                    sub_chunk['content'] = current_chunk
                    sub_chunk['unique_id'] = f"{base_chunk['unique_id']}_{chunk_index}"
                    chunks.append(sub_chunk)
                    chunk_index += 1

                # 开始新块
                current_chunk = sentence

                # 如果单个句子仍然过长，强制切分
                if len(current_chunk) > self.max_chunk_size:
                    force_chunks = self._force_split_content(current_chunk, base_chunk, chunk_index)
                    chunks.extend(force_chunks)
                    chunk_index += len(force_chunks)
                    current_chunk = ''

        # 保存最后一个块
        if current_chunk:
            sub_chunk = base_chunk.copy()
            sub_chunk['content'] = current_chunk
            sub_chunk['unique_id'] = f"{base_chunk['unique_id']}_{chunk_index}"
            chunks.append(sub_chunk)

        return chunks

    def _force_split_content(self, content: str, base_chunk: Dict[str, Any], start_index: int) -> List[Dict[str, Any]]:
        """
        强制切分过长的内容

        Args:
            content: 要切分的内容
            base_chunk: 基础块信息
            start_index: 起始索引

        Returns:
            List[Dict]: 强制切分后的块列表
        """
        chunks = []
        chunk_index = start_index

        for i in range(0, len(content), self.max_chunk_size - self.overlap):
            chunk_content = content[i:i + self.max_chunk_size]
            if chunk_content.strip():
                sub_chunk = base_chunk.copy()
                sub_chunk['content'] = chunk_content
                sub_chunk['unique_id'] = f"{base_chunk['unique_id']}_{chunk_index}"
                chunks.append(sub_chunk)
                chunk_index += 1

        return chunks

    def _split_markdown_content(self, markdown_content: str) -> List[Dict[str, Any]]:
        """
        从Markdown内容进行切分

        Args:
            markdown_content: Markdown格式的内容

        Returns:
            List[Dict]: 切分后的块列表
        """
        chunks = []
        sections = re.split(r'\n(?=#+\s)', markdown_content)

        for i, section in enumerate(sections):
            section = section.strip()
            if not section:
                continue

            # 提取标题
            title_match = re.match(r'^(#+)\s*(.+?)(?:\n|$)', section)
            title = title_match.group(2) if title_match else ''

            chunk = {
                'content': section,
                'title': title,
                'type': 'markdown_section',
                'subtype': f'level_{len(title_match.group(1))}' if title_match else 'content',
                'page_number': 0,
                'unique_id': f'markdown_chunk_{i}',
                'markdown_content': section,
                'position': {'x': 0, 'y': 0, 'width': 0, 'height': 0}
            }

            if len(chunk['content']) > self.max_chunk_size:
                sub_chunks = self._split_large_content(chunk)
                chunks.extend(sub_chunks)
            else:
                chunks.append(chunk)

        return chunks

    def extract_metadata(self, chunk: Dict[str, Any], document: KnowledgeDocument) -> Dict[str, Any]:
        """
        提取文档片段的元数据

        Args:
            chunk: 文档块
            document: 知识文档对象

        Returns:
            Dict: 元数据字典
        """
        content = chunk.get('content', '')

        return {
            'vendor': self._detect_vendor(content),
            'category': self._classify_content(content),
            'source_document': document.original_filename,
            'page_number': chunk.get('page_number', 0),
            'element_type': chunk.get('type', 'text'),
            'element_subtype': chunk.get('subtype', ''),
            'unique_id': chunk.get('unique_id', ''),
            'has_markdown': bool(chunk.get('markdown_content')),
            'has_title': bool(chunk.get('title')),
            'content_length': len(content),
            'position': chunk.get('position', {})
        }

    def _detect_vendor(self, content: str) -> str:
        """
        检测厂商信息

        Args:
            content: 文本内容

        Returns:
            str: 检测到的厂商
        """
        content_lower = content.lower()

        # 华为相关关键词
        huawei_keywords = ['华为', 'huawei', 'vrp', 'hua wei', 'hcie', 'hcip', 'hcia']
        if any(keyword in content_lower for keyword in huawei_keywords):
            return '华为'

        # 思科相关关键词
        cisco_keywords = ['思科', 'cisco', 'ios', 'nexus', 'catalyst', 'ccna', 'ccnp', 'ccie']
        if any(keyword in content_lower for keyword in cisco_keywords):
            return '思科'

        # 华三相关关键词
        h3c_keywords = ['华三', 'h3c', 'comware', 'h3cne', 'h3cse', 'h3cie']
        if any(keyword in content_lower for keyword in h3c_keywords):
            return '华三'

        # 新华三相关关键词
        new_h3c_keywords = ['新华三', 'new h3c']
        if any(keyword in content_lower for keyword in new_h3c_keywords):
            return '新华三'

        return '通用'

    def _classify_content(self, content: str) -> str:
        """
        对内容进行分类

        Args:
            content: 文本内容

        Returns:
            str: 内容分类
        """
        content_lower = content.lower()

        # 路由协议
        routing_keywords = ['ospf', 'bgp', 'rip', 'isis', 'eigrp', '路由', 'route', 'routing']
        if any(keyword in content_lower for keyword in routing_keywords):
            return '路由协议'

        # 交换技术
        switching_keywords = ['vlan', 'stp', 'trunk', 'access', '交换', 'switch', 'spanning-tree']
        if any(keyword in content_lower for keyword in switching_keywords):
            return '交换技术'

        # 安全配置
        security_keywords = ['acl', 'firewall', 'security', 'ipsec', 'vpn', '安全', '防火墙']
        if any(keyword in content_lower for keyword in security_keywords):
            return '网络安全'

        # QoS
        qos_keywords = ['qos', 'traffic', 'police', 'shape', 'priority', '服务质量']
        if any(keyword in content_lower for keyword in qos_keywords):
            return 'QoS'

        # MPLS
        mpls_keywords = ['mpls', 'label', 'lsp', 'ldp', 'rsvp-te']
        if any(keyword in content_lower for keyword in mpls_keywords):
            return 'MPLS'

        # 故障排除
        troubleshooting_keywords = ['故障', 'debug', 'troubleshoot', 'error', 'problem', '问题', '异常']
        if any(keyword in content_lower for keyword in troubleshooting_keywords):
            return '故障排除'

        # 配置相关
        config_keywords = ['配置', 'config', 'configure', 'setup', 'install']
        if any(keyword in content_lower for keyword in config_keywords):
            return '配置管理'

        return '其他'
