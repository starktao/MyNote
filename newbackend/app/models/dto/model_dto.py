"""
Model Related DTOs
"""

from typing import Optional
from pydantic import BaseModel, Field


class ModelRequestDTO(BaseModel):
    provider_id: str = Field(..., description="提供商ID")
    name: str = Field(..., description="模型名称")
    alias: Optional[str] = Field(None, description="模型别名")
    enabled: bool = Field(default=True, description="是否启用")


class ModelResponseDTO(BaseModel):
    id: str
    provider_id: str
    name: str
    alias: Optional[str]
    enabled: bool
    created_at: str


class ModelActivationDTO(BaseModel):
    model_config = {"protected_namespaces": ()}  # 允许 model_ 开头的字段名

    model_id: str = Field(..., description="模型ID")
    enabled: bool = Field(..., description="是否启用")


class ModelConfigDTO(BaseModel):
    model_config = {"protected_namespaces": ()}  # 允许 model_ 开头的字段名

    model_id: str = Field(..., description="模型ID")
    api_key: str = Field(..., description="API密钥")