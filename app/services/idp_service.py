"""
IP智慧解答专家系统 - 阿里云文档智能服务

本模块封装阿里云文档智能API，提供文档解析能力。
"""

import os
import time
import logging
from typing import Dict, Any, Optional
from alibabacloud_docmind_api20220711.client import Client as docmind_api20220711Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_docmind_api20220711 import models as docmind_api20220711_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_credentials.client import Client as CredClient
from flask import current_app

logger = logging.getLogger(__name__)


class IDPService:
    """阿里云文档智能服务封装类"""

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

    def parse_document(self, file_path: str) -> Dict[str, Any]:
        """
        调用阿里云文档智能API解析文档

        Args:
            file_path: 文档文件路径

        Returns:
            Dict: 解析结果数据

        Raises:
            Exception: 解析失败时抛出异常
        """
        try:
            logger.info(f"开始解析文档: {file_path}")

            # 步骤1: 提交文档解析任务
            request = docmind_api20220711_models.SubmitDocStructureJobAdvanceRequest(
                file_url_object=open(file_path, "rb"),
                file_name=os.path.basename(file_path),
                structure_type='default',  # 返回完整结构化信息
                formula_enhancement=True   # 开启公式识别增强
            )
            runtime = util_models.RuntimeOptions()

            response = self.client.submit_doc_structure_job_advance(request, runtime)
            job_id = response.body.data.id

            logger.info(f"文档解析任务提交成功，任务ID: {job_id}")

            # 步骤2: 轮询获取结果
            max_attempts = 120  # 最大轮询次数（20分钟）
            attempt = 0

            while attempt < max_attempts:
                try:
                    query_request = docmind_api20220711_models.GetDocStructureResultRequest(
                        id=job_id,
                        reveal_markdown=True  # 输出Markdown格式
                    )

                    query_response = self.client.get_doc_structure_result(query_request)

                    if query_response.body.completed:
                        if query_response.body.status == 'Success':
                            logger.info(f"文档解析完成: {file_path}")
                            return query_response.body.data
                        else:
                            error_msg = f"文档解析失败: {query_response.body.message}"
                            logger.error(error_msg)
                            raise Exception(error_msg)

                    # 等待10秒后重试
                    time.sleep(10)
                    attempt += 1

                    if attempt % 6 == 0:  # 每分钟记录一次进度
                        logger.info(f"文档解析进行中，已等待 {attempt * 10} 秒...")

                except Exception as e:
                    if "completed" in str(e).lower():
                        # 可能是网络临时问题，继续重试
                        logger.warning(f"查询解析状态时出现临时错误: {str(e)}")
                        time.sleep(10)
                        attempt += 1
                        continue
                    else:
                        raise

            # 超时处理
            error_msg = f"文档解析超时，任务ID: {job_id}"
            logger.error(error_msg)
            raise Exception(error_msg)

        except Exception as e:
            logger.error(f"IDP服务调用失败: {str(e)}")
            raise Exception(f"IDP服务调用失败: {str(e)}")

    def parse_document_from_url(self, file_url: str, file_name: str) -> Dict[str, Any]:
        """
        通过URL解析文档

        Args:
            file_url: 文档URL
            file_name: 文件名

        Returns:
            Dict: 解析结果数据

        Raises:
            Exception: 解析失败时抛出异常
        """
        try:
            logger.info(f"开始解析文档URL: {file_url}")

            request = docmind_api20220711_models.SubmitDocStructureJobRequest(
                file_url=file_url,
                file_name=file_name,
                structure_type='default',
                formula_enhancement=True
            )

            response = self.client.submit_doc_structure_job(request)
            job_id = response.body.data.id

            logger.info(f"文档解析任务提交成功，任务ID: {job_id}")

            # 轮询获取结果
            max_attempts = 120
            attempt = 0

            while attempt < max_attempts:
                try:
                    query_request = docmind_api20220711_models.GetDocStructureResultRequest(
                        id=job_id,
                        reveal_markdown=True
                    )

                    query_response = self.client.get_doc_structure_result(query_request)

                    if query_response.body.completed:
                        if query_response.body.status == 'Success':
                            logger.info(f"文档解析完成: {file_url}")
                            return query_response.body.data
                        else:
                            error_msg = f"文档解析失败: {query_response.body.message}"
                            logger.error(error_msg)
                            raise Exception(error_msg)

                    time.sleep(10)
                    attempt += 1

                    if attempt % 6 == 0:
                        logger.info(f"文档解析进行中，已等待 {attempt * 10} 秒...")

                except Exception as e:
                    if "completed" in str(e).lower():
                        logger.warning(f"查询解析状态时出现临时错误: {str(e)}")
                        time.sleep(10)
                        attempt += 1
                        continue
                    else:
                        raise

            error_msg = f"文档解析超时，任务ID: {job_id}"
            logger.error(error_msg)
            raise Exception(error_msg)

        except Exception as e:
            logger.error(f"IDP服务调用失败: {str(e)}")
            raise Exception(f"IDP服务调用失败: {str(e)}")

    def get_supported_formats(self) -> list:
        """
        获取支持的文档格式列表

        Returns:
            list: 支持的文件格式
        """
        return [
            'pdf', 'doc', 'docx', 'ppt', 'pptx',
            'xls', 'xlsx', 'txt', 'rtf', 'odt',
            'jpg', 'jpeg', 'png', 'bmp', 'tiff'
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
        return file_ext in self.get_supported_formats()
