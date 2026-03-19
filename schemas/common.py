# schemas/common.py
"""
通用请求体模型
"""
from typing import Any

from pydantic import BaseModel, Field


class IdBody(BaseModel):
    """仅需 id 的请求（如 delete）"""
    id: int | None = None


class ListQuery(BaseModel):
    """列表查询参数（GET 用 Query，POST 用 Body）"""
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(10, ge=1, le=1000, description="每页条数")
    query: dict[str, Any] | None = Field(None, description="筛选条件")
