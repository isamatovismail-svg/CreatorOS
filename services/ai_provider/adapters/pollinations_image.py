import urllib.request
import urllib.parse
import os
import subprocess
import logging
from typing import Optional
from django.conf import settings
from ..base import BaseImageProvider

logger = logging.getLogger(__name__)

class PollinationsImageProvider(BaseImageProvider):
    """
    Free Image Provider utilizing Pollinations.ai API (no API key required)
    with robust local visual image rendering fallback.
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
        is_test_mode = getattr(settings, 'CREATOROS_TEST_MODE', False) or os.getenv('CREATOROS_TEST_MODE', '').lower() in ('true', '1', 't') or kwargs.get('fast_test')

        if not is_test_mode:
            encoded_prompt = urllib.parse.quote(prompt[:200])
            url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true"

            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (CreatorOS/1.0)"})
                with urllib.request.urlopen(req, timeout=10) as response:
                    content = response.read()
                    if len(content) > 1024:
                        with open(output_path, "wb") as out_file:
                            out_file.write(content)
                        logger.info(f"Generated image saved to {output_path} ({len(content)} bytes)")
                        return output_path
            except Exception as e:
                logger.warning(f"Failed to fetch image from Pollinations ({e}). Generating robust local visual background...")

        # Robust local image generator using Pillow or FFmpeg
        self._generate_local_fallback_image(output_path, width=width, height=height)
        return output_path

    def _generate_local_fallback_image(self, output_path: str, width: int = 1080, height: int = 1920):
        """Generates a valid 9:16 vertical JPEG background image locally."""
        try:
            from PIL import Image, ImageDraw
            img = Image.new('RGB', (width, height), color=(18, 24, 38))
            draw = ImageDraw.Draw(img)
            # Simple futuristic gradient-like shape
            draw.rectangle([60, 60, width - 60, height - 60], outline=(99, 102, 241), width=6)
            img.save(output_path, 'JPEG', quality=90)
            logger.info(f"Created local fallback JPEG image using Pillow at {output_path}")
            return
        except ImportError:
            pass

        # Fallback to FFmpeg single-frame render if Pillow is unavailable
        try:
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", f"color=c=0x121826:s={width}x{height}",
                "-vframes", "1",
                output_path
            ]
            subprocess.run(cmd, capture_output=True, timeout=10, check=True)
            logger.info(f"Created local fallback image using FFmpeg at {output_path}")
        except Exception as err:
            logger.error(f"Failed to generate local image via FFmpeg: {err}")
            # Ensure at least valid image bytes exist
            with open(output_path, "wb") as f:
                f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9')

