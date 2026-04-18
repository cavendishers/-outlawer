from app.services.local_media_service import (
    build_local_media_derivative,
    choose_best_transcript,
    extract_time_candidates,
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
