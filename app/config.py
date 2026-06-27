from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Voice Data Assistant"
    MAX_RESULTS: int = 10

    # Voice
    OBFUSCATION_STRENGTH: str = "mild"  # mild, medium, strong
    STT_MODEL: str = "base"               # whisper model size

    # LLM
    OLLAMA_MODEL: str = "llama3.1:8b"
    
    # TTS (Edge TTS - free, no API key)
    EDGE_TTS_VOICE: str = "en-US-AriaNeural"

    # Security
    API_KEY: str = "secret-key-change-me"

    class Config:
        env_file = ".env"

settings = Settings()
