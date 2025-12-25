"""
Provider Controller - AI Provider Management
"""

from fastapi import APIRouter
from app.utils.response import R
from app.utils.health_check import test_ai_connection
from typing import Dict

router = APIRouter(tags=["Providers"])


@router.get("/providers")
async def get_providers():
    """Get all providers (placeholder)"""
    return R.success({"message": "Providers endpoint - coming soon"})


@router.post("/providers")
async def create_provider():
    """Create provider (placeholder)"""
    return R.success({"message": "Create provider endpoint - coming soon"})


@router.post("/connect_test")
def connect_test(body: Dict):
    """Test AI connection"""
    print("=" * 50)
    print("DEBUG: Received connection test request")
    print(f"Request body: {body}")
    print("=" * 50)

    try:
        provider_id = body.get("provider_id")
        model_name = body.get("model_name", "gpt-3.5-turbo")

        print(f"DEBUG: provider_id = {provider_id}, model_name = {model_name}")

        if not provider_id:
            print("DEBUG: Missing provider_id")
            return R.error("需要提供provider_id", 400)

        # Test AI connection
        print(f"DEBUG: Testing AI connection for {provider_id}/{model_name}...")
        result = test_ai_connection(provider_id, model_name)
        print(f"DEBUG: Test result: {result}")

        if result["status"] == "[OK]":
            print("DEBUG: Connection test successful")
            return R.success({"message": "连接测试成功", "ok": True})
        else:
            print(f"DEBUG: Connection test failed: {result['message']}")
            return R.error(result["message"], 400)

    except Exception as e:
        print(f"DEBUG: Exception in connect_test: {str(e)}")
        import traceback
        print(f"DEBUG: Full traceback: {traceback.format_exc()}")

        # Return friendly error messages based on error type
        error_msg = str(e)
        if "timeout" in error_msg.lower():
            return R.error("连接超时，请检查网络或更换模型", 400)
        elif "api" in error_msg.lower() and "key" in error_msg.lower():
            return R.error("API密钥无效，请检查配置", 400)
        elif "connection" in error_msg.lower():
            return R.error("网络连接失败，请检查网络设置", 400)
        else:
            return R.error(f"连接测试失败: {error_msg}", 400)