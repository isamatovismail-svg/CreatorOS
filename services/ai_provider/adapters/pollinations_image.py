import urllib.request
import urllib.parse
import os
import logging
from typing import Optional
from ..base import BaseImageProvider

logger = logging.getLogger(__name__)

class PollinationsImageProvider(BaseImageProvider):
    """
    Free Image Provider utilizing Pollinations.ai API (no API key required).
    """

    @property
    def provider_name(self) -> str:
        return "pollinations"

    def generate_image(
        self,
        prompt: str,
        output_path: str,
        width: int = 1080,
        height: int = 1920,
        api_key: Optional[str] = None,
        **kwargs
    ) -> str:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        encoded_prompt = urllib.parse.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true"

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "CreatorOS/1.0"})
            with urllib.request.urlopen(req, timeout=20) as response, open(output_path, "wb") as out_file:
                out_file.write(response.read())
            logger.info(f"Generated image saved to {output_path}")
        except Exception as e:
            logger.error(f"Failed to fetch image from Pollinations: {e}")
            # Create a basic fallback file if request fails
            with open(output_path, "wb") as out_file:
                out_file.write(b"")

        return output_path
