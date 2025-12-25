"""
Model Service - Business Logic for AI Models
"""

from typing import List, Optional, Dict, Any
from app.repositories.model_repository import ModelRepository
from app.repositories.provider_repository import ProviderRepository
from app.models.database.model import Model
from app.models.database.provider import Provider

# 支持的模型白名单 - 只保留4个模型
SUPPORTED_MODELS = [
    {
        "id": "openai-gpt-4o-mini",
        "name": "GPT-4o Mini",
        "provider": "OpenAI",
        "provider_id": "openai",
        "model_name": "gpt-4o-mini",
        "description": "ChatGPT - 轻量版GPT-4o，速度快成本低",
        "base_url": "https://api.openai.com/v1"
    },
    {
        "id": "qwen-plus",
        "name": "千问-Plus",
        "provider": "阿里云",
        "provider_id": "qwen",
        "model_name": "qwen-plus",
        "description": "千问Plus模型，平衡性能和成本",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"
    },
    {
        "id": "qwen-vl-plus",
        "name": "千问3-VL-Plus",
        "provider": "阿里云",
        "provider_id": "qwen",
        "model_name": "qwen-vl-plus",
        "description": "千问3-VL-Plus多模态模型，支持图像理解",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"
    },
    {
        "id": "deepseek-chat",
        "name": "DeepSeek Chat",
        "provider": "DeepSeek",
        "provider_id": "deepseek",
        "model_name": "deepseek-chat",
        "description": "DeepSeek对话模型",
        "base_url": "https://api.deepseek.com"
    }
]


class ModelService:
    """AI model management service"""

    def __init__(self):
        """Initialize model service - 使用新的上下文管理器模式"""
        pass

    def get_supported_models(self) -> List[dict]:
        """Get all supported models (predefined whitelist)"""
        return SUPPORTED_MODELS

    def get_all_models(self) -> List[Dict[str, Any]]:
        """Get all models from database"""
        try:
            print("Debug: Getting all models from database...")
            with ModelRepository() as model_repo:
                models = model_repo.find_all()
            print(f"Debug: Found {len(models)} models in database")
            result = []
            for model in models:
                print(f"Debug: Processing model: {model.id}")
                result.append({
                    "id": model.id,
                    "provider_id": model.provider_id,
                    "model_name": model.name,
                    "alias": model.alias or model.name,
                    "enabled": bool(model.enabled),
                    "created_at": model.created_at.isoformat() if model.created_at else None,
                })
            print(f"Debug: Returning {len(result)} models")
            return result
        except Exception as e:
            print(f"Debug: Error in get_all_models: {str(e)}")
            raise Exception(f"Failed to get all models: {str(e)}")

    def get_active_models(self) -> List[Dict[str, Any]]:
        """Get only enabled/active models"""
        try:
            with ModelRepository() as model_repo:
                models = model_repo.find_by_condition({"enabled": True})
            result = []
            for model in models:
                result.append({
                    "id": model.id,
                    "provider_id": model.provider_id,
                    "model_name": model.name,
                    "alias": model.alias or model.name,
                    "enabled": bool(model.enabled),
                    "created_at": model.created_at.isoformat() if model.created_at else None,
                })
            return result
        except Exception as e:
            raise Exception(f"Failed to get active models: {str(e)}")

    def get_model_by_id(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific model by ID"""
        try:
            with ModelRepository() as model_repo:
                model = model_repo.find_by_id(model_id)
            if not model:
                return None

            return {
                "id": model.id,
                "provider_id": model.provider_id,
                "model_name": model.name,
                "alias": model.alias or model.name,
                "enabled": bool(model.enabled),
                "created_at": model.created_at.isoformat() if model.created_at else None,
            }
        except Exception as e:
            raise Exception(f"Failed to get model {model_id}: {str(e)}")

    def create_model(self, model_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new model"""
        try:
            model = Model(
                id=model_data.get("id"),
                name=model_data.get("model_name", model_data.get("name")),
                provider_id=model_data.get("provider_id"),
                alias=model_data.get("alias"),
                enabled=model_data.get("enabled", True)
            )

            with ModelRepository() as model_repo:
                created_model = model_repo.create(model)

            return {
                "id": created_model.id,
                "provider_id": created_model.provider_id,
                "model_name": created_model.name,
                "alias": created_model.alias or created_model.name,
                "enabled": bool(created_model.enabled),
                "created_at": created_model.created_at.isoformat() if created_model.created_at else None,
            }
        except Exception as e:
            raise Exception(f"Failed to create model: {str(e)}")

    def update_model(self, model_id: str, model_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing model"""
        try:
            with ModelRepository() as model_repo:
                existing_model = model_repo.find_by_id(model_id)
                if not existing_model:
                    raise Exception(f"Model {model_id} not found")

                # Update fields
                for key, value in model_data.items():
                    if hasattr(existing_model, key) and key in ["name", "alias", "enabled"]:
                        setattr(existing_model, key, value)

                updated_model = model_repo.update(existing_model)

            return {
                "id": updated_model.id,
                "provider_id": updated_model.provider_id,
                "model_name": updated_model.name,
                "alias": updated_model.alias or updated_model.name,
                "enabled": bool(updated_model.enabled),
                "created_at": updated_model.created_at.isoformat() if updated_model.created_at else None,
            }
        except Exception as e:
            raise Exception(f"Failed to update model {model_id}: {str(e)}")

    def get_model_configuration(self, model_id: str) -> Dict[str, Any]:
        """Get model configuration with masked API key"""
        try:
            with ModelRepository() as model_repo:
                model = model_repo.find_by_id(model_id)
                if not model:
                    raise Exception(f"Model not found: {model_id}")

            with ProviderRepository() as provider_repo:
                provider = provider_repo.find_by_id(model.provider_id)
                if not provider:
                    raise Exception(f"Provider not found: {model.provider_id}")

            # Mask API key for security
            api_key = provider.api_key or ""
            masked_api_key = self._mask_api_key(api_key) if api_key else ""

            return {
                "model_id": model.id,
                "model_name": model.name,
                "provider_id": provider.id,
                "provider_name": provider.name,
                "provider_type": provider.type,
                "api_key": masked_api_key,
                "base_url": provider.base_url or "",
                "enabled": bool(model.enabled),
                "has_api_key": bool(api_key)
            }
        except Exception as e:
            raise Exception(f"Failed to get model configuration: {str(e)}")

    def reconfigure_model(self, model_id: str, new_api_key: str) -> Dict[str, Any]:
        """Reconfigure model with new API key"""
        try:
            # First, get model info
            with ModelRepository() as model_repo:
                model = model_repo.find_by_id(model_id)
                if not model:
                    raise Exception(f"模型未找到: {model_id}")

            # Get provider info
            with ProviderRepository() as provider_repo:
                provider = provider_repo.find_by_id(model.provider_id)
                if not provider:
                    raise Exception(f"Provider未找到: {model.provider_id}")

            # ===== 新增：重配置前验证连接 =====
            # 从白名单中查找模型配置
            supported_models = self.get_supported_models()
            model_config = None
            for supported in supported_models:
                if supported["provider_id"] == model.provider_id and supported["model_name"] == model.name:
                    model_config = supported
                    break

            if not model_config:
                # 如果白名单中找不到，使用现有provider信息构建配置
                model_config = {
                    "model_name": model.name,
                    "base_url": provider.base_url or "",
                    "provider_id": provider.id
                }

            print(f"[MODEL_SERVICE] 开始验证新API Key连接...")
            self._verify_connection(model_config, new_api_key)
            print(f"[MODEL_SERVICE] 新API Key验证通过，开始更新配置")
            # =====================================

            # Update the API key
            updated_provider = provider_repo.update(provider.id, {"api_key": new_api_key})

            # Return updated configuration with masked API key
            masked_api_key = self._mask_api_key(new_api_key)

            return {
                "model_id": model.id,
                "model_name": model.name,
                "provider_id": updated_provider.id,
                "provider_name": updated_provider.name,
                "api_key": masked_api_key,
                "base_url": updated_provider.base_url or "",
                "enabled": bool(model.enabled),
                "message": "模型重新配置成功"
            }
        except Exception as e:
            # 如果是验证失败，直接抛出原始错误信息
            raise Exception(str(e))

    def _mask_api_key(self, api_key: str) -> str:
        """Mask API key for display"""
        if not api_key or len(api_key) < 8:
            return api_key

        # Show first 3 and last 3 characters, mask the rest
        if len(api_key) <= 10:
            return api_key[:2] + "***" + api_key[-2:]
        else:
            return api_key[:3] + "***" + api_key[-3:]

    def _verify_connection(self, model_config: Dict[str, Any], api_key: str) -> None:
        """
        验证模型连接

        Args:
            model_config: 模型配置信息
            api_key: API密钥

        Raises:
            Exception: 连接失败时抛出异常，包含详细错误信息
        """
        try:
            print(f"[MODEL_SERVICE] 验证模型连接: {model_config['model_name']}")

            # 导入 AIService
            from app.services.ai_service import AIService

            # 创建 AIService 实例
            ai_service = AIService(
                api_key=api_key,
                base_url=model_config['base_url'],
                model_name=model_config['model_name']
            )

            # 测试连接
            success = ai_service.test_connection()

            if not success:
                raise Exception("连接测试失败")

            print(f"[MODEL_SERVICE] 连接验证成功")

        except Exception as e:
            error_msg = str(e).lower()

            # 根据错误类型提供详细提示
            if '401' in error_msg or 'unauthorized' in error_msg or 'invalid' in error_msg:
                raise Exception(f"API Key 无效，请检查您的密钥是否正确")
            elif 'timeout' in error_msg or 'timed out' in error_msg:
                raise Exception(f"连接超时，请检查网络连接或API服务是否可用")
            elif 'connection' in error_msg or 'network' in error_msg:
                raise Exception(f"无法连接到API服务，请检查网络或base_url配置")
            elif 'not found' in error_msg or '404' in error_msg:
                raise Exception(f"模型 {model_config['model_name']} 不存在，请检查模型名称")
            else:
                raise Exception(f"连接验证失败: {str(e)}")

    def delete_model(self, model_id: str) -> Dict[str, Any]:
        """Delete a model configuration"""
        try:
            print(f"Debug: Attempting to delete model with ID: {model_id}")

            # First, print all models in database for debugging
            with ModelRepository() as model_repo:
                all_models = model_repo.find_all()
            print(f"Debug: All models in database:")
            for model in all_models:
                print(f"  - ID: {model.id}, provider_id: {model.provider_id}, name: {model.name}")

            # Find the model
            with ModelRepository() as model_repo:
                model = model_repo.find_by_id(model_id)
                if not model:
                    print(f"Debug: Model with ID {model_id} not found in database")
                    raise Exception(f"Model not found: {model_id}")

                print(f"Debug: Found model: {model.id}, provider: {model.provider_id}")

                provider_id = model.provider_id

                # Delete the model
                success = model_repo.delete(model_id)
                print(f"Debug: Delete operation result: {success}")
                if not success:
                    raise Exception("Failed to delete model")

            # Check if provider has other models, if not delete the provider
            with ModelRepository() as model_repo:
                remaining_models = model_repo.find_by_condition({"provider_id": provider_id})
            if not remaining_models:
                with ProviderRepository() as provider_repo:
                    provider = provider_repo.find_by_id(provider_id)
                    if provider and provider.type == "built-in":
                        print(f"Debug: Deleting provider {provider_id} as no more models")
                        provider_repo.delete(provider_id)

            return {"message": "Model configuration deleted successfully"}
        except Exception as e:
            print(f"Debug: Error in delete_model: {str(e)}")
            raise Exception(f"Failed to delete model: {str(e)}")

    def get_models_by_provider(self, provider_id: str) -> List[Dict[str, Any]]:
        """Get models by provider"""
        try:
            with ModelRepository() as model_repo:
                models = model_repo.find_by_condition({"provider_id": provider_id})
            result = []
            for model in models:
                result.append({
                    "id": model.id,
                    "provider_id": model.provider_id,
                    "model_name": model.name,
                    "alias": model.alias or model.name,
                    "enabled": bool(model.enabled),
                    "created_at": model.created_at.isoformat() if model.created_at else None,
                })
            return result
        except Exception as e:
            raise Exception(f"Failed to get models for provider {provider_id}: {str(e)}")

    def configure_model(self, model_id: str, api_key: str) -> Dict[str, Any]:
        """Configure model with API key"""
        try:
            # Find the model configuration from supported models
            supported_models = self.get_supported_models()
            model_config = None
            for model in supported_models:
                if model["id"] == model_id:
                    model_config = model
                    break

            if not model_config:
                # Debug: Print supported model IDs
                supported_ids = [m["id"] for m in supported_models]
                print(f"Debug: Requested model_id: {model_id}")
                print(f"Debug: Supported model IDs: {supported_ids}")
                raise Exception(f"不支持的模型: {model_id}，当前仅支持 4 个模型")

            # ===== 新增：配置前验证连接 =====
            print(f"[MODEL_SERVICE] 开始验证连接...")
            self._verify_connection(model_config, api_key)
            print(f"[MODEL_SERVICE] 连接验证通过，开始保存配置")
            # =====================================

            # Check if provider exists
            with ProviderRepository() as provider_repo:
                provider = provider_repo.find_by_id(model_config["provider_id"])

                if provider:
                    # Update existing provider's API key
                    provider.api_key = api_key
                    provider.enabled = True
                    provider_repo.update(provider.id, {
                        "api_key": api_key,
                        "enabled": True
                    })
                else:
                    # Create new provider
                    provider = Provider(
                        id=model_config["provider_id"],
                        name=model_config["provider"],
                        logo=model_config["provider"][0],
                        type="built-in",
                        api_key=api_key,
                        base_url=model_config["base_url"],
                        enabled=True
                    )
                    provider_repo.create(provider)

            # Check if model exists
            with ModelRepository() as model_repo:
                existing_models = model_repo.find_by_condition({
                    "provider_id": model_config["provider_id"],
                    "name": model_config["model_name"]
                })
                model = existing_models[0] if existing_models else None

                if not model:
                    # Create model with proper ID format (avoid duplicate provider prefix)
                    if model_config["model_name"].startswith(model_config["provider_id"] + "-"):
                        model_id_new = model_config["model_name"]
                    else:
                        model_id_new = f"{model_config['provider_id']}-{model_config['model_name']}"

                    model = Model(
                        id=model_id_new,
                        provider_id=model_config["provider_id"],
                        name=model_config["model_name"],
                        alias=model_config["name"],
                        enabled=True
                    )
                    model_repo.create(model)

            return {
                "message": "模型配置成功",
                "model_id": model_id_new if 'model_id_new' in locals() else model_id,
                "provider_id": model_config["provider_id"],
                "model_name": model_config["model_name"]
            }
        except Exception as e:
            # 如果是验证失败，直接抛出原始错误信息
            raise Exception(str(e))

    def activate_model(self, model_id: str) -> Dict[str, Any]:
        """Activate a specific model"""
        try:
            # Find the model
            with ModelRepository() as model_repo:
                model = model_repo.find_by_id(model_id)
                if not model:
                    raise Exception("Model not found")

                model_name = model.name  # Store for return statement

            # Check if provider exists and has API key
            with ProviderRepository() as provider_repo:
                provider = provider_repo.find_by_id(model.provider_id)
                if not provider or not provider.api_key:
                    raise Exception("Model not configured with API key")

            # Deactivate all models and activate the specified one
            with ModelRepository() as model_repo:
                all_models = model_repo.find_all()
                for m in all_models:
                    if m.enabled:
                        model_repo.update_enabled(m.id, False)

                # Activate the specified model
                model_repo.update_enabled(model_id, True)

            return {
                "message": "Model activated",
                "model_id": model_id,
                "model_name": model_name
            }
        except Exception as e:
            raise Exception(f"Failed to activate model: {str(e)}")

    def get_active_model(self) -> Dict[str, Any]:
        """Get currently active model"""
        try:
            # Find enabled model
            with ModelRepository() as model_repo:
                enabled_models = model_repo.find_by_condition({"enabled": True})
            if not enabled_models:
                return {"active_model": None}

            model = enabled_models[0]  # Get first enabled model

            # Get provider
            with ProviderRepository() as provider_repo:
                provider = provider_repo.find_by_id(model.provider_id)

            # Find model info from supported models
            supported_models = self.get_supported_models()
            model_info = None
            for supported in supported_models:
                if supported["id"] == model.id:
                    model_info = supported
                    break

            return {
                "active_model": {
                    "id": model.id,
                    "name": model.name,
                    "alias": model.alias or model.name,
                    "provider": provider.name if provider else "Unknown",
                    "model_info": model_info
                }
            }
        except Exception as e:
            raise Exception(f"Failed to get active model: {str(e)}")