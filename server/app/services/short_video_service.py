"""Short video generation service.

Creates short music videos by:
1. Downloading the program's original video from cloud storage
2. Randomly selecting a music from the music library
3. Cutting the video to match the music beats (using librosa + moviepy)
4. Limiting the output to a configurable duration (default 15s)
5. Uploading the result back to cloud storage
"""

import os
import random
import tempfile
import logging
import asyncio
from functools import partial
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


def _reverse_time_transform(original_duration: float, fps: float, t: float) -> float:
    return max(0, min(original_duration - t - 1 / fps, original_duration - 1 / fps))


def _analyze_beats(audio_path: str, start_time: float = 0.0, end_time: Optional[float] = None):
    """Analyze bass beats in an audio file using librosa."""
    import librosa

    duration = None
    if end_time and end_time > start_time:
        duration = end_time - start_time

    y, sr = librosa.load(audio_path, sr=22050, offset=start_time, duration=duration)

    # Create bass-focused onset envelope
    stft = librosa.stft(y)
    freqs = librosa.fft_frequencies(sr=sr)
    bass_band = (freqs >= 20) & (freqs <= 200)
    bass_onset_env = np.sum(np.abs(stft[bass_band, :]), axis=0)

    # Beat tracking with bass envelope
    try:
        tempo, beat_frames = librosa.beat.beat_track(
            onset_envelope=bass_onset_env, sr=sr, units="frames"
        )
    except TypeError:
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, units="frames")

    if tempo.size > 0:
        logger.info(f"Detected tempo: {tempo[0]:.2f} BPM")
    else:
        logger.warning("Could not detect tempo")
        return np.array([])

    beat_times = librosa.frames_to_time(beat_frames, sr=sr, hop_length=512)
    logger.info(f"Detected {len(beat_times)} beats")
    return beat_times


def _create_short_video(
    video_path: str,
    music_path: str,
    output_path: str,
    target_duration: float = 15.0,
    cut_intensity: int = 2,
    direction: str = "random",
) -> str:
    """Create a short music video from a source video and music file."""
    from moviepy import AudioFileClip, VideoFileClip, concatenate_videoclips
    from moviepy.video.fx.MultiplySpeed import MultiplySpeed

    # Analyze beats
    beat_times = _analyze_beats(music_path, start_time=0.0, end_time=target_duration)

    if len(beat_times) == 0:
        raise ValueError("No beats detected in the music file")

    # Load and trim audio
    full_audio = AudioFileClip(music_path)
    audio = full_audio.subclipped(0, min(target_duration, full_audio.duration))
    audio_duration = audio.duration

    # Select beats based on cut_intensity
    selected_beats = beat_times[::cut_intensity]

    # Ensure beats start at 0 and end at audio_duration
    if len(selected_beats) == 0 or selected_beats[0] > 0.1:
        selected_beats = np.insert(selected_beats, 0, 0)
    if selected_beats[-1] < audio_duration:
        selected_beats = np.append(selected_beats, audio_duration)

    # Filter beats to audio duration range
    selected_beats = selected_beats[selected_beats <= audio_duration]
    if selected_beats[-1] < audio_duration:
        selected_beats = np.append(selected_beats, audio_duration)

    # Build clips from source video
    clips = []
    videos_to_close = []
    target_size = None

    video = VideoFileClip(video_path)
    videos_to_close.append(video)

    for i in range(len(selected_beats) - 1):
        final_duration = selected_beats[i + 1] - selected_beats[i]

        # Extract a random clip from the source video
        if video.duration >= final_duration:
            max_start = video.duration - final_duration
            clip_start = random.uniform(0, max_start)
            clip = video.subclipped(clip_start, clip_start + final_duration)
        else:
            # If video is shorter than needed, loop or use full video
            clip = video.subclipped(0, video.duration)

        # Apply direction effect
        if direction == "backward":
            original_duration = clip.duration
            reverse_func = partial(
                _reverse_time_transform, original_duration, clip.fps
            )
            clip = clip.time_transform(reverse_func)
            clip = clip.with_duration(original_duration)
        elif direction == "random":
            if random.choice([True, False]):
                original_duration = clip.duration
                reverse_func = partial(
                    _reverse_time_transform, original_duration, clip.fps
                )
                clip = clip.time_transform(reverse_func)
                clip = clip.with_duration(original_duration)

        # Resize to uniform size
        if i == 0:
            target_size = clip.size
        if target_size and clip.size != target_size:
            clip = clip.resized(target_size)

        clips.append(clip)

    if not clips:
        raise ValueError("No valid video clips could be created")

    # Concatenate clips and add audio
    final_video = concatenate_videoclips(clips)
    final_video = final_video.with_audio(audio)
    final_video = final_video.subclipped(0, min(audio_duration, final_video.duration))

    # Write output
    final_video.write_videofile(
        output_path,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile=os.path.join(os.path.dirname(output_path), "temp-audio.m4a"),
        remove_temp=True,
        logger=None,
    )

    # Cleanup
    final_video.close()
    audio.close()
    full_audio.close()
    for v in videos_to_close:
        v.close()

    return output_path


async def generate_short_video_for_program(
    program_id: int,
    target_duration: float = 15.0,
    cut_intensity: int = 2,
    direction: str = "random",
    music_id: Optional[int] = None,
):
    """Generate a short video for a program. Runs in background."""
    from app.database import SessionLocal
    from app.models import Program, Music
    from app.services.storage_service import get_storage_service
    from app.api.upload import _move_to_temp

    db = SessionLocal()
    temp_dir = tempfile.mkdtemp()

    try:
        program = db.query(Program).filter(Program.id == program_id).first()
        if not program:
            logger.error(f"Program {program_id} not found")
            return

        if not program.video_url:
            program.short_video_status = "failed"
            db.commit()
            logger.error(f"Program {program_id} has no video")
            return

        # Select random music (or specific one)
        if music_id:
            music = db.query(Music).filter(Music.id == music_id).first()
        else:
            musics = db.query(Music).all()
            if not musics:
                program.short_video_status = "failed"
                db.commit()
                logger.error("No music in library")
                return
            music = random.choice(musics)

        if not music or not music.storage_url:
            program.short_video_status = "failed"
            db.commit()
            logger.error("No valid music found")
            return

        # Mark as generating
        program.short_video_status = "generating"
        db.commit()

        storage = get_storage_service()

        # Download video and music to temp files
        import aiohttp

        video_path = os.path.join(temp_dir, "source_video.mp4")
        music_path = os.path.join(temp_dir, "source_music.mp3")
        output_path = os.path.join(temp_dir, "output_short.mp4")

        async with aiohttp.ClientSession() as session:
            # Download video
            async with session.get(program.video_url) as resp:
                if resp.status != 200:
                    raise Exception(f"Failed to download video: {resp.status}")
                with open(video_path, "wb") as f:
                    f.write(await resp.read())

            # Download music
            async with session.get(music.storage_url) as resp:
                if resp.status != 200:
                    raise Exception(f"Failed to download music: {resp.status}")
                with open(music_path, "wb") as f:
                    f.write(await resp.read())

        # Run video generation in thread pool (CPU-intensive)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: _create_short_video(
                video_path,
                music_path,
                output_path,
                target_duration=target_duration,
                cut_intensity=cut_intensity,
                direction=direction,
            ),
        )

        # Upload result to cloud storage
        with open(output_path, "rb") as f:
            content = f.read()

        import uuid

        storage_key = f"short-videos/{uuid.uuid4().hex}.mp4"
        storage_url = await storage.upload_file(content, storage_key)

        # Delete old short video
        if program.short_video_url:
            await _move_to_temp(program.short_video_url)

        # Update program
        program.short_video_url = storage_url
        program.short_video_status = "ready"
        db.commit()

        logger.info(f"Short video generated for program {program_id}: {storage_url}")

    except Exception as e:
        logger.error(f"Failed to generate short video for program {program_id}: {e}")
        try:
            program = db.query(Program).filter(Program.id == program_id).first()
            if program:
                program.short_video_status = "failed"
                db.commit()
        except Exception:
            pass

    finally:
        # Cleanup temp files
        import shutil

        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass
        db.close()
