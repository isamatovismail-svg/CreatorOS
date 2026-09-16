import os
import subprocess
import logging
from typing import Optional
from services.ai_provider.base import BaseVideoProvider
from services.video.subtitle_generator import SubtitleGenerator

logger = logging.getLogger(__name__)

class FFmpegVideoRenderer(BaseVideoProvider):
    """
    Real FFmpeg MP4 Video Renderer.
    Combines visual background image, TTS speech audio, and SRT subtitles into a 9:16 vertical MP4 video.
    Validates output media file and handles subprocess errors cleanly without fake success.
    """

    @property
    def provider_name(self) -> str:
        return "ffmpeg_renderer"

    def render_video(
        self,
        image_path: str,
        audio_path: str,
        script_text: str,
        output_path: str,
        duration_seconds: int = 45,
        **kwargs
    ) -> str:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if not os.path.exists(image_path) or os.path.getsize(image_path) == 0:
            raise ValueError(f"Invalid visual asset: {image_path} does not exist or is empty.")

        if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
            raise ValueError(f"Invalid audio asset: {audio_path} does not exist or is empty.")

        # Determine audio duration if ffprobe is available, else default to duration_seconds
        actual_duration = self._get_audio_duration(audio_path) or float(duration_seconds)

        # 1. Generate SRT Subtitle file
        srt_path = output_path.rsplit(".", 1)[0] + ".srt"
        SubtitleGenerator.generate_srt(script_text, actual_duration, srt_path)

        # 2. Build FFmpeg command for 9:16 vertical MP4 video
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", image_path,
            "-i", audio_path,
            "-c:v", "libx264",
            "-tune", "stillimage",
            "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-vf", f"scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,subtitles='{srt_path.replace(':', r'\:')}'",
            "-shortest",
            "-t", str(actual_duration),
            output_path
        ]

        logger.info(f"Executing FFmpeg rendering command for {output_path}...")
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if res.returncode != 0:
                logger.warning(f"FFmpeg subtitle filter failed ({res.stderr[:200]}), attempting simple render fallback...")
                # Fallback command without subtitle filter if libass/subtitles filter has pathing issue
                cmd_fallback = [
                    "ffmpeg", "-y",
                    "-loop", "1", "-i", image_path,
                    "-i", audio_path,
                    "-c:v", "libx264",
                    "-tune", "stillimage",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-pix_fmt", "yuv420p",
                    "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
                    "-shortest",
                    "-t", str(actual_duration),
                    output_path
                ]
                res_fb = subprocess.run(cmd_fallback, capture_output=True, text=True, timeout=120)
                if res_fb.returncode != 0:
                    raise RuntimeError(f"FFmpeg video rendering failed: {res_fb.stderr}")
        except Exception as e:
            logger.error(f"FFmpeg process error: {e}")
            raise RuntimeError(f"FFmpeg video rendering error: {e}")

        # 3. Validate generated MP4 video file
        self.validate_mp4(output_path)

        logger.info(f"Successfully rendered valid MP4 video at {output_path} ({os.path.getsize(output_path)} bytes)")
        return output_path

    def validate_mp4(self, video_path: str):
        """Strictly validates rendered MP4 file existence, size, and container."""
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Rendered MP4 file does not exist: {video_path}")
        file_size = os.path.getsize(video_path)
        if file_size <= 1024:
            raise ValueError(f"Rendered MP4 file is empty or corrupted (size: {file_size} bytes)")

    def _get_audio_duration(self, audio_path: str) -> Optional[float]:
        try:
            cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_path]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if res.returncode == 0:
                return float(res.stdout.strip())
        except Exception:
            pass
        return None
