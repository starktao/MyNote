"""
Provider Related DTOs
"""

from typing import Optional
from pydantic import BaseModel, Field


class ProviderRequestDTO(BaseModel):
    name: str = Field(..., description="提供商名称")
    logo: str = Field(default="default", description="提供商logo")
    type: str = Field(default="custom", description="提供商类型")
    api_key: Optional[str] = Field(None, description="API密钥")
    base_url: Optional[str] = Field(None, description="API基础URL")
    enabled: bool = Field(default=True, description="是否启用")


class ProviderResponseDTO(BaseModel):
    id: str
    name: str
    logo: str
    type: str
    api_key: Optional[str]
    base_url: Optional[str]
    enabled: bool
    created_at: str
    updated_at: str


class ProviderTestDTO(BaseModel):
    model_config = {"protected_namespaces": ()}  # 允许 model_ 开头的字段名

    provider_id: str = Field(..., description="提供商ID")
    model_name: str = Field(..., description="测试模型名称")
    test_prompt: str = Field(default="Hello, test connection", description="测试提示词")


class ProviderTestResultDTO(BaseModel):
    model_config = {"protected_namespaces": ()}  # 允许 model_ 开头的字段名

    success: bool
    provider_id: str
    model_name: str
    response: Optional[str] = None
    error: Optional[str] = None
    response_time: Optional[float] = None