import os
from dotenv import load_dotenv

# Carga las variables de entorno desde el archivo .env si existe en backend/
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(dotenv_path=dotenv_path)

class Settings:
    """
    Configuración centralizada y segura de AgroSense AI.
    Lee de variables de entorno o del archivo .env local.
    """
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    
    # Proveedor LLM (DeepSeek / OpenAI compatible)
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "deepseek-chat")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
    AZURE_OPENAI_ENDPOINT: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    
    # Motor de Decisiones IA: TypeSafe Jev (jevai.net)
    JEV_MODEL_NAME: str = os.getenv("JEV_MODEL_NAME", "typesafe/jev-latest")
    JEV_DECISIONS_API_URL: str = os.getenv("JEV_DECISIONS_API_URL", "https://openrouter.ai/api/alpha/decisions")
    
    # Token de seguridad para dispositivos en terreno
    JEV_DEVICE_AUTH_TOKEN: str = os.getenv("JEV_DEVICE_AUTH_TOKEN", "default_secret_token")
    
    # Base de Datos
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./app/agrosense.db")

settings = Settings()
