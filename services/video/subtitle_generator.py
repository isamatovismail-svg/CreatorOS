import os
import re
import logging
from typing import List

logger = logging.getLogger(__name__)

def format_timestamp(seconds: float) -> str:
    """Formats seconds into SRT timestamp string HH:MM:SS,mmm."""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"

class SubtitleGenerator:
    """
    Generates readable .srt subtitle files by splitting script text into chunks
    and deterministically distributing timing across total audio duration.
    """

    @classmethod
    def generate_srt(cls, script_text: str, duration_seconds: float, output_srt_path: str) -> str:
        os.makedirs(os.path.dirname(output_srt_path), exist_ok=True)

        # Split text into sentences or short clauses
        sentences = [s.strip() for s in re.split(r'[.!?\n]+', script_text) if s.strip()]
        if not sentences:
            sentences = [script_text.strip() or "CreatorOS Daily Video"]

        total_chunks = len(sentences)
        chunk_duration = max(1.5, duration_seconds / total_chunks)

        srt_blocks = []
        start_time = 0.0

        for idx, text in enumerate(sentences, start=1):
            end_time = min(duration_seconds, start_time + chunk_duration)
            start_str = format_timestamp(start_time)
            end_str = format_timestamp(end_time)

            srt_blocks.append(f"{idx}\n{start_str} --> {end_str}\n{text}\n")
            start_time = end_time

        srt_content = "\n".join(srt_blocks)
        with open(output_srt_path, "w", encoding="utf-8") as f:
            f.write(srt_content)

        logger.info(f"Generated SRT subtitles at {output_srt_path} ({total_chunks} subtitle blocks)")
        return output_srt_path
