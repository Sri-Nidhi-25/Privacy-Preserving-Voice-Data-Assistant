from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Voice Data Assistant"
    MAX_RESULTS: int = 10

    # Voice
    OBFUSCATION_STRENGTH: str = "mild"
    STT_MODEL: str = "small.en"               

    # LLM
    OLLAMA_MODEL: str = "llama3.2:latest"
    
    # TTS (Edge TTS - free, no API key)
    EDGE_TTS_VOICE: str = "en-US-GuyNeural"

    # Security
    API_KEY: str = "secret-key-change-me"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure string settings do not contain accidental leading/trailing whitespace
        self.OLLAMA_MODEL = self.OLLAMA_MODEL.strip()
        self.STT_MODEL = self.STT_MODEL.strip()
        self.EDGE_TTS_VOICE = self.EDGE_TTS_VOICE.strip()
        self.OBFUSCATION_STRENGTH = self.OBFUSCATION_STRENGTH.strip().lower()

    class Config:
        env_file = ".env"

settings = Settings()

