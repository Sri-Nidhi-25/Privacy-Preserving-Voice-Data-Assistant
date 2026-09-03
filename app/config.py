from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Voice Data Assistant"
    MAX_RESULTS: int = 10

    # Voice
    OBFUSCATION_STRENGTH: str = "mild"
    STT_MODEL: str = "small.en"               

    # LLM
    OLLAMA_MODEL: str = "llama3.2:latest "
    
    # TTS (Edge TTS - free, no API key)
    EDGE_TTS_VOICE: str = "en-US-GuyNeural"

    # Security
    API_KEY: str = "secret-key-change-me"

    class Config:
        env_file = ".env"

settings = Settings()

