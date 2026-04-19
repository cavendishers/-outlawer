from app.services.local_media_service import (
    build_local_media_derivative,
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
        "app.services.local_media_service.extract_image_text",
        lambda content, mime_type: "2026-04-18 Zhang San and Li Si project launch meeting",
    )

    payload = build_local_media_derivative("image", "Launch", "image/png", b"png-bytes")

    assert payload is not None
    assert payload["parser_name"] == "local_tesseract_ocr"
    assert payload["canonical_text"] == "2026-04-18 Zhang San and Li Si project launch meeting"
    assert payload["observed_time"] == ["2026-04-18"]


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
