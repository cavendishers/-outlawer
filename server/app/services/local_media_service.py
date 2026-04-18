import json
import logging
import re
import shutil
import subprocess
import tempfile
import urllib.request
import wave
import zipfile
from pathlib import Path

from vosk import KaldiRecognizer, Model, SetLogLevel

from app.core.config import get_settings


logger = logging.getLogger("outlawer.local_media")
SetLogLevel(-1)

VOSK_MODEL_URLS = {
    "zh": "https://alphacephei.com/vosk/models/vosk-model-small-cn-0.22.zip",
    "en": "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip",
}


def build_local_media_derivative(asset_type: str, title: str, mime_type: str, content: bytes) -> dict[str, object] | None:
    if asset_type == "image":
        text = extract_image_text(content, mime_type)
        parser_name = "local_tesseract_ocr"
    elif asset_type == "audio":
        text = extract_audio_text(content, mime_type)
        parser_name = "local_vosk_asr"
    elif asset_type == "video":
        text = extract_video_text(content, mime_type)
        parser_name = "local_video_ocr_asr"
    else:
        return None

    normalized = normalize_media_text(text)
    if not normalized:
        return None

    return {
        "canonical_text": normalized,
        "short_summary": build_local_summary(asset_type, title, normalized),
        "observed_people": [],
        "observed_events": [],
        "observed_time": extract_time_candidates(normalized),
        "observed_location": [],
        "confidence": 0.68,
        "parsing_notes": f"{parser_name} generated normalized text from the uploaded media.",
        "parser_name": parser_name,
    }


def extract_image_text(content: bytes, mime_type: str) -> str:
    settings = get_settings()
    if not shutil.which(settings.local_media_tesseract_bin):
        return ""

    suffix = guess_suffix(mime_type, "image")
    with tempfile.TemporaryDirectory(prefix="outlawer-image-") as tmpdir:
        input_path = Path(tmpdir) / f"input{suffix}"
        input_path.write_bytes(content)
        result = subprocess.run(
            [
                settings.local_media_tesseract_bin,
                str(input_path),
                "stdout",
                "-l",
                settings.local_media_tesseract_languages,
                "--psm",
                "6",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            logger.warning("local_image_ocr_failed code=%s stderr=%s", result.returncode, result.stderr.strip())
            return ""
        return result.stdout


def extract_audio_text(content: bytes, mime_type: str) -> str:
    settings = get_settings()
    if not shutil.which(settings.local_media_ffmpeg_bin):
        return ""

    with tempfile.TemporaryDirectory(prefix="outlawer-audio-") as tmpdir:
        tmp_path = Path(tmpdir)
        source_path = tmp_path / f"source{guess_suffix(mime_type, 'audio')}"
        pcm_path = tmp_path / "audio.wav"
        source_path.write_bytes(content)

        convert = subprocess.run(
            [
                settings.local_media_ffmpeg_bin,
                "-y",
                "-i",
                str(source_path),
                "-ar",
                "16000",
                "-ac",
                "1",
                "-f",
                "wav",
                str(pcm_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if convert.returncode != 0:
            logger.warning("local_audio_ffmpeg_failed code=%s stderr=%s", convert.returncode, convert.stderr.strip())
            return ""

        transcripts: list[str] = []
        for language in ("zh", "en"):
            transcript = transcribe_wave_file(pcm_path, language)
            if transcript:
                transcripts.append(transcript)
        return choose_best_transcript(transcripts)


def extract_video_text(content: bytes, mime_type: str) -> str:
    settings = get_settings()
    if not shutil.which(settings.local_media_ffmpeg_bin):
        return ""

    with tempfile.TemporaryDirectory(prefix="outlawer-video-") as tmpdir:
        tmp_path = Path(tmpdir)
        source_path = tmp_path / f"source{guess_suffix(mime_type, 'video')}"
        frames_dir = tmp_path / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)
        audio_path = tmp_path / "audio.wav"
        source_path.write_bytes(content)

        frame_extract = subprocess.run(
            [
                settings.local_media_ffmpeg_bin,
                "-y",
                "-i",
                str(source_path),
                "-vf",
                "fps=1",
                "-frames:v",
                "3",
                str(frames_dir / "frame_%02d.png"),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if frame_extract.returncode != 0:
            logger.warning("local_video_frame_extract_failed code=%s stderr=%s", frame_extract.returncode, frame_extract.stderr.strip())

        frame_texts: list[str] = []
        for frame_path in sorted(frames_dir.glob("*.png")):
            text = extract_image_text(frame_path.read_bytes(), "image/png")
            normalized = normalize_media_text(text)
            if normalized:
                frame_texts.append(normalized)

        audio_extract = subprocess.run(
            [
                settings.local_media_ffmpeg_bin,
                "-y",
                "-i",
                str(source_path),
                "-vn",
                "-ar",
                "16000",
                "-ac",
                "1",
                "-f",
                "wav",
                str(audio_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        audio_text = ""
        if audio_extract.returncode == 0 and audio_path.exists():
            audio_text = extract_audio_text(audio_path.read_bytes(), "audio/wav")

        sections: list[str] = []
        unique_frame_text = dedupe_texts(frame_texts)
        if unique_frame_text:
            sections.append("画面文字：")
            sections.append("\n".join(unique_frame_text))
        if audio_text:
            sections.append("音轨转写：")
            sections.append(audio_text)
        return "\n".join(sections).strip()


def transcribe_wave_file(path: Path, language: str) -> str:
    model_path = ensure_vosk_model(language)
    if model_path is None:
        return ""

    with wave.open(str(path), "rb") as wav_file:
        recognizer = KaldiRecognizer(Model(str(model_path)), wav_file.getframerate())
        recognizer.SetWords(True)
        parts: list[str] = []
        while True:
            chunk = wav_file.readframes(4000)
            if not chunk:
                break
            if recognizer.AcceptWaveform(chunk):
                parts.append(json.loads(recognizer.Result()).get("text", ""))
        parts.append(json.loads(recognizer.FinalResult()).get("text", ""))
    return normalize_media_text(" ".join(parts))


def ensure_vosk_model(language: str) -> Path | None:
    url = VOSK_MODEL_URLS.get(language)
    if not url:
        return None

    settings = get_settings()
    models_root = Path(settings.local_media_models_dir)
    models_root.mkdir(parents=True, exist_ok=True)
    target_dir = models_root / f"vosk-{language}"
    if (target_dir / "am").exists():
        return target_dir

    zip_path = models_root / f"vosk-{language}.zip"
    if not zip_path.exists():
        logger.info("downloading_vosk_model language=%s", language)
        urllib.request.urlretrieve(url, zip_path)

    extract_root = models_root / f"vosk-{language}-extract"
    if extract_root.exists():
        shutil.rmtree(extract_root)
    extract_root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(extract_root)

    extracted_dirs = [path for path in extract_root.iterdir() if path.is_dir()]
    if not extracted_dirs:
        return None
    extracted_dir = extracted_dirs[0]
    if target_dir.exists():
        shutil.rmtree(target_dir)
    shutil.move(str(extracted_dir), str(target_dir))
    shutil.rmtree(extract_root, ignore_errors=True)
    return target_dir


def choose_best_transcript(transcripts: list[str]) -> str:
    scored = [(score_transcript(text), text) for text in transcripts if text]
    if not scored:
        return ""
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[0][1]


def score_transcript(text: str) -> int:
    normalized = re.sub(r"\s+", "", text)
    cjk_count = len(re.findall(r"[\u4e00-\u9fff]", normalized))
    alpha_count = len(re.findall(r"[A-Za-z]", normalized))
    digit_count = len(re.findall(r"\d", normalized))
    return len(normalized) + cjk_count * 2 + alpha_count + digit_count


def normalize_media_text(text: str) -> str:
    if not text:
        return ""
    normalized = text.replace("\x0c", "\n")
    normalized = re.sub(r"\r\n?", "\n", normalized)
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    lines = [line.strip() for line in normalized.splitlines()]
    return "\n".join(line for line in lines if line).strip()


def dedupe_texts(texts: list[str]) -> list[str]:
    deduped: list[str] = []
    for text in texts:
        if text not in deduped:
            deduped.append(text)
    return deduped


def build_local_summary(asset_type: str, title: str, normalized_text: str) -> str:
    preview = normalized_text.replace("\n", " ")
    preview = preview[:96]
    return f"{title} 已完成{asset_type}本地解析，提取内容：{preview}"


def extract_time_candidates(text: str) -> list[str]:
    patterns = re.findall(r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b", text)
    deduped: list[str] = []
    for item in patterns:
        if item not in deduped:
            deduped.append(item)
    return deduped[:5]


def guess_suffix(mime_type: str, asset_type: str) -> str:
    subtype = mime_type.split("/")[-1].lower().split(";")[0]
    suffixes = {
        "png": ".png",
        "jpeg": ".jpg",
        "jpg": ".jpg",
        "webp": ".webp",
        "wav": ".wav",
        "x-wav": ".wav",
        "mpeg": ".mp3",
        "mp3": ".mp3",
        "ogg": ".ogg",
        "mp4": ".mp4",
        "quicktime": ".mov",
        "webm": ".webm",
    }
    return suffixes.get(subtype, {"image": ".png", "audio": ".wav", "video": ".mp4"}.get(asset_type, ".bin"))
