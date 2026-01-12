"""
Common Schemas - 通用响应结构

定义所有 API 使用的标准响应格式。
"""

from __future__ import annotations

from typing import Optional, Dict, Any, List, Generic, TypeVar
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

T = TypeVar("T")


class BaseSchema(BaseModel):
    """基础 Schema 类
    
    所有 Schema 都应该继承此类以保持一致性。
    """
    model_config = ConfigDict(
        from_attributes=True,  # 支持从 ORM 转换
        use_enum_values=True,
        validate_assignment=True,
        json_schema_extra={"example": {}}
    )


class BaseResponse(BaseModel):
    """基础 API 响应
    
    标准的 API 响应格式，所有端点都应该返回此格式。
    """
    success: bool = Field(True, description="请求是否成功")
    data: Optional[Dict[str, Any]] = Field(None, description="响应数据")
    error: Optional[str] = Field(None, description="错误信息（如果失败）")
    message: Optional[str] = Field(None, description="提示信息")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "data": {"id": 1},
                "error": None,
                "message": "操作成功"
            }
        }
    )


class DataResponse(BaseModel, Generic[T]):
    """数据响应
    
    用于返回单个对象的响应。
    """
    success: bool = Field(True, description="请求是否成功")
    data: T = Field(..., description="响应数据")
    message: Optional[str] = Field(None, description="提示信息")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "data": {"id": 1, "name": "示例"},
                "message": "获取成功"
            }
        }
    )


class ListResponse(BaseModel, Generic[T]):
    """列表响应
    
    用于返回对象列表的响应。
    """
    success: bool = Field(True, description="请求是否成功")
    data: List[T] = Field(..., description="数据列表")
    total: int = Field(..., description="总记录数")
    page: int = Field(1, description="当前页码")
    page_size: int = Field(20, description="每页记录数")
    message: Optional[str] = Field(None, description="提示信息")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "data": [{"id": 1}, {"id": 2}],
                "total": 100,
                "page": 1,
                "page_size": 20,
                "message": "获取成功"
            }
        }
    )


from enum import Enum

class ErrorCode(str, Enum):
    """标准错误码定义"""
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    
    # 业务特定错误码
    TOOL_EXECUTION_FAILED = "TOOL_EXECUTION_FAILED"
    LLM_CALL_FAILED = "LLM_CALL_FAILED"
    MCP_CONNECTION_ERROR = "MCP_CONNECTION_ERROR"
    PREFLIGHT_CHECK_FAILED = "PREFLIGHT_CHECK_FAILED"
    JOB_EXECUTION_ERROR = "JOB_EXECUTION_ERROR"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"

class ErrorResponse(BaseModel):
    """错误响应
    
    用于返回错误信息的响应。
    """
    success: bool = Field(False, description="请求是否成功")
    error: str = Field(..., description="错误类型")
    detail: str = Field(..., description="错误详情")
    code: ErrorCode = Field(ErrorCode.INTERNAL_SERVER_ERROR, description="错误代码")
    hints: List[str] = Field(default_factory=list, description="针对错误或警告的建议动作")
    data: Optional[Dict[str, Any]] = Field(None, description="附加错误上下文数据")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": False,
                "error": "ValidationError",
                "detail": "参数验证失败",
                "code": "VALIDATION_ERROR",
                "hints": ["Check input parameters"],
                "data": {"field": "ticker"}
            }
        }
    )


class PaginationParams(BaseModel):
    """分页参数
    
    用于请求列表时的分页参数。
    """
    page: int = Field(1, ge=1, description="页码（从 1 开始）")
    page_size: int = Field(20, ge=1, le=100, description="每页记录数（1-100）")
    sort_by: Optional[str] = Field(None, description="排序字段")
    sort_order: Optional[str] = Field("asc", pattern="^(asc|desc)$", description="排序方向")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "page": 1,
                "page_size": 20,
                "sort_by": "created_at",
                "sort_order": "desc"
            }
        }
    )
    
    @property
    def offset(self) -> int:
        """计算偏移量"""
        return (self.page - 1) * self.page_size


class HealthResponse(BaseModel):
    """健康检查响应

    用于健康检查端点的响应。
    """
    status: str = Field(..., description="服务状态")
    version: str = Field(..., description="服务版本")
    timestamp: datetime = Field(default_factory=datetime.now, description="检查时间")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "timestamp": "2025-12-26T00:00:00Z"
            }
        }
    )


class SuccessResponse(BaseModel):
    """Unified success response format.

    Use this for simple success responses from CRUD operations.
    """
    status: str = Field("success", description="操作状态")
    message: str = Field(..., description="操作结果描述")
    data: Optional[Dict[str, Any]] = Field(None, description="附加数据")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"status": "success", "message": "Operation completed"},
                {"status": "success", "message": "Item deleted", "data": {"id": 123}}
            ]
        }
    )


__all__ = [
    "BaseSchema",
    "BaseResponse",
    "DataResponse",
    "ListResponse",
    "ErrorResponse",
    "PaginationParams",
    "HealthResponse",
    "SuccessResponse",
]
