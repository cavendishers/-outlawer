from app.domains.extraction.local_media import (
    build_local_media_derivative,
    build_audio_segments_from_words,
    build_source_attribution_from_text,
    choose_best_transcript,
    choose_video_frame_interval,
    choose_video_frame_limit,
    extract_time_candidates,
    format_timecode,
    normalize_media_text,
)


def test_normalize_media_text_collapses_noise() -> None:
    text = "  2026-04-18   Zhang San \n\n\n Li Si \x0c"

    assert normalize_media_text(text) == "2026-04-18 Zhang San\nLi Si"


def test_choose_best_transcript_prefers_more_complete_result() -> None:
    transcripts = [
        "",
        "johnson and he",
        "zhang san and li si held the project launch meeting in room a",
    ]

    assert choose_best_transcript(transcripts) == transcripts[2]


def test_extract_time_candidates_dedupes_dates() -> None:
    text = "2026-04-18 Zhang San met Li Si. 2026-04-18 was the project launch day."

    assert extract_time_candidates(text) == ["2026-04-18"]


def test_build_local_media_derivative_uses_local_parser_payload(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.domains.extraction.local_media.extract_image_text",
        lambda content, mime_type: "2026-04-18 Zhang San and Li Si project launch meeting",
    )

    payload = build_local_media_derivative("image", "Launch", "image/png", b"png-bytes")

    assert payload is not None
    assert payload["parser_name"] == "local_tesseract_ocr"
    assert "画面文字：" in payload["canonical_text"]
    assert "2026-04-18 Zhang San and Li Si project launch meeting" in payload["canonical_text"]
    assert payload["observed_time"] == ["2026-04-18"]


def test_build_local_media_derivative_generates_image_semantics_without_ocr(monkeypatch) -> None:
    monkeypatch.setattr("app.domains.extraction.local_media.extract_image_text", lambda content, mime_type: "")

    png_bytes = (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x10\x00\x00\x00\x08\x08\x02\x00\x00\x00"
        b"\x00\x00\x00\x00"
    )
    payload = build_local_media_derivative("image", "项目启动会白板讨论照片", "image/png", png_bytes)

    assert payload is not None
    assert payload["document_type"] == "会议现场照片"
    assert payload["image_layout"] == "横向 16x8"
    assert "会议现场" in payload["observed_scene"]
    assert "白板" in payload["observed_objects"]
    assert "讨论" in payload["observed_actions"]
    assert "图像语义提示：" in payload["canonical_text"]


def test_build_audio_segments_from_words_groups_words_by_pause() -> None:
    segments = build_audio_segments_from_words(
        [
            {"word": "项目", "start": 0.1, "end": 0.3},
            {"word": "启动", "start": 0.31, "end": 0.6},
            {"word": "会议", "start": 0.61, "end": 0.9},
            {"word": "后续", "start": 3.0, "end": 3.2},
            {"word": "待办", "start": 3.21, "end": 3.5},
        ]
    )

    assert len(segments) == 2
    assert segments[0]["transcript"] == "项目 启动 会议"
    assert segments[1]["transcript"] == "后续 待办"


def test_build_local_media_derivative_generates_audio_context_without_transcript(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.domains.extraction.local_media.extract_audio_observations",
        lambda content, mime_type, title="": {
            "text": "",
            "audio_segments": [],
            "speaker_hints": [],
            "observed_topics": ["项目启动", "后续待办"],
            "observed_decisions": [],
            "observed_follow_ups": ["后续跟进导入流程"],
            "conversation_type": "会议讨论",
        },
    )

    payload = build_local_media_derivative("audio", "项目启动会议后续待办录音", "audio/wav", b"wav-bytes")

    assert payload is not None
    assert payload["conversation_type"] == "会议讨论"
    assert payload["observed_topics"] == ["项目启动", "后续待办"]
    assert payload["observed_follow_ups"] == ["后续跟进导入流程"]
    assert "音频上下文提示：" in payload["canonical_text"]


def test_video_sampling_scales_with_duration() -> None:
    assert choose_video_frame_interval(None) == 3
    assert choose_video_frame_interval(12) == 3
    assert choose_video_frame_interval(45) == 6
    assert choose_video_frame_interval(120) == 12
    assert choose_video_frame_interval(600) == 75

    assert choose_video_frame_limit(None) == 6
    assert choose_video_frame_limit(12) == 6
    assert choose_video_frame_limit(45) == 8


def test_source_attribution_marks_direct_evidence_by_default() -> None:
    attribution = build_source_attribution_from_text(
        source_type="video_frame_ocr",
        label="scene_01",
        timecode="00:00:03",
        text=" 项目启动会 2026-04-18\n",
        confidence=0.6,
    )

    assert attribution == [
        {
            "source_type": "video_frame_ocr",
            "label": "scene_01",
            "timecode": "00:00:03",
            "text": "项目启动会 2026-04-18",
            "confidence": 0.6,
            "evidence_type": "direct_observation",
        }
    ]


def test_format_timecode_uses_hh_mm_ss() -> None:
    assert format_timecode(0) == "00:00:00"
    assert format_timecode(65) == "00:01:05"
    assert format_timecode(3661) == "01:01:01"
