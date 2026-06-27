from pydantic import BaseModel
from typing import Dict, Any


class QueryResponse(BaseModel):
    obfuscated_audio_url: str
    answer_audio_url: str
    transcript: str
    answer_text: str
    metadata: Dict[str, Any]
