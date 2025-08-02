#!/usr/bin/env python3
"""
模拟 Weaviate HTTP 服务器用于开发测试
"""
from flask import Flask, jsonify, request
import uuid
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# 内存存储
data_store = {}
schema = {"classes": []}

@app.route('/v1/.well-known/ready', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"})

@app.route('/v1/meta', methods=['GET'])
def get_meta():
    return jsonify({
        "version": "1.21.2",
        "hostname": "localhost",
        "modules": {}
    })

@app.route('/v1/schema', methods=['GET'])
def get_schema():
    return jsonify(schema)

@app.route('/v1/schema', methods=['POST'])
def create_class():
    class_data = request.json
    schema["classes"].append(class_data)
    app.logger.info(f"Created class: {class_data.get('class')}")
    return jsonify(class_data)

@app.route('/v1/objects', methods=['POST'])
def create_object():
    obj_data = request.json
    obj_id = str(uuid.uuid4())
    class_name = obj_data.get('class')

    if class_name not in data_store:
        data_store[class_name] = {}

    data_store[class_name][obj_id] = obj_data
    app.logger.info(f"Created object in class {class_name}")

    return jsonify({"id": obj_id})

@app.route('/v1/batch/objects', methods=['POST'])
def batch_objects():
    objects = request.json.get('objects', [])
    results = []

    for obj in objects:
        obj_id = str(uuid.uuid4())
        class_name = obj.get('class')

        if class_name not in data_store:
            data_store[class_name] = {}

        data_store[class_name][obj_id] = obj
        results.append({"id": obj_id, "result": {"status": "SUCCESS"}})

    app.logger.info(f"Batch created {len(objects)} objects")
    return jsonify(results)

@app.route('/v1/graphql', methods=['POST'])
def graphql_query():
    # 简单的 GraphQL 模拟
    query_data = request.json
    app.logger.info(f"GraphQL query: {query_data}")

    # 返回模拟搜索结果
    return jsonify({
        "data": {
            "Get": {
                "Document": [
                    {
                        "content": "网络设备配置管理是网络运维的重要环节",
                        "title": "测试文档 1",
                        "source": "mock_data",
                        "doc_type": "test",
                        "chunk_index": 0,
                        "_additional": {"score": 0.95, "distance": 0.05}
                    },
                    {
                        "content": "OSPF协议是一种链路状态路由协议",
                        "title": "测试文档 2",
                        "source": "mock_data",
                        "doc_type": "test",
                        "chunk_index": 1,
                        "_additional": {"score": 0.88, "distance": 0.12}
                    }
                ]
            },
            "Aggregate": {
                "Document": [
                    {
                        "meta": {
                            "count": len(data_store.get("Document", {}))
                        }
                    }
                ]
            }
        }
    })

if __name__ == '__main__':
    print("🚀 启动模拟 Weaviate 服务器...")
    print("📍 访问地址: http://localhost:8080")
    print("⚠️  这只是用于开发测试的模拟服务器")
    app.run(host='0.0.0.0', port=8080, debug=True)
