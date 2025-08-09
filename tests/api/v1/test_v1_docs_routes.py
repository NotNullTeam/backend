"""
API 文档路由测试

覆盖 Swagger UI 页面与 OpenAPI 规范端点，防止回归导致 404。
"""


class TestDocsRoutes:
	def test_docs_ui_page_available(self, client):
		"""GET /api/v1/docs/ 应返回自定义的 Swagger UI HTML 页面"""
		response = client.get('/api/v1/docs/')
		assert response.status_code == 200
		assert 'text/html' in response.content_type
		# 模板包含 swagger-ui 容器 ID
		assert b'id="swagger-ui"' in response.data

	def test_swagger_json_available(self, client):
		"""GET /api/v1/docs/swagger.json 应返回 OpenAPI/Swagger 规范 JSON"""
		response = client.get('/api/v1/docs/swagger.json')
		assert response.status_code == 200
		assert 'application/json' in response.content_type

		data = response.get_json()
		assert isinstance(data, dict)
		# 兼容 OpenAPI 3 (openapi) 或 Swagger 2 (swagger) 规范键
		assert ('openapi' in data) or ('swagger' in data)
		# 至少应包含路径定义
		assert 'paths' in data


