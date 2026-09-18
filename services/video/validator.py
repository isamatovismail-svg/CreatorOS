import os
import json
import subprocess
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class VideoValidationError(Exception):
    """Raised when generated video file fails strict format and stream validation."""
    pass

def validate_video_file(file_path: str, min_duration: float = 1.0) -> Dict[str, Any]:
    """
    Performs rigorous automated inspection and validation of generated MP4 video files.
    Ensures file exists, size > 0, valid MP4 container, video stream present, audio stream present,
    valid duration, and clean FFprobe execution.
    """
    if not file_path:
        raise VideoValidationError("Validation failed: Media file path is empty.")

    if not os.path.exists(file_path):
        raise VideoValidationError(f"Validation failed: Video file does not exist at '{file_path}'.")

    file_size = os.path.getsize(file_path)
    if file_size <= 0:
        raise VideoValidationError(f"Validation failed: Video file size is 0 bytes at '{file_path}'.")

    # Run ffprobe inspector command
    ffprobe_cmd = [
        'ffprobe',
        '-v', 'quiet',
        '-print_format', 'json',
        '-show_format',
        '-show_streams',
        file_path
    ]

    try:
        result = subprocess.run(ffprobe_cmd, capture_output=True, text=True, check=True)
        probe_data = json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        raise VideoValidationError(f"Validation failed: FFprobe container inspection failed: {e.stderr}")
    except Exception as e:
        raise VideoValidationError(f"Validation failed: FFprobe JSON parse error: {e}")

    format_info = probe_data.get('format', {})
    streams = probe_data.get('streams', [])

    # 1. Container format check
    format_name = format_info.get('format_name', '')
    if 'mp4' not in format_name and 'mov' not in format_name and 'matroska' not in format_name:
        raise VideoValidationError(f"Validation failed: Unsupported format '{format_name}'. Expected MP4/MOV container.")

    # 2. Stream presence checks
    video_streams = [s for s in streams if s.get('codec_type') == 'video']
    audio_streams = [s for s in streams if s.get('codec_type') == 'audio']

    if not video_streams:
        raise VideoValidationError("Validation failed: No video stream found in MP4 file.")

    if not audio_streams:
        raise VideoValidationError("Validation failed: No audio stream found in MP4 file.")

    video_stream = video_streams[0]
    width = int(video_stream.get('width', 0))
    height = int(video_stream.get('height', 0))

    if width <= 0 or height <= 0:
        raise VideoValidationError(f"Validation failed: Invalid resolution ({width}x{height}).")

    # 3. Duration check
    duration = float(format_info.get('duration', 0.0))
    if duration < min_duration:
        raise VideoValidationError(f"Validation failed: Video duration ({duration:.2f}s) is less than minimum {min_duration}s.")

    logger.info(
        f"✅ Video Validation Passed: {file_path} "
        f"({width}x{height}, {duration:.1f}s, size: {file_size} bytes, video: {video_stream.get('codec_name')}, audio: {len(audio_streams)} stream(s))"
    )

    return {
        'valid': True,
        'file_path': file_path,
        'file_size': file_size,
        'width': width,
        'height': height,
        'duration': duration,
        'video_codec': video_stream.get('codec_name'),
        'has_audio': len(audio_streams) > 0
    }
