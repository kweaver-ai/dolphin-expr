import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests

from dolphin.core.skill.skill_function import SkillFunction
from dolphin.core.skill.skillkit import Skillkit


_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*([\s\S]*?)\s*```$", re.IGNORECASE)


def _extract_json_text(maybe_fenced: str) -> str:
    if maybe_fenced is None:
        return ""
    text = str(maybe_fenced).strip()
    m = _JSON_FENCE_RE.match(text)
    if m:
        return m.group(1).strip()
    return text


def _json_loads_loose(maybe_json: str) -> Any:
    text = _extract_json_text(maybe_json)
    if not text:
        return {}
    return json.loads(text)


def _normalize_condition(condition: Any) -> Any:
    """Normalize condition format for object_query API.
    
    Supports two formats:
    1. Standard API format (pass through):
       {"operation": "==", "field": "name", "value": "test", "value_from": "const"}
       {"operation": "and", "sub_conditions": [...]}
    
    2. Simplified format (auto-convert):
       {"field_name": value}  ->  {"operation": "==", "field": "field_name", "value": value, "value_from": "const"}
       {"field1": v1, "field2": v2}  ->  {"operation": "and", "sub_conditions": [...]}
    
    For simplified format:
    - Single value: uses "==" operator
    - List value: uses "in" operator
    """
    if not isinstance(condition, dict):
        return condition
    
    # Already in standard format: has "operation" key
    if "operation" in condition:
        return condition
    
    # Simplified format: convert {"field": value, ...} to API format
    sub_conditions = []
    for field, value in condition.items():
        # Skip None values
        if value is None:
            continue
        
        # Infer operator based on value type
        if isinstance(value, list):
            op = "in"
        else:
            op = "=="
        
        sub_conditions.append({
            "field": field,
            "operation": op,
            "value": value,
            "value_from": "const"
        })
    
    # No valid conditions
    if not sub_conditions:
        return None
    
    # Single condition: return directly without wrapping
    if len(sub_conditions) == 1:
        return sub_conditions[0]
    
    # Multiple conditions: wrap with "and"
    return {
        "operation": "and",
        "sub_conditions": sub_conditions
    }


@dataclass(frozen=True)
class _ToolEndpoint:
    path: str
    service_type: str = "default"  # "action_info" or "default"

    def resolve_url(self, base_url: str) -> str:
        """Resolve full URL from base URL and path.
        
        Args:
            base_url: Base URL (must be provided, no default)
        
        Returns:
            Full URL string
        """
        base = base_url.rstrip("/")
        path = (self.path or "").lstrip("/")
        # If base_url already contains the API path prefix, only append the endpoint name
        if base.endswith("/api/agent-retrieval/in/v1/kn"):
            # Extract endpoint name from path (e.g., "kn_search" from "/api/agent-retrieval/in/v1/kn/kn_search")
            endpoint_name = path.split("/")[-1] if "/" in path else path
            return f"{base}/{endpoint_name}"
        return f"{base}/{path}"


class ContextLoaderSkillkit(Skillkit):
    def getName(self) -> str:
        return "context_loader_skillkit"

    def getDesc(self) -> str:
        return "Context Loader / KN middleware tools (HTTP)."

    def _get_timeout_seconds(self, timeout_seconds: Optional[int]) -> int:
        if timeout_seconds is not None and timeout_seconds > 0:
            return int(timeout_seconds)
        env = os.environ.get("CONTEXT_LOADER_TIMEOUT_SECONDS", "").strip()
        if env.isdigit() and int(env) > 0:
            return int(env)
        return 30

    def _get_base_url(self, base_url: Optional[str], service_type: str = "default") -> str:
        """Get base URL from parameter, environment variable, or fail if not configured.
        
        Args:
            base_url: Explicit base URL parameter
            service_type: Service type - "action_info" (port 8000) or "default" (port 30779)
        
        Returns:
            Base URL string
            
        Raises:
            ValueError: If base URL is not configured
        """
        if base_url:
            return base_url.rstrip("/")
        
        # Try service-specific environment variable first
        if service_type == "action_info":
            env_url = os.environ.get("CONTEXT_LOADER_ACTION_INFO_BASE_URL", "").strip()
            if env_url:
                return env_url.rstrip("/")
        
        # Fall back to general base URL
        env_url = os.environ.get("CONTEXT_LOADER_BASE_URL", "").strip()
        if env_url:
            return env_url.rstrip("/")
        
        # Fail fast if not configured
        service_hint = f" (use CONTEXT_LOADER_ACTION_INFO_BASE_URL for {service_type})" if service_type == "action_info" else ""
        raise ValueError(
            f"Context loader base URL not configured. "
            f"Please set CONTEXT_LOADER_BASE_URL environment variable{service_hint}."
        )

    def _get_headers(
        self,
        x_account_id: Optional[str],
        x_account_type: Optional[str],
    ) -> Dict[str, str]:
        # Get account ID: parameter > environment variable > fail fast.
        # Do not use placeholder values like "test".
        account_id = (x_account_id or "").strip()
        if not account_id:
            account_id = os.environ.get("CONTEXT_LOADER_ACCOUNT_ID", "").strip()
        if not account_id or account_id.lower() == "test":
            raise ValueError(
                "x-account-id is required. Please set CONTEXT_LOADER_ACCOUNT_ID (not 'test') "
                "or pass x_account_id parameter."
            )
        
        # Get account type: parameter > environment variable > default "user"
        account_type = x_account_type
        if not account_type:
            account_type = os.environ.get("CONTEXT_LOADER_ACCOUNT_TYPE", "").strip()
        if not account_type:
            account_type = "user"  # Default to "user" if not specified
        
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        headers["x-account-id"] = account_id
        headers["x-account-type"] = account_type
        return headers

    def _post_json(
        self,
        *,
        endpoint: _ToolEndpoint,
        body: Dict[str, Any],
        base_url: Optional[str],
        x_account_id: Optional[str],
        x_account_type: Optional[str],
        timeout_seconds: Optional[int],
        query_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            resolved_base_url = self._get_base_url(base_url, endpoint.service_type)
        except ValueError as e:
            return {"error": str(e), "error_type": "configuration_error"}
        try:
            headers = self._get_headers(x_account_id, x_account_type)
        except ValueError as e:
            return {"error": str(e), "error_type": "authentication_error"}
        url = endpoint.resolve_url(resolved_base_url)
        timeout = self._get_timeout_seconds(timeout_seconds)
        
        try:
            resp = requests.post(url, json=body, headers=headers, timeout=timeout, params=query_params)
            resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            error_detail = {"error_type": "http_error", "status_code": e.response.status_code}
            # Always keep the raw response text for debugging (full details)
            raw_response_text = e.response.text
            try:
                parsed_response = e.response.json()
                error_detail["response"] = parsed_response
                # Always include raw response text to ensure full details are available
                # This helps when the JSON's "details" field is truncated by upstream service
                error_detail["raw_response_text"] = raw_response_text
            except Exception:
                # Keep full response text without truncation
                error_detail["response"] = raw_response_text
            
            if e.response.status_code == 403:
                error_detail["error"] = f"Permission denied (403). Check account credentials."
                error_detail["suggestion"] = f"Verify x-account-id '{headers.get('x-account-id')}' has access to kn_id"
            elif e.response.status_code == 400:
                error_detail["error"] = f"Bad request (400). Check request parameters."
                error_detail["suggestion"] = "Review payload format and required fields"
            elif e.response.status_code == 404:
                error_detail["error"] = f"Not found (404). Endpoint or resource does not exist."
            elif e.response.status_code == 500:
                error_detail["error"] = f"Server error (500). Service may be unavailable."
                error_detail["suggestion"] = "Try again later or contact service administrator"
            else:
                error_detail["error"] = f"HTTP {e.response.status_code}: {str(e)}"
            return error_detail
        except requests.exceptions.Timeout:
            return {"error": "Request timeout", "error_type": "timeout_error", "suggestion": "Increase timeout or check network"}
        except requests.exceptions.ConnectionError as e:
            # Keep full connection error message without truncation
            return {"error": f"Connection error: {str(e)}", "error_type": "connection_error", "suggestion": "Check network connectivity and service availability"}
        except Exception as e:
            # Keep full error message without truncation
            return {"error": f"Unexpected error: {str(e)}", "error_type": "unknown_error"}
        
        try:
            data = resp.json()
        except Exception:
            # Keep full response text without truncation
            data = {"error": "Non-JSON response", "text": resp.text, "error_type": "response_parse_error"}
        if isinstance(data, dict):
            data.setdefault("provider", "context_loader")
            data.setdefault("headers", headers)
        return data

    def get_action_info(
        self,
        kn_id: str,
        at_id: str,
        unique_identity: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """Recall action info and return _dynamic_tools for Dolphin to load dynamically.

        Args:
            kn_id (str): Knowledge network ID, e.g. "bird_formula_1"
            at_id (str): Action template ID configured in the middleware
            unique_identity (str): JSON string of a single object identity; will be parsed as dict
            **kwargs: Other parameters (ignored for backward compatibility)

        Note:
            Configuration (base_url, account_id, account_type, timeout) is automatically loaded
            from environment variables set by the experiment runner. LLM does not need to provide these.

        Returns:
            Dict[str, Any]: {"answer": <json_response>}
        """
        endpoint = _ToolEndpoint(
            path="/api/agent-retrieval/in/v1/kn/get_action_info",
            service_type="action_info",
        )
        try:
            unique_identity_obj = _json_loads_loose(unique_identity)
        except Exception as e:
            return {"answer": {"error": f"Invalid unique_identity JSON: {e}"}}

        body = {"kn_id": kn_id, "at_id": at_id, "unique_identity": unique_identity_obj}
        try:
            data = self._post_json(
                endpoint=endpoint,
                body=body,
                base_url=None,  # Auto-loaded from env
                x_account_id=None,  # Auto-loaded from env
                x_account_type=None,  # Auto-loaded from env
                timeout_seconds=None,  # Auto-loaded from env
            )
            return {"answer": data}
        except Exception as e:
            return {"answer": {"error": f"get_action_info request failed: {e}"}}

    def object_search(
        self,
        payload: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """基于知识网络的语义实例搜索工具。

        **功能说明**：
        - 支持传入自然语言问题或关键词，返回相关的概念定义（对象类、关系类）及匹配的实例数据
        - 适合做粗召回，不适合做精确查询

        **使用场景**：
        - 初次探索：不清楚有哪些相关概念时，用 query 描述需求
        - 实例召回：按名称搜索特定实体（如 "race 20", "Hamilton"）

        Args:
            payload (str): JSON 请求体字符串，包含:
                - query (str, 必填): 搜索的问题或关键词
                - kn_id (str, 可选): 知识网络ID，可从环境变量自动填充

        Returns:
            Dict[str, Any]: {"answer": {"object_types": [...], "nodes": [...], ...}}
        """
        endpoint = _ToolEndpoint(
            path="/api/agent-retrieval/in/v1/kn/kn_search",
            service_type="default",
        )
        try:
            body = _json_loads_loose(payload)
            if not isinstance(body, dict):
                return {"answer": {"error": "Payload must be a JSON object"}}
        except Exception as e:
            return {"answer": {"error": f"Invalid payload JSON: {e}"}}

        # Fill kn_id from env if missing.
        if "kn_id" not in body or not str(body.get("kn_id") or "").strip():
            env_kn_id = os.environ.get("CONTEXT_LOADER_KN_ID", "").strip()
            if not env_kn_id:
                return {"answer": {"error": "kn_id is required in payload or set CONTEXT_LOADER_KN_ID"}}
            body["kn_id"] = env_kn_id

        # Validate required fields
        if "query" not in body:
            return {"answer": {"error": "query is required in payload"}}

        try:
            data = self._post_json(
                endpoint=endpoint,
                body=body,
                base_url=None,  # Auto-loaded from env
                x_account_id=None,  # Auto-loaded from env
                x_account_type=None,  # Auto-loaded from env
                timeout_seconds=None,  # Auto-loaded from env
            )
            return {"answer": data}
        except Exception as e:
            return {"answer": {"error": f"object_search request failed: {e}"}}

    def concept_search(
        self,
        payload: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """业务知识网络的概念/Schema 语义检索工具。

        **功能说明**：
        - 专注于检索业务知识网络的 Schema 定义信息
        - 返回对象类定义（属性、主键、支持的操作符）
        - 返回关系类定义（源对象类、目标对象类）
        - 提供查询意图理解和相关性评分

        **使用场景**：
        - 了解数据模型：需要知道有哪些对象类、每个类有哪些属性
        - 查询规划：确定使用哪个 ot_id（concept_id）进行 object_query
        - 语义理解：获取属性的 display_name 和 comment 区分字段含义

        Args:
            payload (str): JSON 请求体字符串，包含:
                - query (str, 必填): 搜索的问题或关键词
                - kn_id (str, 可选): 知识网络ID，可从环境变量自动填充

        Returns:
            Dict[str, Any]: {"answer": {"concepts": [...], "query_understanding": {...}}}
        """
        endpoint = _ToolEndpoint(
            path="/api/agent-retrieval/in/v1/kn/semantic-search",
            service_type="default",
        )
        try:
            body = _json_loads_loose(payload)
            if not isinstance(body, dict):
                return {"answer": {"error": "Payload must be a JSON object"}}
        except Exception as e:
            return {"answer": {"error": f"Invalid payload JSON: {e}"}}

        # Fill kn_id from env if missing.
        if "kn_id" not in body or not str(body.get("kn_id") or "").strip():
            env_kn_id = os.environ.get("CONTEXT_LOADER_KN_ID", "").strip()
            if not env_kn_id:
                return {"answer": {"error": "kn_id is required in payload or set CONTEXT_LOADER_KN_ID"}}
            body["kn_id"] = env_kn_id

        # Validate required fields
        if "query" not in body:
            return {"answer": {"error": "query is required in payload"}}

        try:
            data = self._post_json(
                endpoint=endpoint,
                body=body,
                base_url=None,  # Auto-loaded from env
                x_account_id=None,  # Auto-loaded from env
                x_account_type=None,  # Auto-loaded from env
                timeout_seconds=None,  # Auto-loaded from env
            )
            return {"answer": data}
        except Exception as e:
            return {"answer": {"error": f"concept_search request failed: {e}"}}

    def object_query(
        self,
        payload: str = "{}",
        **kwargs,
    ) -> Dict[str, Any]:
        """根据对象类ID精确查询实例数据。

        **功能说明**：
        - 基于 ot_id（对象类ID/concept_id）查询该类型的实例列表
        - 支持 condition 条件过滤、sort 排序、limit 分页
        - 返回实例的完整数据属性值

        **使用场景**：
        - 已知 ot_id，需要批量获取实例数据
        - 需要精确过滤条件（如 raceid == 20）
        - 需要排序或分页返回

        **重要限制**：
        - ot_id 是必填参数，来自 concept_search/object_search 返回的 concept_id
        - limit 范围：1-100，**超过 100 会自动修正为 100**
        - 某些字段不支持 condition 过滤，遇到 400 错误请改用 object_search

        **condition 条件格式**:
        
        1. 简化格式（推荐，自动转换）:
           - 等值: {"raceid": 20}
           - 多值: {"driverid": [1, 2, 3]}  → 自动转为 in
           - 多条件: {"raceid": 20, "position": 1}  → 自动转为 and

        2. 完整格式（需要 >, <, !=, match 等操作符时使用）:
           - 单条件: {"operation": "==", "field": "raceid", "value": 20, "value_from": "const"}
           - 支持的 operation: ==, !=, >, >=, <, <=, in, not_in, match, like
           - 组合条件: {"operation": "and", "sub_conditions": [条件1, 条件2, ...]}
           
           示例 - 查询 position > 5:
           {"operation": ">", "field": "position", "value": 5, "value_from": "const"}
           
           示例 - 文本模糊搜索:
           {"operation": "match", "field": "name", "value": "Hamilton", "value_from": "const"}

        **完整调用示例**:
        ```json
        {"ot_id": "qualifying", "limit": 100, "condition": {"raceid": 20}}
        ```

        Args:
            payload (str): JSON 请求体字符串，包含:
                - ot_id (str, 必填): 对象类ID，来自 concept_search/object_search 的 concept_id
                - limit (int, 必填): 返回数量，范围 1-100
                - condition (object, 可选): 过滤条件，支持简化格式 {"field": value}
                - sort (array, 可选): 排序规则
                - properties (array, 可选): 指定返回的属性字段

        Returns:
            Dict[str, Any]: {"answer": {"datas": [...], "type_info": {...}}}
        """
        endpoint = _ToolEndpoint(
            path="/api/agent-retrieval/in/v1/kn/query_object_instance",
            service_type="default",
        )
        try:
            payload_dict = _json_loads_loose(payload)
            if not isinstance(payload_dict, dict):
                return {"answer": {"error": "Payload must be a JSON object"}}
        except Exception as e:
            return {"answer": {"error": f"Invalid payload JSON: {e}"}}

        # Fill kn_id from env if missing.
        if "kn_id" not in payload_dict or not str(payload_dict.get("kn_id") or "").strip():
            env_kn_id = os.environ.get("CONTEXT_LOADER_KN_ID", "").strip()
            if not env_kn_id:
                return {"answer": {"error": "kn_id is required in payload or set CONTEXT_LOADER_KN_ID"}}
            payload_dict["kn_id"] = env_kn_id

        # Extract query parameters (kn_id and ot_id are required according to adp file)
        query_params: Dict[str, Any] = {}
        query_params["kn_id"] = payload_dict.pop("kn_id")
        
        if "ot_id" not in payload_dict:
            return {"answer": {"error": "ot_id is required in payload. Get it from concept_search or object_search result's concept_id field."}}
        query_params["ot_id"] = payload_dict.pop("ot_id")
        
        # Optional query parameters
        if "include_type_info" in payload_dict:
            query_params["include_type_info"] = payload_dict.pop("include_type_info")
        if "include_logic_params" in payload_dict:
            query_params["include_logic_params"] = payload_dict.pop("include_logic_params")
        
        # Remaining payload becomes request body (should contain limit and other FirstQueryWithSearchAfter fields)
        # According to ADP: request_body is optional, but if provided, limit is required
        body = payload_dict
        
        # Validate: if body is provided and not empty, limit should be present
        if body and "limit" not in body:
            return {"answer": {"error": "limit is required in request body (range: 1-100). Note: max is 100, not 200!"}}
        
        # Auto-clamp limit to 100 if it exceeds the API maximum
        if body and "limit" in body and body["limit"] > 100:
            body["limit"] = 100
        
        # Normalize condition format: support simplified {"field": value} syntax
        if body and "condition" in body:
            normalized = _normalize_condition(body["condition"])
            if normalized is None:
                # Remove invalid/empty condition
                del body["condition"]
            else:
                body["condition"] = normalized
        
        try:
            data = self._post_json(
                endpoint=endpoint,
                body=body,
                base_url=None,  # Auto-loaded from env
                x_account_id=None,  # Auto-loaded from env
                x_account_type=None,  # Auto-loaded from env
                timeout_seconds=None,  # Auto-loaded from env
                query_params=query_params,
            )
            return {"answer": data}
        except Exception as e:
            return {"answer": {"error": f"object_query request failed: {e}"}}

    def query_instance_subgraph(
        self,
        payload: str = "{}",
        **kwargs,
    ) -> Dict[str, Any]:
        """Query instance subgraph with a raw JSON payload.

        Args:
            payload (str): JSON string containing:
                - kn_id (str, optional): Will be auto-filled from CONTEXT_LOADER_KN_ID if missing (moved to query param)
                - include_logic_params (bool, optional): Include logic params (query param)
                - relation_type_paths (array, required if body is provided): Relation type paths array
            **kwargs: Other parameters (ignored for backward compatibility)

        Note:
            Configuration (base_url, account_id, account_type, timeout) is automatically loaded
            from environment variables set by the experiment runner. LLM does not need to provide these.
            kn_id will be automatically filled from CONTEXT_LOADER_KN_ID if not present in payload.
            
            According to API spec:
            - kn_id is a required query parameter
            - include_logic_params is an optional query parameter
            - Request body is optional, but if provided, relation_type_paths is required

        Returns:
            Dict[str, Any]: {"answer": <json_response>}
        """
        endpoint = _ToolEndpoint(
            path="/api/agent-retrieval/in/v1/kn/query_instance_subgraph",
            service_type="default",
        )
        try:
            payload_dict = _json_loads_loose(payload)
            if not isinstance(payload_dict, dict):
                return {"answer": {"error": "Payload must be a JSON object"}}
        except Exception as e:
            return {"answer": {"error": f"Invalid payload JSON: {e}"}}
        
        # Fill kn_id from env if missing.
        if "kn_id" not in payload_dict or not str(payload_dict.get("kn_id") or "").strip():
            env_kn_id = os.environ.get("CONTEXT_LOADER_KN_ID", "").strip()
            if not env_kn_id:
                return {"answer": {"error": "kn_id is required in payload or set CONTEXT_LOADER_KN_ID"}}
            payload_dict["kn_id"] = env_kn_id

        # Extract query parameters (kn_id is required, include_logic_params is optional)
        query_params: Dict[str, Any] = {}
        query_params["kn_id"] = payload_dict.pop("kn_id")
        
        if "include_logic_params" in payload_dict:
            query_params["include_logic_params"] = payload_dict.pop("include_logic_params")
        
        # Remaining payload becomes request body (should contain relation_type_paths if body is provided)
        # According to ADP: request_body is optional, but if provided, relation_type_paths is required
        body = payload_dict
        
        # Validate: if body is provided and not empty, relation_type_paths should be present
        if body and "relation_type_paths" not in body:
            return {"answer": {"error": "relation_type_paths is required in request body when body is provided"}}
        
        try:
            data = self._post_json(
                endpoint=endpoint,
                body=body,
                base_url=None,  # Auto-loaded from env
                x_account_id=None,  # Auto-loaded from env
                x_account_type=None,  # Auto-loaded from env
                timeout_seconds=None,  # Auto-loaded from env
                query_params=query_params,
            )
            return {"answer": data}
        except Exception as e:
            return {"answer": {"error": f"query_instance_subgraph request failed: {e}"}}

    def get_logic_property_values(
        self,
        payload: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """Resolve logic property values with a raw JSON payload.

        Args:
            payload (str): JSON request body as string. Must contain:
                - kn_id (str, optional): Will be auto-filled from CONTEXT_LOADER_KN_ID if missing
                - ot_id (str, required): Object type ID
                - query (str, required): User query string
                - unique_identities (array, required): Array of unique identity objects
                - properties (array, required): Array of property names to query
                - additional_context (str, optional): Additional context information
                - options (object, optional): Resolve options
            **kwargs: Other parameters (ignored for backward compatibility)

        Note:
            Configuration (base_url, account_id, account_type, timeout) is automatically loaded
            from environment variables set by the experiment runner. LLM does not need to provide these.
            kn_id will be automatically filled from CONTEXT_LOADER_KN_ID if not present in payload.

        Returns:
            Dict[str, Any]: {"answer": <json_response>}
        """
        endpoint = _ToolEndpoint(
            path="/api/agent-retrieval/in/v1/kn/logic-property-resolver",
            service_type="default",
        )
        try:
            body = _json_loads_loose(payload)
            if not isinstance(body, dict):
                return {"answer": {"error": "Payload must be a JSON object"}}
        except Exception as e:
            return {"answer": {"error": f"Invalid payload JSON: {e}"}}
        
        # Fill kn_id from env if missing.
        if "kn_id" not in body or not str(body.get("kn_id") or "").strip():
            env_kn_id = os.environ.get("CONTEXT_LOADER_KN_ID", "").strip()
            if not env_kn_id:
                return {"answer": {"error": "kn_id is required in payload or set CONTEXT_LOADER_KN_ID"}}
            body["kn_id"] = env_kn_id

        # Validate required fields according to ResolveLogicPropertiesRequest schema
        required_fields = ["ot_id", "query", "unique_identities", "properties"]
        missing_fields = [field for field in required_fields if field not in body]
        if missing_fields:
            return {"answer": {"error": f"Missing required fields: {', '.join(missing_fields)}"}}
        
        try:
            data = self._post_json(
                endpoint=endpoint,
                body=body,
                base_url=None,  # Auto-loaded from env
                x_account_id=None,  # Auto-loaded from env
                x_account_type=None,  # Auto-loaded from env
                timeout_seconds=None,  # Auto-loaded from env
            )
            return {"answer": data}
        except Exception as e:
            return {"answer": {"error": f"get_logic_property_values request failed: {e}"}}

    def _createSkills(self) -> List[SkillFunction]:
        return [
            SkillFunction(self.get_action_info),
            SkillFunction(self.concept_search),
            SkillFunction(self.object_search),
            SkillFunction(self.object_query),
            SkillFunction(self.query_instance_subgraph),
            SkillFunction(self.get_logic_property_values),
        ]


if __name__ == "__main__":
    # Test _normalize_condition function
    print("=" * 60)
    print("Testing _normalize_condition")
    print("=" * 60)
    
    test_cases = [
        # (input, description)
        ({"circuitid": 17}, "简化格式: 单字段等值查询"),
        ({"raceid": [1, 2, 3]}, "简化格式: 列表值自动转为 in"),
        ({"a": 1, "b": 2}, "简化格式: 多字段自动包装为 and"),
        ({"field": None}, "简化格式: None 值应被忽略"),
        ({"operation": "==", "field": "x", "value": 1, "value_from": "const"}, "标准格式: 直接透传"),
        ({"operation": "and", "sub_conditions": [
            {"field": "a", "operation": "==", "value": 1, "value_from": "const"}
        ]}, "标准格式: and 组合直接透传"),
        ({}, "空 dict"),
        ("not a dict", "非 dict 类型"),
    ]
    
    for i, (input_val, desc) in enumerate(test_cases, 1):
        print(f"\n[Test {i}] {desc}")
        print(f"  Input:  {input_val}")
        result = _normalize_condition(input_val)
        print(f"  Output: {result}")
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)
