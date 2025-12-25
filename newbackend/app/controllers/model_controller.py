"""
Model Controller - AI Model Management
"""

from fastapi import APIRouter
from typing import List
from pydantic import BaseModel, Field
from app.utils.response import R
from app.repositories.model_repository import ModelRepository
from app.services.model_service import ModelService
from app.models.dto.model_dto import ModelConfigDTO

router = APIRouter(tags=["Models"])


class ModelReconfigDTO(BaseModel):
    """Model reconfiguration request DTO"""
    api_key: str = Field(..., min_length=1, description="New API key for the model")


@router.get("/models")
def get_models():
    """Get all models"""
    try:
        model_service = ModelService()
        models = model_service.get_all_models()
        return R.success(models)
    except Exception as e:
        return R.error(msg=f"Failed to get models: {str(e)}")


@router.get("/models/active")
def get_active_models():
    """Get active models only"""
    try:
        model_service = ModelService()
        active_models = model_service.get_active_models()
        return R.success(active_models)
    except Exception as e:
        return R.error(msg=f"Failed to get active models: {str(e)}")


@router.get("/model_list")
def get_model_list():
    """Get model list (alias for compatibility)"""
    return get_models()


@router.get("/supported_models")
def get_supported_models_endpoint():
    """Get supported models (predefined list)"""
    try:
        model_service = ModelService()
        supported = model_service.get_supported_models()
        return R.success(supported)
    except Exception as e:
        return R.error(msg=f"Failed to get supported models: {str(e)}")


@router.get("/model_enable/{provider_id}")
def model_enable(provider_id: str):
    """获取启用的模型"""
    try:
        model_service = ModelService()
        models = model_service.get_models_by_provider(provider_id)

        # 只返回启用的模型
        enabled_models = [model for model in models if model.get("enabled", False)]

        data = [
            {
                "id": model["id"],
                "model_name": model["model_name"],
                "alias": model["alias"] or model["model_name"],
            }
            for model in enabled_models
        ]
        return R.success(data)
    except Exception as e:
        return R.error(str(e))


@router.post("/models")
async def create_model():
    """Create a new model"""
    try:
        model_service = ModelService()
        # This is a placeholder - would need request body
        return R.success({"message": "Create model endpoint - implementation needed"})
    except Exception as e:
        return R.error(msg=f"Failed to create model: {str(e)}")


@router.get("/models/{model_id}/configuration")
async def get_model_configuration(model_id: str):
    """Get model configuration with masked API key"""
    try:
        model_service = ModelService()
        config = model_service.get_model_configuration(model_id)
        return R.success(config)
    except Exception as e:
        return R.error(msg=f"Failed to get model configuration: {str(e)}")


@router.put("/models/{model_id}")
async def reconfigure_model(model_id: str, reconfig_data: ModelReconfigDTO):
    """Reconfigure model with new API key"""
    try:
        model_service = ModelService()
        result = model_service.reconfigure_model(model_id, reconfig_data.api_key)
        return R.success(result)
    except Exception as e:
        return R.error(msg=f"Failed to reconfigure model: {str(e)}")


@router.post("/configure_model")
def configure_model(config: ModelConfigDTO):
    """Configure model with API key"""
    try:
        model_service = ModelService()
        result = model_service.configure_model(config.model_id, config.api_key)
        return R.success(result)
    except Exception as e:
        return R.error(msg=f"Failed to configure model: {str(e)}")


@router.delete("/models/{model_id}")
def delete_model(model_id: str):
    """Delete model configuration"""
    print("=" * 50)
    print(f"DEBUG CONTROLLER V2: Received delete request for model_id: {model_id}")
    print("=" * 50)
    try:
        print(f"Debug Controller: Creating ModelService instance...")
        model_service = ModelService()
        print(f"Debug Controller: ModelService created, calling delete_model...")
        result = model_service.delete_model(model_id)
        print(f"Debug Controller: Delete successful, result: {result}")
        return R.success(result)
    except Exception as e:
        print(f"Debug Controller: Delete failed with error: {str(e)}")
        import traceback
        print(f"Debug Controller: Full traceback: {traceback.format_exc()}")
        return R.error(msg=f"Failed to delete model: {str(e)}")


@router.post("/models/{model_id}/activate")
def activate_model(model_id: str):
    """Activate a specific model"""
    try:
        model_service = ModelService()
        result = model_service.activate_model(model_id)
        return R.success(result)
    except Exception as e:
        return R.error(msg=f"Failed to activate model: {str(e)}")


@router.get("/model/active")
def get_active_model():
    """Get currently active model"""
    try:
        model_service = ModelService()
        result = model_service.get_active_model()
        return R.success(result)
    except Exception as e:
        return R.error(msg=f"Failed to get active model: {str(e)}")