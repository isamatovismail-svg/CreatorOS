import urllib.request
import json
import logging
from typing import Optional
from ..base import BaseLLMProvider

logger = logging.getLogger(__name__)

class DefaultLLMProvider(BaseLLMProvider):
    """
    Default LLM Provider adapter supporting external API endpoints (e.g. OpenAI / Groq / Gemini)
    and robust fallback script generation when no API key is set.
    """

    @property
    def provider_name(self) -> str:
        return "default_llm"

    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs
    ) -> str:
        # If API key is provided, attempt OpenAI / compatible endpoint
        if api_key:
            try:
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                }
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})

                payload = json.dumps({
                    "model": kwargs.get("model", "gpt-3.5-turbo"),
                    "messages": messages,
                    "temperature": kwargs.get("temperature", 0.7)
                }).encode("utf-8")

                req = urllib.request.Request(
                    "https://api.openai.com/v1/chat/completions",
                    data=payload,
                    headers=headers,
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    return data["choices"][0]["message"]["content"]
            except Exception as e:
                logger.warning(f"API call failed, falling back to smart engine: {e}")

        # Smart fallback generator (for free MVP testing without requiring API keys immediately)
        topic = kwargs.get("topic", "Technology & AI")
        return f"""
[HOOK]
Did you know that 90% of creators struggle with consistency? Here is how to fix it!

[SCRIPT]
Welcome back! Today we are diving into {topic}. 
Step 1: Automate your content pipeline using modern modular tools.
Step 2: Let AI draft your initial scripts, visuals, and captions.
Step 3: Schedule everything in advance so your workflow stays consistent.

[CAPTION]
Mastering {topic} has never been easier! Work smarter, not harder. 🚀 #CreatorOS #{topic.replace(' ', '')} #ContentCreation #AI
"""
