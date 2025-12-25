from app.infrastructure.database.connection import engine, SessionLocal
from app.infrastructure.database.db import Base


def init_db():
    from app.models.database.provider import Provider
    import json
    import os

    Base.metadata.create_all(bind=engine)

    # Initialize built-in providers
    init_builtin_providers()


def init_builtin_providers():
    """Initialize built-in AI providers"""
    from app.models.database.provider import Provider
    import json
    import os

    db = SessionLocal()
    try:
        # 检查是否已有内置提供商
        existing_builtin = db.query(Provider).filter(Provider.type == "built-in").count()
        if existing_builtin > 0:
            return

        # 读取内置提供商配置
        builtin_file = os.path.join(os.path.dirname(__file__), "builtin_providers.json")
        if os.path.exists(builtin_file):
            with open(builtin_file, "r", encoding="utf-8") as f:
                builtin_providers = json.load(f)

            for provider_data in builtin_providers:
                provider = Provider(
                    id=provider_data["id"],
                    name=provider_data["name"],
                    logo=provider_data["logo"],
                    type=provider_data["type"],
                    api_key=provider_data["api_key"],
                    base_url=provider_data["base_url"],
                    enabled=provider_data.get("enabled", False)
                )
                db.add(provider)

            db.commit()
            print(f"Successfully initialized {len(builtin_providers)} builtin AI providers")
    except Exception as e:
        print(f"Failed to initialize builtin providers: {e}")
        db.rollback()
    finally:
        db.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

