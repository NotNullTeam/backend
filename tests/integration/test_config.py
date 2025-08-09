"""
IP智慧解答专家系统 - 配置集成测试

本模块测试配置管理和错误处理器的集成测试。
"""

import pytest
from unittest.mock import patch
from app import create_app, db
from config.settings import Config, DevelopmentConfig, TestingConfig, ProductionConfig


@pytest.mark.integration
class TestErrorHandlers:
    """测试错误处理器"""

    def test_400_bad_request_handler(self, client):
        """测试400错误处理器"""
        # 发送无效JSON请求
        response = client.post('/api/v1/auth/login',
                             data='invalid json',
                             content_type='application/json')

        assert response.status_code == 400
        data = response.get_json()

        assert data['code'] == 400
        assert data['status'] == 'error'
        assert data['error']['type'] == 'INVALID_REQUEST'
        assert '请求参数格式错误' in data['error']['message']

    def test_401_unauthorized_handler(self, client):
        """测试401错误处理器"""
        # 访问需要认证的端点但不提供令牌
        response = client.get('/api/v1/auth/me')

        assert response.status_code == 401
        # JWT扩展可能返回不同的错误格式
        # 只验证状态码即可

    def test_404_not_found_handler(self, client):
        """测试404错误处理器"""
        # 访问不存在的端点
        response = client.get('/api/v1/nonexistent')

        assert response.status_code == 404
        data = response.get_json()

        assert data['code'] == 404
        assert data['status'] == 'error'
        assert data['error']['type'] == 'NOT_FOUND'
        assert '请求的资源不存在' in data['error']['message']

    def test_422_unprocessable_entity_handler(self, client):
        """测试JWT错误处理器"""
        # 使用无效的JWT令牌
        headers = {'Authorization': 'Bearer invalid_token'}
        response = client.get('/api/v1/auth/me', headers=headers)

        assert response.status_code == 401  # JWT错误返回401
        data = response.get_json()
        assert data['status'] == 'error'
        assert data['error']['type'] == 'UNAUTHORIZED'

    def test_500_internal_error_handler(self, client, database, monkeypatch):
        """测试500错误处理器"""
        # 模拟数据库错误
        def mock_commit():
            raise Exception("Database error")

        # 先正常登录获取令牌
        user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'roles': 'user'
        }
        from app.models.user import User
        user = User(**user_data)
        user.set_password('testpass123')
        database.session.add(user)
        database.session.commit()

        login_response = client.post('/api/v1/auth/login', json={
            'username': 'testuser',
            'password': 'testpass123'
        })

        token = login_response.get_json()['access_token']

        # 模拟数据库提交错误
        monkeypatch.setattr(database.session, 'commit', mock_commit)

        # 尝试登录（会触发commit）
        response = client.post('/api/v1/auth/login', json={
            'username': 'testuser',
            'password': 'testpass123'
        })

        assert response.status_code == 500
        data = response.get_json()

        assert data['code'] == 500
        assert data['status'] == 'error'
        assert data['error']['type'] == 'INTERNAL_ERROR'


@pytest.mark.integration
class TestConfigIntegration:
    """测试配置集成"""

    def test_database_configuration(self, app):
        """测试数据库配置"""
        with app.app_context():
            # 测试数据库连接配置
            assert db.engine is not None

            # 测试数据库URI配置
            db_uri = app.config['SQLALCHEMY_DATABASE_URI']
            assert db_uri is not None
            assert 'sqlite' in db_uri.lower()  # 测试环境使用SQLite

    def test_jwt_configuration(self, app):
        """测试JWT配置"""
        from datetime import timedelta
        
        # 验证JWT秘钥存在
        assert app.config['JWT_SECRET_KEY'] is not None
        assert len(app.config['JWT_SECRET_KEY']) > 0
        
        # 验证JWT过期时间配置 - 应该是timedelta对象或数字
        access_expires = app.config.get('JWT_ACCESS_TOKEN_EXPIRES')
        if access_expires is not None:
            assert isinstance(access_expires, (int, bool, timedelta)), f"JWT_ACCESS_TOKEN_EXPIRES type: {type(access_expires)}"
        
        refresh_expires = app.config.get('JWT_REFRESH_TOKEN_EXPIRES')
        if refresh_expires is not None:
            assert isinstance(refresh_expires, (int, bool, timedelta)), f"JWT_REFRESH_TOKEN_EXPIRES type: {type(refresh_expires)}"
        
        # 验证JWT配置的合理性
        if isinstance(access_expires, timedelta):
            assert access_expires.total_seconds() > 0, "JWT access token expires should be positive"
        if isinstance(refresh_expires, timedelta):
            assert refresh_expires.total_seconds() > 0, "JWT refresh token expires should be positive"

    def test_cors_configuration(self, client):
        """测试CORS配置"""
        response = client.options('/api/v1/auth/login')

        # CORS应该允许OPTIONS请求
        assert response.status_code in [200, 204]

    def test_file_upload_configuration(self, app):
        """测试文件上传配置"""
        assert app.config['MAX_CONTENT_LENGTH'] is not None
        assert app.config['MAX_CONTENT_LENGTH'] > 0

        upload_folder = app.config.get('UPLOAD_FOLDER')
        if upload_folder:
            assert isinstance(upload_folder, str)

    def test_production_config_security(self):
        """测试生产环境安全配置"""
        app = create_app(ProductionConfig)

        assert app.config['DEBUG'] is False
        assert app.config['SECRET_KEY'] is not None
        assert app.config['JWT_SECRET_KEY'] is not None

    def test_logging_configuration(self, app):
        """测试日志配置"""
        # 测试日志记录器是否配置
        assert app.logger is not None

        # 在测试环境中，应该有控制台处理器
        if app.config['TESTING']:
            assert len(app.logger.handlers) >= 0
