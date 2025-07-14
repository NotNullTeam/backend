"""
IP智慧解答专家系统 - 反馈API测试

本模块测试反馈相关的API接口。
"""

import pytest
import json
from app.models.feedback import Feedback


@pytest.mark.api
@pytest.mark.feedback
class TestFeedbackSubmitAPI:
    """测试反馈提交API"""

    def test_submit_feedback_success(self, client, auth_headers, sample_case):
        """测试成功提交反馈"""
        feedback_data = {
            'outcome': 'solved',
            'rating': 5,
            'comment': '问题已完美解决，非常感谢！',
            'corrected_solution': {
                'steps': ['重启路由器', '检查配置', '更新固件']
            },
            'knowledge_contribution': {
                'new_info': '这个问题在华为设备上比较常见'
            }
        }

        response = client.post(f'/api/v1/cases/{sample_case.id}/feedback',
                             json=feedback_data,
                             headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        assert data['code'] == 200
        assert data['status'] == 'success'
        assert data['data']['outcome'] == feedback_data['outcome']
        assert data['data']['rating'] == feedback_data['rating']
        assert data['data']['comment'] == feedback_data['comment']

    def test_submit_feedback_minimal_data(self, client, auth_headers, sample_case):
        """测试提交最少必需数据的反馈"""
        feedback_data = {
            'outcome': 'unsolved'
        }

        response = client.post(f'/api/v1/cases/{sample_case.id}/feedback',
                             json=feedback_data,
                             headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        assert data['code'] == 200
        assert data['status'] == 'success'
        assert data['data']['outcome'] == 'unsolved'
        assert data['data']['rating'] is None

    def test_submit_feedback_invalid_outcome(self, client, auth_headers, sample_case):
        """测试提交无效结果的反馈"""
        feedback_data = {
            'outcome': 'invalid_outcome',
            'rating': 3
        }

        response = client.post(f'/api/v1/cases/{sample_case.id}/feedback',
                             json=feedback_data,
                             headers=auth_headers)

        assert response.status_code == 400
        data = response.get_json()

        assert data['code'] == 400
        assert data['status'] == 'error'
        assert '无效的解决结果' in data['error']['message']

    def test_submit_feedback_invalid_rating(self, client, auth_headers, sample_case):
        """测试提交无效评分的反馈"""
        feedback_data = {
            'outcome': 'solved',
            'rating': 6  # 超出1-5范围
        }

        response = client.post(f'/api/v1/cases/{sample_case.id}/feedback',
                             json=feedback_data,
                             headers=auth_headers)

        assert response.status_code == 400
        data = response.get_json()

        assert data['code'] == 400
        assert data['status'] == 'error'
        assert '评分必须是1-5之间的整数' in data['error']['message']

    def test_submit_feedback_missing_outcome(self, client, auth_headers, sample_case):
        """测试提交缺少结果的反馈"""
        feedback_data = {
            'rating': 4,
            'comment': '还不错'
        }

        response = client.post(f'/api/v1/cases/{sample_case.id}/feedback',
                             json=feedback_data,
                             headers=auth_headers)

        assert response.status_code == 400
        data = response.get_json()

        assert data['code'] == 400
        assert data['status'] == 'error'
        assert '解决结果不能为空' in data['error']['message']

    def test_submit_feedback_case_not_found(self, client, auth_headers):
        """测试为不存在的案例提交反馈"""
        fake_case_id = 'non-existent-case-id'
        feedback_data = {
            'outcome': 'solved',
            'rating': 5
        }

        response = client.post(f'/api/v1/cases/{fake_case_id}/feedback',
                             json=feedback_data,
                             headers=auth_headers)

        assert response.status_code == 404
        data = response.get_json()

        assert data['code'] == 404
        assert data['status'] == 'error'
        assert '案例不存在' in data['error']['message']

    def test_submit_feedback_duplicate(self, client, auth_headers, sample_case, database):
        """测试重复提交反馈"""
        # 先提交一次反馈
        feedback_data = {
            'outcome': 'solved',
            'rating': 4
        }

        response1 = client.post(f'/api/v1/cases/{sample_case.id}/feedback',
                              json=feedback_data,
                              headers=auth_headers)

        assert response1.status_code == 200

        # 再次提交反馈
        response2 = client.post(f'/api/v1/cases/{sample_case.id}/feedback',
                              json=feedback_data,
                              headers=auth_headers)

        assert response2.status_code == 400
        data = response2.get_json()

        assert data['code'] == 400
        assert data['status'] == 'error'
        assert '该案例已经提交过反馈' in data['error']['message']

    def test_submit_feedback_unauthorized(self, client, sample_case):
        """测试未授权提交反馈"""
        feedback_data = {
            'outcome': 'solved',
            'rating': 5
        }

        response = client.post(f'/api/v1/cases/{sample_case.id}/feedback',
                             json=feedback_data)

        assert response.status_code == 401


@pytest.mark.api
@pytest.mark.feedback
class TestFeedbackUpdateAPI:
    """测试反馈更新API"""

    def test_update_feedback_success(self, client, auth_headers, sample_case, sample_feedback):
        """测试成功更新反馈"""
        update_data = {
            'outcome': 'partially_solved',
            'rating': 3,
            'comment': '部分解决了问题',
            'corrected_solution': {
                'additional_steps': ['需要额外的配置步骤']
            }
        }

        response = client.put(f'/api/v1/cases/{sample_case.id}/feedback',
                            json=update_data,
                            headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        assert data['code'] == 200
        assert data['status'] == 'success'
        assert data['data']['outcome'] == update_data['outcome']
        assert data['data']['rating'] == update_data['rating']
        assert data['data']['comment'] == update_data['comment']

    def test_update_feedback_partial_data(self, client, auth_headers, sample_case, sample_feedback):
        """测试部分更新反馈"""
        update_data = {
            'rating': 4
        }

        response = client.put(f'/api/v1/cases/{sample_case.id}/feedback',
                            json=update_data,
                            headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        assert data['code'] == 200
        assert data['status'] == 'success'
        assert data['data']['rating'] == 4
        # 其他字段应该保持不变
        assert data['data']['outcome'] == sample_feedback.outcome

    def test_update_feedback_invalid_outcome(self, client, auth_headers, sample_case, sample_feedback):
        """测试更新为无效结果的反馈"""
        update_data = {
            'outcome': 'invalid_outcome'
        }

        response = client.put(f'/api/v1/cases/{sample_case.id}/feedback',
                            json=update_data,
                            headers=auth_headers)

        assert response.status_code == 400
        data = response.get_json()

        assert data['code'] == 400
        assert data['status'] == 'error'
        assert '无效的解决结果' in data['error']['message']

    def test_update_feedback_invalid_rating(self, client, auth_headers, sample_case, sample_feedback):
        """测试更新为无效评分的反馈"""
        update_data = {
            'rating': 0  # 低于1
        }

        response = client.put(f'/api/v1/cases/{sample_case.id}/feedback',
                            json=update_data,
                            headers=auth_headers)

        assert response.status_code == 400
        data = response.get_json()

        assert data['code'] == 400
        assert data['status'] == 'error'
        assert '评分必须是1-5之间的整数' in data['error']['message']

    def test_update_feedback_not_found(self, client, auth_headers, sample_case):
        """测试更新不存在的反馈"""
        update_data = {
            'rating': 4
        }

        response = client.put(f'/api/v1/cases/{sample_case.id}/feedback',
                            json=update_data,
                            headers=auth_headers)

        assert response.status_code == 404
        data = response.get_json()

        assert data['code'] == 404
        assert data['status'] == 'error'
        assert '反馈不存在' in data['error']['message']

    def test_update_feedback_case_not_found(self, client, auth_headers):
        """测试更新不存在案例的反馈"""
        fake_case_id = 'non-existent-case-id'
        update_data = {
            'rating': 4
        }

        response = client.put(f'/api/v1/cases/{fake_case_id}/feedback',
                            json=update_data,
                            headers=auth_headers)

        assert response.status_code == 404
        data = response.get_json()

        assert data['code'] == 404
        assert data['status'] == 'error'
        assert '案例不存在' in data['error']['message']

    def test_update_feedback_unauthorized(self, client, sample_case, sample_feedback):
        """测试未授权更新反馈"""
        update_data = {
            'rating': 4
        }

        response = client.put(f'/api/v1/cases/{sample_case.id}/feedback',
                            json=update_data)

        assert response.status_code == 401
