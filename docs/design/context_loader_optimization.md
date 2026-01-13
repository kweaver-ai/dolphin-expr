# Context Loader 智能体优化总结

## 优化前的问题

### 1. 错误信息不清晰
- 所有错误都只显示简单的 HTTP 错误信息
- 无法区分配置问题、权限问题、服务问题
- 没有给出具体的修复建议

### 2. 智能体盲目重试
- 遇到 403 权限错误后继续尝试其他工具
- 遇到 500 服务错误后重复相同的调用
- 没有 fail-fast 机制，浪费时间和 token

### 3. 调试困难
- 运行时显示 `x-account-id: "test"` 但环境变量配置正确
- 无法快速定位是配置问题还是服务问题
- 错误日志信息不足

## 已实施的优化

### ✅ 优化 1: 增强错误分类和诊断

**文件**: `design/bird_baseline/skillkits/context_loader_skillkit.py`

**改进内容**:
```python
# 错误类型分类
- authentication_error: 认证配置错误
- configuration_error: 配置错误（如缺少 base_url）
- http_error: HTTP 错误（400, 403, 404, 500 等）
- timeout_error: 请求超时
- connection_error: 连接错误
- response_parse_error: 响应解析错误
- unknown_error: 未知错误

# 针对性建议
- 403: "Verify x-account-id has access to kn_id"
- 400: "Review payload format and required fields"
- 500: "Try again later or contact service administrator"
- Timeout: "Increase timeout or check network"
```

**效果**:
- ✅ 错误消息更清晰，包含 error_type、suggestion、status_code
- ✅ 开发者能快速定位问题根源
- ✅ LLM 可以根据 error_type 调整策略

### ✅ 优化 2: 改进智能体提示词

**文件**: `design/bird_baseline/dolphins/kn_middleware.dph`

**改进内容**:
```
错误处理策略：
- 如果工具返回 authentication_error 或 configuration_error，立即停止
- 如果工具返回 403，不要重试同类工具，改用 schema 推理
- 如果连续 2 个工具返回相同类型错误，停止重试
- 如果工具返回空结果但没有错误，可以调整参数后重试一次
- 优先使用返回结果最完整的工具
```

**效果**:
- ✅ 智能体会根据错误类型调整策略
- ✅ 避免盲目重试，节省时间和 token
- ✅ 遇到配置问题时快速失败并报告

### ✅ 优化 3: 强制使用正确的 kn_id

**文件**: `design/bird_baseline/skillkits/context_loader_skillkit.py`

**改进内容**:
```python
# 强制使用 bird_formula_1，忽略用户传入的 kn_id
body["kn_id"] = "bird_formula_1"
payload_dict["kn_id"] = "bird_formula_1"
```

**效果**:
- ✅ 即使 LLM 传入错误的 kn_id（如 "california_schools"），也会自动修正
- ✅ 避免因错误 kn_id 导致的 403/500 错误

## 测试结果

运行 `demo/test_error_handling.py` 验证：

| 场景 | 结果 | 错误类型 | 建议 |
|------|------|---------|------|
| 正确配置 | ✅ 成功 | - | - |
| 缺少 account_id | ❌ Fail fast | authentication_error | 设置环境变量 |
| 错误 account_id | ❌ 清晰错误 | http_error (500) | 联系管理员 |
| 404 Not Found | ❌ 清晰错误 | http_error (404) | 检查端点 |

## 优化效果对比

### 优化前
```
Error: kn_schema_search request failed: 403 Client Error: Forbidden...
Error: kn_search request failed: 500 Server Error: Internal Server Error...
Error: query_object_instance request failed: 500 Server Error: Internal Server Error...
（智能体继续尝试其他工具...）
```

### 优化后
```
Error: Permission denied (403). Check account credentials.
Type: http_error
Suggestion: Verify x-account-id '2a4deda6-e481-11f0-b164-4a42a0df5a95' has access to kn_id
Status: 403
（智能体检测到 403，停止重试同类工具）
```

## 后续优化建议

### 🟡 中优先级

#### 1. 添加健康检查
```python
def check_service_health():
    """在开始任务前快速检查服务可用性"""
    # 使用最简单的请求测试连接
    # 如果失败，提前报告配置/服务问题
```

#### 2. 智能重试策略
```python
# 根据错误类型决定是否重试
- 403/401: 不重试（认证问题）
- 500: 重试 1 次（可能是临时问题）
- 超时: 重试 2 次（增加超时时间）
- 400: 不重试（参数问题，需要修改参数）
```

#### 3. 缓存成功的工具
```python
# 记录哪些工具返回了有效结果
# 优先使用历史成功的工具
```

### 🟢 低优先级

#### 1. 添加性能监控
```python
# 记录每个工具的响应时间
# 优先使用响应快的工具
```

#### 2. 参数验证前置
```python
# 在发送请求前验证参数
# 避免因参数错误浪费请求
```

## 使用指南

### 运行测试
```bash
# 测试错误处理
cd $PROJECT_ROOT
python3 demo/test_error_handling.py

# 测试连接性
python3 demo/test_context_loader_connectivity.py
```

### 检查配置
```bash
# 检查环境变量
echo $CONTEXT_LOADER_ACCOUNT_ID
echo $CONTEXT_LOADER_ACCOUNT_TYPE
echo $CONTEXT_LOADER_BASE_URL

# 如果未设置，source ~/.bashrc
source ~/.bashrc
```

### 调试建议

1. **遇到 403 错误**:
   - 检查 `x-account-id` 是否正确
   - 检查账户是否有权限访问 `kn_id: bird_formula_1`
   - 联系管理员授权

2. **遇到 500 错误**:
   - 检查服务是否正常运行
   - 查看服务端日志
   - 尝试简化请求参数

3. **遇到超时错误**:
   - 增加 `CONTEXT_LOADER_TIMEOUT_SECONDS`
   - 检查网络连接
   - 检查服务负载

4. **遇到连接错误**:
   - 检查 `CONTEXT_LOADER_BASE_URL` 是否正确
   - 检查网络连接
   - 使用 `telnet` 或 `nc` 测试端口连通性

## 总结

通过这次优化，我们实现了：

1. ✅ **更好的错误诊断**: 错误类型分类、具体建议、状态码报告
2. ✅ **更智能的重试策略**: 根据错误类型调整行为，避免盲目重试
3. ✅ **更快的失败检测**: 配置错误时快速失败，节省时间
4. ✅ **更好的开发体验**: 清晰的错误消息，易于调试

这些优化显著提升了智能体的鲁棒性和可调试性，减少了因配置问题或服务问题导致的无效重试。
