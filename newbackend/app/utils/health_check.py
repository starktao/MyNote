"""
Health Check Utilities
Check system health and AI connections
"""

from typing import List, Dict, Any
from app.infrastructure.database.connection import get_db
from app.services.model_service import ModelService
from app.repositories.provider_repository import ProviderRepository
from app.infrastructure.llm.provider import generate_markdown_via_llm


def check_database() -> Dict[str, Any]:
    """Check database connection"""
    try:
        from sqlalchemy import text
        db = next(get_db())
        db.execute(text("SELECT 1"))
        return {"status": "[OK]", "message": "Database connection normal"}
    except Exception as e:
        return {"status": "[ERROR]", "message": f"Database connection failed: {e}"}
    finally:
        if 'db' in locals():
            db.close()


def check_providers() -> List[Dict[str, Any]]:
    """Check AI provider configuration"""
    results = []
    try:
        with ProviderRepository() as provider_repo:
            providers = provider_repo.find_all_enabled()

        if not providers:
            results.append({"status": "[WARNING]", "message": "No AI providers configured"})
            return results

        for provider in providers:
            if provider.api_key:
                results.append({
                    "status": "[OK]",
                    "message": f"Provider {provider.name} ({provider.id}) configured normally"
                })
            else:
                results.append({
                    "status": "[ERROR]",
                    "message": f"Provider {provider.name} ({provider.id}) missing API key"
                })

    except Exception as e:
        results.append({"status": "[ERROR]", "message": f"Error checking providers: {e}"})

    return results


def check_models() -> List[Dict[str, Any]]:
    """Check AI model configuration"""
    results = []
    try:
        model_service = ModelService()
        models = model_service.get_active_models()

        if not models:
            results.append({"status": "[WARNING]", "message": "No AI models configured"})
        else:
            for model in models:
                with ProviderRepository() as provider_repo:
                    provider = provider_repo.find_by_id(model["provider_id"])
                if provider and provider.enabled:
                    results.append({
                        "status": "[OK]",
                        "message": f"Model {model['model_name']} (provider: {model['provider_id']}) configured normally"
                    })
                else:
                    results.append({
                        "status": "[ERROR]",
                        "message": f"Model {model['model_name']}'s provider {model['provider_id']} not found or disabled"
                    })

    except Exception as e:
        results.append({"status": "[ERROR]", "message": f"Error checking models: {e}"})

    return results


def test_ai_connection(provider_id: str, model_name: str) -> Dict[str, Any]:
    """Test AI connection"""
    try:
        # Use simple test text
        test_text = "This is a test."
        print(f"DEBUG: Calling generate_markdown_via_llm with provider_id={provider_id}, model_name={model_name}")

        result = generate_markdown_via_llm(
            provider_id=provider_id,
            model_name=model_name,
            transcript_text=test_text,
            style="concise",
            formats=[],
            extras=None
        )

        print(f"DEBUG: LLM returned result: '{result}'")
        print(f"DEBUG: Result length: {len(result) if result else 0}")

        # Check if meaningful content was returned - 只要模型返回了有效内容即表示连接成功
        if result and len(result.strip()) > 3:
            return {"status": "[OK]", "message": f"AI connection test successful (provider: {provider_id}, model: {model_name})"}
        else:
            print(f"DEBUG: Failed validation - result exists: {bool(result)}, stripped length > 3: {len(result.strip()) > 3 if result else False}")
            return {"status": "[ERROR]", "message": f"AI connection test failed, returned empty or invalid response (provider: {provider_id}, model: {model_name})"}

    except Exception as e:
        print(f"DEBUG: Exception in test_ai_connection: {str(e)}")
        import traceback
        print(f"DEBUG: Full traceback: {traceback.format_exc()}")
        return {"status": "[ERROR]", "message": f"AI connection test failed (provider: {provider_id}, model: {model_name}): {e}"}


