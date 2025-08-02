"""
IP智慧解答专家系统 - 阿里云文档智能服务

本模块封装阿里云文档智能API，提供文档解析能力。
使用文档解析（大模型版）API，支持更丰富的文档格式和更准确的解析结果。
"""

import os
import time
import logging
import json
from typing import Dict, Any, Optional, List
from alibabacloud_docmind_api20220711.client import Client as docmind_api20220711Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_docmind_api20220711 import models as docmind_api20220711_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_credentials.client import Client as CredClient
from flask import current_app

logger = logging.getLogger(__name__)


class IDPService:
    """阿里云文档智能服务封装类 - 使用文档解析（大模型版）API"""

    def __init__(self):
        """初始化IDP服务客户端"""
        try:
            # 使用默认凭证初始化Credentials Client
            cred = CredClient()
            config = open_api_models.Config(
                access_key_id=cred.get_credential().access_key_id,
                access_key_secret=cred.get_credential().access_key_secret
            )
            config.endpoint = 'docmind-api.cn-hangzhou.aliyuncs.com'
            self.client = docmind_api20220711Client(config)
            logger.info("IDP服务客户端初始化成功")
        except Exception as e:
            logger.error(f"IDP服务客户端初始化失败: {str(e)}")
            raise

    def parse_document(self, file_path: str, enable_llm: bool = True, enable_formula: bool = True) -> Dict[str, Any]:
        """
        调用阿里云文档解析（大模型版）API解析文档

        Args:
            file_path: 文档文件路径
            enable_llm: 是否开启大模型增强（默认开启）
            enable_formula: 是否开启公式识别增强（默认开启）

        Returns:
            Dict: 解析结果数据

        Raises:
            Exception: 解析失败时抛出异常
        """
        try:
            logger.info(f"开始解析文档: {file_path}")

            # 步骤1: 提交文档解析任务（使用大模型版）
            request = docmind_api20220711_models.SubmitDocParserJobAdvanceRequest(
                file_url_object=open(file_path, "rb"),
                file_name=os.path.basename(file_path),
                llm_enhancement=enable_llm,      # 开启大模型增强
                formula_enhancement=enable_formula  # 开启公式识别增强
            )
            runtime = util_models.RuntimeOptions()

            response = self.client.submit_doc_parser_job_advance(request, runtime)
            job_id = response.body.data.id

            logger.info(f"文档解析任务提交成功，任务ID: {job_id}")

            # 步骤2: 轮询查询任务状态
            max_attempts = 120  # 最大轮询次数（20分钟）
            attempt = 0

            while attempt < max_attempts:
                try:
                    # 查询处理状态
                    status_request = docmind_api20220711_models.QueryDocParserStatusRequest(
                        id=job_id
                    )
                    status_response = self.client.query_doc_parser_status(status_request)

                    status = status_response.body.data.status
                    logger.info(f"任务状态: {status}")

                    if status == 'success':
                        # 步骤3: 获取解析结果
                        return self._get_complete_result(job_id)
                    elif status == 'Fail':
                        error_msg = f"文档解析失败，任务ID: {job_id}"
                        logger.error(error_msg)
                        raise Exception(error_msg)

                    # 状态为 Init 或 Processing，继续等待
                    time.sleep(10)
                    attempt += 1

                    if attempt % 6 == 0:  # 每分钟记录一次进度
                        processing = getattr(status_response.body.data, 'processing', 0)
                        logger.info(f"文档解析进行中，进度: {processing}%, 已等待 {attempt * 10} 秒...")

                except Exception as e:
                    logger.warning(f"查询解析状态时出现临时错误: {str(e)}")
                    time.sleep(10)
                    attempt += 1
                    continue

            # 超时处理
            error_msg = f"文档解析超时，任务ID: {job_id}"
            logger.error(error_msg)
            raise Exception(error_msg)

        except Exception as e:
            logger.error(f"IDP服务调用失败: {str(e)}")
            raise Exception(f"IDP服务调用失败: {str(e)}")

    def _get_complete_result(self, job_id: str) -> Dict[str, Any]:
        """
        分批获取完整的解析结果

        Args:
            job_id: 任务ID

        Returns:
            Dict: 完整的解析结果
        """
        complete_result = {
            "layouts": [],
            "logics": None,
            "tables": [],
            "paragraphs": [],
            "images": []
        }

        layout_num = 0
        layout_step_size = 100  # 每次获取100个layout

        while True:
            try:
                result_request = docmind_api20220711_models.GetDocParserResultRequest(
                    id=job_id,
                    layout_num=layout_num,
                    layout_step_size=layout_step_size
                )

                result_response = self.client.get_doc_parser_result(result_request)
                batch_data = result_response.body.data

                # 解析返回的JSON数据
                if isinstance(batch_data, str):
                    batch_data = json.loads(batch_data)

                # 合并layouts数据
                if 'layouts' in batch_data and batch_data['layouts']:
                    complete_result['layouts'].extend(batch_data['layouts'])
                    layout_num += len(batch_data['layouts'])

                    # 如果返回的layouts数量小于step_size，说明已经获取完毕
                    if len(batch_data['layouts']) < layout_step_size:
                        break
                else:
                    break

                # 合并其他数据（只在第一次时设置）
                if layout_num == len(batch_data['layouts']):
                    complete_result['logics'] = batch_data.get('logics')
                    complete_result['tables'] = batch_data.get('tables', [])
                    complete_result['paragraphs'] = batch_data.get('paragraphs', [])
                    complete_result['images'] = batch_data.get('images', [])

            except Exception as e:
                logger.error(f"获取解析结果失败: {str(e)}")
                break

        logger.info(f"解析完成，共获取 {len(complete_result['layouts'])} 个layout元素")
        return complete_result

    def parse_document_from_url(self, file_url: str, file_name: str, enable_llm: bool = True, enable_formula: bool = True) -> Dict[str, Any]:
        """
        通过URL解析文档（使用大模型版）

        Args:
            file_url: 文档URL
            file_name: 文件名
            enable_llm: 是否开启大模型增强
            enable_formula: 是否开启公式识别增强

        Returns:
            Dict: 解析结果数据

        Raises:
            Exception: 解析失败时抛出异常
        """
        try:
            logger.info(f"开始解析文档URL: {file_url}")

            request = docmind_api20220711_models.SubmitDocParserJobRequest(
                file_url=file_url,
                file_name=file_name,
                llm_enhancement=enable_llm,
                formula_enhancement=enable_formula
            )

            response = self.client.submit_doc_parser_job(request)
            job_id = response.body.data.id

            logger.info(f"文档解析任务提交成功，任务ID: {job_id}")

            # 轮询查询任务状态
            max_attempts = 120
            attempt = 0

            while attempt < max_attempts:
                try:
                    status_request = docmind_api20220711_models.QueryDocParserStatusRequest(
                        id=job_id
                    )
                    status_response = self.client.query_doc_parser_status(status_request)

                    status = status_response.body.data.status

                    if status == 'success':
                        return self._get_complete_result(job_id)
                    elif status == 'Fail':
                        error_msg = f"文档解析失败，任务ID: {job_id}"
                        logger.error(error_msg)
                        raise Exception(error_msg)

                    time.sleep(10)
                    attempt += 1

                    if attempt % 6 == 0:
                        processing = getattr(status_response.body.data, 'processing', 0)
                        logger.info(f"文档解析进行中，进度: {processing}%, 已等待 {attempt * 10} 秒...")

                except Exception as e:
                    logger.warning(f"查询解析状态时出现临时错误: {str(e)}")
                    time.sleep(10)
                    attempt += 1
                    continue

            error_msg = f"文档解析超时，任务ID: {job_id}"
            logger.error(error_msg)
            raise Exception(error_msg)

        except Exception as e:
            logger.error(f"IDP服务调用失败: {str(e)}")
            raise Exception(f"IDP服务调用失败: {str(e)}")

    def get_supported_formats(self) -> List[str]:
        """
        获取支持的文档格式列表

        Returns:
            List[str]: 支持的文件格式
        """
        return [
            # 文档格式
            'pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'xlsm',
            # 图片格式
            'jpg', 'jpeg', 'png', 'bmp', 'gif',
            # 其他格式
            'markdown', 'md', 'html', 'epub', 'mobi', 'rtf', 'txt'
        ]

    def get_supported_video_formats(self) -> List[str]:
        """
        获取支持的音视频格式列表

        Returns:
            List[str]: 支持的音视频格式
        """
        return [
            # 视频格式
            'mp4', 'mkv', 'avi', 'mov', 'wmv',
            # 音频格式
            'mp3', 'wav', 'aac'
        ]

    def validate_file_format(self, file_path: str) -> bool:
        """
        验证文件格式是否受支持

        Args:
            file_path: 文件路径

        Returns:
            bool: 是否支持该格式
        """
        file_ext = os.path.splitext(file_path)[1].lower().lstrip('.')
        supported_formats = self.get_supported_formats() + self.get_supported_video_formats()
        return file_ext in supported_formats

    def extract_text_from_layouts(self, layouts: List[Dict]) -> str:
        """
        从layouts中提取纯文本内容

        Args:
            layouts: 布局数据列表

        Returns:
            str: 提取的文本内容
        """
        text_parts = []
        for layout in layouts:
            if 'text' in layout and layout['text'].strip():
                text_parts.append(layout['text'].strip())

        return '\n'.join(text_parts)

    def extract_markdown_from_layouts(self, layouts: List[Dict]) -> str:
        """
        从layouts中提取Markdown格式内容

        Args:
            layouts: 布局数据列表

        Returns:
            str: 提取的Markdown内容
        """
        markdown_parts = []
        for layout in layouts:
            # 优先使用markdownContent，如果没有则使用text
            if 'markdownContent' in layout and layout['markdownContent'].strip():
                markdown_parts.append(layout['markdownContent'].strip())
            elif 'text' in layout and layout['text'].strip():
                markdown_parts.append(layout['text'].strip())

        return '\n\n'.join(markdown_parts)

    def get_document_statistics(self, result_data: Dict[str, Any]) -> Dict[str, int]:
        """
        获取文档解析统计信息

        Args:
            result_data: 解析结果数据

        Returns:
            Dict[str, int]: 统计信息
        """
        layouts = result_data.get('layouts', [])

        stats = {
            'total_layouts': len(layouts),
            'text_count': 0,
            'title_count': 0,
            'table_count': 0,
            'image_count': 0,
            'formula_count': 0
        }

        for layout in layouts:
            layout_type = layout.get('type', '').lower()
            if layout_type in ['text', 'paragraph']:
                stats['text_count'] += 1
            elif layout_type in ['title', 'header']:
                stats['title_count'] += 1
            elif layout_type == 'table':
                stats['table_count'] += 1
            elif layout_type in ['image', 'figure']:
                stats['image_count'] += 1
            elif layout_type == 'formula':
                stats['formula_count'] += 1

        return stats
