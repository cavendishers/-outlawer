import json
import logging
import math
import re
import shutil
import struct
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
        normalized_text = normalize_media_text(text)
        image_metadata = extract_image_metadata(content, mime_type)
        observed_scene = extract_image_scene_candidates(title, normalized_text, image_metadata)
        observed_objects = extract_image_object_candidates(title, normalized_text)
        observed_actions = extract_image_action_candidates(title, normalized_text)
        document_type = infer_image_document_type(title, normalized_text, image_metadata)
        image_layout = build_image_layout_label(image_metadata)
        source_attribution = build_source_attribution_from_text(
            source_type="image_ocr",
            label="image_ocr",
            text=normalized_text,
            confidence=0.66,
        )
        source_attribution.extend(
            build_source_attribution_from_text(
                source_type="image_scene_inference",
                label="image_semantic_hint",
                text=build_image_semantic_hint(
                    document_type=document_type,
                    image_layout=image_layout,
                    observed_scene=observed_scene,
                    observed_objects=observed_objects,
                    observed_actions=observed_actions,
                ),
                confidence=0.42,
                evidence_type="model_inference",
            )
        )
        text = build_image_semantic_canonical_text(
            normalized_text=normalized_text,
            document_type=document_type,
            image_layout=image_layout,
            observed_scene=observed_scene,
            observed_objects=observed_objects,
            observed_actions=observed_actions,
        )
        parser_name = "local_tesseract_ocr"
    elif asset_type == "audio":
        text = extract_audio_text(content, mime_type)
        normalized_text = normalize_media_text(text)
        source_attribution = build_source_attribution_from_text(
            source_type="audio_transcript",
            label="audio_transcript",
            text=normalized_text,
            confidence=0.68,
        )
        parser_name = "local_vosk_asr"
        observed_scene = []
        observed_objects = []
        observed_actions = []
        document_type = None
        image_layout = None
    elif asset_type == "video":
        video_observation = extract_video_observations(content, mime_type)
        text = str(video_observation.get("text") or "")
        source_attribution = list(video_observation.get("source_attribution") or [])
        video_scene_segments = list(video_observation.get("video_scene_segments") or [])
        parser_name = "local_video_ocr_asr"
        observed_scene = []
        observed_objects = []
        observed_actions = []
        document_type = None
        image_layout = None
    else:
        return None

    normalized = normalize_media_text(text)
    if not normalized:
        return None

    return {
        "canonical_text": normalized,
        "short_summary": build_local_summary(asset_type, title, normalized),
        "observed_people": extract_people_candidates(normalized),
        "observed_events": extract_event_candidates(normalized),
        "observed_time": extract_time_candidates(normalized),
        "observed_location": extract_location_candidates(normalized),
        "observed_scene": observed_scene,
        "observed_objects": observed_objects,
        "observed_actions": observed_actions,
        "document_type": document_type,
        "image_layout": image_layout,
        "confidence": 0.68,
        "parsing_notes": f"{parser_name} generated normalized text from the uploaded media.",
        "parser_name": parser_name,
        "source_attribution": source_attribution,
        "video_scene_segments": video_scene_segments if asset_type == "video" else [],
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


def extract_video_observations(content: bytes, mime_type: str) -> dict[str, object]:
    settings = get_settings()
    if not shutil.which(settings.local_media_ffmpeg_bin):
        return {"text": "", "source_attribution": []}

    with tempfile.TemporaryDirectory(prefix="outlawer-video-") as tmpdir:
        tmp_path = Path(tmpdir)
        source_path = tmp_path / f"source{guess_suffix(mime_type, 'video')}"
        frames_dir = tmp_path / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)
        audio_path = tmp_path / "audio.wav"
        source_path.write_bytes(content)
        duration_seconds = probe_media_duration_seconds(source_path, settings.local_media_ffmpeg_bin)
        frame_interval_seconds = choose_video_frame_interval(duration_seconds)
        max_frames = choose_video_frame_limit(duration_seconds)

        frame_extract = subprocess.run(
            [
                settings.local_media_ffmpeg_bin,
                "-y",
                "-i",
                str(source_path),
                "-vf",
                f"fps=1/{frame_interval_seconds}",
                "-frames:v",
                str(max_frames),
                str(frames_dir / "frame_%02d.png"),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if frame_extract.returncode != 0:
            logger.warning("local_video_frame_extract_failed code=%s stderr=%s", frame_extract.returncode, frame_extract.stderr.strip())

        frame_texts: list[str] = []
        source_attribution: list[dict[str, object]] = []
        video_scene_segments: list[dict[str, object]] = []
        for index, frame_path in enumerate(sorted(frames_dir.glob("*.png"))):
            text = extract_image_text(frame_path.read_bytes(), "image/png")
            normalized = normalize_media_text(text)
            start_seconds = index * frame_interval_seconds
            end_seconds = start_seconds + frame_interval_seconds
            if normalized:
                frame_texts.append(normalized)
                label = f"scene_{index + 1:02d}"
                source_attribution.extend(
                    build_source_attribution_from_text(
                        source_type="video_frame_ocr",
                        label=label,
                        text=normalized,
                        confidence=0.6,
                        timecode=format_timecode(start_seconds),
                    )
                )
                video_scene_segments.append(
                    {
                        "segment_index": index + 1,
                        "start_timecode": format_timecode(start_seconds),
                        "end_timecode": format_timecode(end_seconds),
                        "frame_label": label,
                        "ocr_text": normalized,
                        "confidence": 0.6,
                        "evidence_type": "direct_observation",
                    }
                )

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
            source_attribution.extend(
                build_source_attribution_from_text(
                    source_type="video_audio_transcript",
                    label="audio_track",
                    text=audio_text,
                    confidence=0.7,
                    timecode=format_timecode(0),
                )
            )

        sections: list[str] = []
        unique_frame_text = dedupe_texts(frame_texts)
        if unique_frame_text:
            sections.append("画面文字：")
            sections.append("\n".join(unique_frame_text))
        if audio_text:
            sections.append("音轨转写：")
            sections.append(audio_text)
        return {
            "text": "\n".join(sections).strip(),
            "source_attribution": source_attribution,
            "video_scene_segments": video_scene_segments,
        }


def extract_video_text(content: bytes, mime_type: str) -> str:
    return str(extract_video_observations(content, mime_type).get("text") or "")


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


def extract_people_candidates(text: str) -> list[str]:
    candidates: list[str] = []
    for match in re.finditer(r"([\u4e00-\u9fff]{2,4})和([\u4e00-\u9fff]{2,4})", text):
        candidates.extend([match.group(1), match.group(2)])
    for match in re.finditer(r"([\u4e00-\u9fff]{2,4})(?=在|于|参加|提出|记录|讨论|发言|确认|汇报)", text):
        candidates.append(match.group(1))
    for match in re.finditer(r"[A-Z][a-z]+(?:\s[A-Z][a-z]+){0,2}", text):
        candidates.append(match.group(0))
    return dedupe_named_items(candidates, min_length=2, max_items=5)


def extract_location_candidates(text: str) -> list[str]:
    candidates = re.findall(r"(?:在|于)([\u4e00-\u9fffA-Za-z0-9\-]{2,16}(?:会议室|办公室|教室|实验室|大厅|会场|园区|大厦|中心|车站|酒店|学校|医院|楼|室))", text)
    return dedupe_named_items(candidates, min_length=2, max_items=5)


def extract_event_candidates(text: str) -> list[str]:
    keywords = ["启动会", "项目启动会议", "会议", "讨论", "复盘", "汇报", "培训", "演讲", "采访", "发布会"]
    hits = [keyword for keyword in keywords if keyword in text]
    return dedupe_named_items(hits, min_length=2, max_items=5)


def build_source_attribution_from_text(
    *,
    source_type: str,
    label: str,
    text: str,
    confidence: float,
    timecode: str | None = None,
    evidence_type: str = "direct_observation",
) -> list[dict[str, object]]:
    normalized = normalize_media_text(text)
    if not normalized:
        return []
    return [
        {
            "source_type": source_type,
            "label": label,
            "timecode": timecode,
            "text": normalized,
            "confidence": confidence,
            "evidence_type": evidence_type,
        }
    ]


def extract_image_metadata(content: bytes, mime_type: str) -> dict[str, int | str | None]:
    width, height = probe_image_dimensions(content, mime_type)
    return {
        "width": width,
        "height": height,
        "orientation": infer_image_orientation(width, height),
    }


def probe_image_dimensions(content: bytes, mime_type: str) -> tuple[int | None, int | None]:
    try:
        if mime_type == "image/png" and content[:8] == b"\x89PNG\r\n\x1a\n":
            width, height = struct.unpack(">II", content[16:24])
            return int(width), int(height)
        if mime_type == "image/gif" and content[:6] in {b"GIF87a", b"GIF89a"}:
            width, height = struct.unpack("<HH", content[6:10])
            return int(width), int(height)
        if mime_type in {"image/jpeg", "image/jpg"} or content[:2] == b"\xff\xd8":
            return parse_jpeg_dimensions(content)
        if mime_type == "image/webp" and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
            return parse_webp_dimensions(content)
    except Exception:  # noqa: BLE001
        logger.warning("local_image_metadata_probe_failed mime_type=%s", mime_type)
    return None, None


def parse_jpeg_dimensions(content: bytes) -> tuple[int | None, int | None]:
    index = 2
    content_length = len(content)
    while index + 9 < content_length:
        if content[index] != 0xFF:
            index += 1
            continue
        marker = content[index + 1]
        if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
            height = struct.unpack(">H", content[index + 5 : index + 7])[0]
            width = struct.unpack(">H", content[index + 7 : index + 9])[0]
            return int(width), int(height)
        block_length = struct.unpack(">H", content[index + 2 : index + 4])[0]
        if block_length <= 0:
            break
        index += 2 + block_length
    return None, None


def parse_webp_dimensions(content: bytes) -> tuple[int | None, int | None]:
    if len(content) < 30:
        return None, None
    chunk_header = content[12:16]
    if chunk_header == b"VP8 " and len(content) >= 30:
        width = struct.unpack("<H", content[26:28])[0] & 0x3FFF
        height = struct.unpack("<H", content[28:30])[0] & 0x3FFF
        return int(width), int(height)
    if chunk_header == b"VP8L" and len(content) >= 25:
        bits = struct.unpack("<I", content[21:25])[0]
        width = (bits & 0x3FFF) + 1
        height = ((bits >> 14) & 0x3FFF) + 1
        return int(width), int(height)
    if chunk_header == b"VP8X" and len(content) >= 30:
        width = 1 + int.from_bytes(content[24:27], "little")
        height = 1 + int.from_bytes(content[27:30], "little")
        return width, height
    return None, None


def infer_image_orientation(width: int | None, height: int | None) -> str | None:
    if not width or not height:
        return None
    if width == height:
        return "square"
    if width > height:
        return "landscape"
    return "portrait"


def build_image_layout_label(metadata: dict[str, int | str | None]) -> str | None:
    width = metadata.get("width")
    height = metadata.get("height")
    orientation = str(metadata.get("orientation") or "").strip()
    if not isinstance(width, int) or not isinstance(height, int):
        return None
    orientation_labels = {
        "landscape": "横向",
        "portrait": "纵向",
        "square": "方形",
    }
    prefix = orientation_labels.get(orientation, "未知布局")
    return f"{prefix} {width}x{height}"


def infer_image_document_type(title: str, text: str, metadata: dict[str, int | str | None]) -> str | None:
    haystack = f"{title}\n{text}".lower()
    if any(keyword in haystack for keyword in ["截图", "screenshot", "screen", "界面", "页面"]):
        return "界面截图"
    if any(keyword in haystack for keyword in ["白板", "投影", "幻灯", "slide", "ppt"]):
        return "会议现场照片"
    if any(keyword in haystack for keyword in ["文档", "报告", "方案", "清单", "合同", "通知", "表格"]):
        return "文档页"
    if any(keyword in haystack for keyword in ["海报", "poster", "展板"]):
        return "海报或展板"
    if any(keyword in haystack for keyword in ["照片", "photo", "现场", "合影"]):
        return "现场照片"
    if metadata.get("orientation") == "portrait":
        return "纵向图片"
    if metadata.get("orientation") == "landscape":
        return "横向图片"
    return None


def extract_image_scene_candidates(title: str, text: str, metadata: dict[str, int | str | None]) -> list[str]:
    haystack = f"{title}\n{text}"
    candidates: list[str] = []
    if any(keyword in haystack for keyword in ["会议", "启动会", "讨论", "复盘", "汇报"]):
        candidates.append("会议现场")
    if any(keyword in haystack for keyword in ["白板", "板书"]):
        candidates.append("白板讨论")
    if any(keyword in haystack for keyword in ["投影", "幻灯", "PPT", "ppt", "slide"]):
        candidates.append("投影演示")
    if any(keyword in haystack for keyword in ["截图", "界面", "页面", "按钮"]):
        candidates.append("软件界面")
    if not candidates and metadata.get("orientation") == "portrait":
        candidates.append("纵向图像")
    if not candidates and metadata.get("orientation") == "landscape":
        candidates.append("横向图像")
    return dedupe_named_items(candidates, min_length=2, max_items=5)


def extract_image_object_candidates(title: str, text: str) -> list[str]:
    haystack = f"{title}\n{text}"
    keyword_map = {
        "白板": "白板",
        "投影": "投影幕布",
        "幻灯": "投影幕布",
        "PPT": "演示文稿",
        "ppt": "演示文稿",
        "slide": "演示文稿",
        "图表": "图表",
        "表格": "表格",
        "文档": "文档页",
        "报告": "文档页",
        "页面": "界面面板",
        "按钮": "界面控件",
        "会议室": "会议空间",
    }
    candidates = [label for keyword, label in keyword_map.items() if keyword in haystack]
    return dedupe_named_items(candidates, min_length=2, max_items=6)


def extract_image_action_candidates(title: str, text: str) -> list[str]:
    haystack = f"{title}\n{text}"
    keyword_map = {
        "讨论": "讨论",
        "汇报": "汇报",
        "讲解": "讲解",
        "演示": "演示",
        "记录": "记录",
        "复盘": "复盘",
        "确认": "确认",
        "规划": "规划",
        "启动": "启动准备",
    }
    candidates = [label for keyword, label in keyword_map.items() if keyword in haystack]
    return dedupe_named_items(candidates, min_length=2, max_items=6)


def build_image_semantic_hint(
    *,
    document_type: str | None,
    image_layout: str | None,
    observed_scene: list[str],
    observed_objects: list[str],
    observed_actions: list[str],
) -> str:
    parts: list[str] = []
    if document_type:
        parts.append(f"图像类型推断为{document_type}")
    if image_layout:
        parts.append(f"布局为{image_layout}")
    if observed_scene:
        parts.append(f"可能场景：{'、'.join(observed_scene)}")
    if observed_objects:
        parts.append(f"可见元素：{'、'.join(observed_objects)}")
    if observed_actions:
        parts.append(f"可能行为：{'、'.join(observed_actions)}")
    return "；".join(parts)


def build_image_semantic_canonical_text(
    *,
    normalized_text: str,
    document_type: str | None,
    image_layout: str | None,
    observed_scene: list[str],
    observed_objects: list[str],
    observed_actions: list[str],
) -> str:
    sections: list[str] = []
    if normalized_text:
        sections.append("画面文字：")
        sections.append(normalized_text)
    semantic_hint = build_image_semantic_hint(
        document_type=document_type,
        image_layout=image_layout,
        observed_scene=observed_scene,
        observed_objects=observed_objects,
        observed_actions=observed_actions,
    )
    if semantic_hint:
        sections.append("图像语义提示：")
        sections.append(semantic_hint)
    return "\n".join(sections).strip()


def probe_media_duration_seconds(source_path: Path, ffmpeg_bin: str) -> int | None:
    ffprobe_bin = resolve_ffprobe_bin(ffmpeg_bin)
    if not ffprobe_bin:
        return None
    result = subprocess.run(
        [
            ffprobe_bin,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(source_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        logger.warning("local_video_duration_probe_failed code=%s stderr=%s", result.returncode, result.stderr.strip())
        return None
    try:
        duration = float(result.stdout.strip())
    except ValueError:
        return None
    if duration <= 0:
        return None
    return int(math.ceil(duration))


def resolve_ffprobe_bin(ffmpeg_bin: str) -> str | None:
    ffprobe_candidate = str(Path(ffmpeg_bin).with_name("ffprobe")) if "/" in ffmpeg_bin else "ffprobe"
    if shutil.which(ffprobe_candidate):
        return ffprobe_candidate
    return shutil.which("ffprobe")


def choose_video_frame_interval(duration_seconds: int | None) -> int:
    if duration_seconds is None:
        return 3
    if duration_seconds <= 18:
        return 3
    if duration_seconds <= 60:
        return 6
    if duration_seconds <= 180:
        return 12
    return max(15, math.ceil(duration_seconds / 8))


def choose_video_frame_limit(duration_seconds: int | None) -> int:
    if duration_seconds is None:
        return 6
    if duration_seconds <= 18:
        return 6
    return 8


def dedupe_named_items(items: list[str], *, min_length: int, max_items: int) -> list[str]:
    deduped: list[str] = []
    for item in items:
        cleaned = normalize_media_text(item).replace("\n", " ")
        if len(cleaned) < min_length or cleaned in deduped:
            continue
        deduped.append(cleaned)
        if len(deduped) >= max_items:
            break
    return deduped


def format_timecode(total_seconds: int) -> str:
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


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
