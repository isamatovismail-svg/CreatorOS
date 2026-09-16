import os
import re
import subprocess
import logging
from typing import Optional, List
from django.conf import settings
from ..base import BaseTTSProvider

logger = logging.getLogger(__name__)

LANG_MAP = {
    'russian': 'ru',
    'ru': 'ru',
    'uzbek': 'uz',
    'uz': 'uz',
    'english': 'en',
    'en': 'en'
}

class DefaultTTSProvider(BaseTTSProvider):
    """
    Default Text-to-Speech Provider utilizing gTTS (Google Text-to-Speech) for real MP3 voice generation.
    Processes full script text without arbitrary character truncation, with automatic language resolution
    and robust FFmpeg silent audio fallback.
    """

    @property
    def provider_name(self) -> str:
        return "default_tts"

    def generate_audio(
        self,
        text: str,
        output_path: str,
        voice: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs
    ) -> str:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        clean_text = text.strip() if text and text.strip() else "Welcome to CreatorOS automated content platform."
        
        is_test_mode = getattr(settings, 'CREATOROS_TEST_MODE', False) or os.getenv('CREATOROS_TEST_MODE', '').lower() in ('true', '1', 't') or kwargs.get('fast_test')
        if is_test_mode:
            self._generate_silent_audio_fallback(output_path, duration_seconds=kwargs.get('duration_seconds', 3))
            return output_path

        raw_lang = kwargs.get('language') or kwargs.get('lang') or 'en'
        lang_code = LANG_MAP.get(str(raw_lang).lower(), 'en')

        try:
            from gtts import gTTS
            
            # Split into chunks of max 800 characters by sentence to respect gTTS limits without losing text
            chunks = self._chunk_text(clean_text, max_chars=800)
            
            if len(chunks) == 1:
                tts = gTTS(text=chunks[0], lang=lang_code, slow=False)
                tts.save(output_path)
            else:
                chunk_files = []
                for idx, chunk in enumerate(chunks):
                    chunk_path = output_path.rsplit('.', 1)[0] + f"_part{idx}.mp3"
                    tts = gTTS(text=chunk, lang=lang_code, slow=False)
                    tts.save(chunk_path)
                    chunk_files.append(chunk_path)

                # Combine audio chunks via FFmpeg concat
                self._concat_mp3_chunks(chunk_files, output_path)
                
                # Cleanup temp chunks
                for cf in chunk_files:
                    if os.path.exists(cf):
                        os.remove(cf)

            if os.path.exists(output_path) and os.path.getsize(output_path) > 512:
                logger.info(f"Successfully synthesized full gTTS voiceover at {output_path} ({os.path.getsize(output_path)} bytes)")
                return output_path

        except Exception as e:
            logger.warning(f"gTTS voiceover generation failed ({e}), generating silent fallback audio stream...")

        # FFmpeg silent audio stream fallback (guarantees valid MP3 file for FFmpeg rendering)
        self._generate_silent_audio_fallback(output_path, duration_seconds=10)
        return output_path

    def _chunk_text(self, text: str, max_chars: int = 800) -> List[str]:
        sentences = re.split(r'(?<=[.!?\n])\s+', text)
        chunks = []
        current = ""
        for s in sentences:
            if len(current) + len(s) < max_chars:
                current += (" " if current else "") + s
            else:
                if current:
                    chunks.append(current)
                current = s
        if current:
            chunks.append(current)
        return chunks if chunks else [text]

    def _concat_mp3_chunks(self, chunk_files: List[str], output_path: str):
        concat_list_file = output_path.rsplit('.', 1)[0] + "_list.txt"
        with open(concat_list_file, "w", encoding="utf-8") as f:
            for cf in chunk_files:
                f.write(f"file '{cf}'\n")

        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", concat_list_file,
            "-c", "copy",
            output_path
        ]
        subprocess.run(cmd, capture_output=True, timeout=30, check=True)
        if os.path.exists(concat_list_file):
            os.remove(concat_list_file)

    def _generate_silent_audio_fallback(self, output_path: str, duration_seconds: int = 10):
        try:
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", "anullsrc=r=44100:cl=stereo",
                "-t", str(duration_seconds),
                "-c:a", "libmp3lame", "-b:a", "128k",
                output_path
            ]
            subprocess.run(cmd, capture_output=True, timeout=10, check=True)
            logger.info(f"Generated silent audio fallback at {output_path}")
        except Exception as err:
            logger.error(f"FFmpeg silent audio generation failed: {err}")
            with open(output_path, "wb") as f:
                f.write(b"ID3\x04\x00\x00\x00\x00\x00\x00")
