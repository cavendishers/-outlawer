from app.models.raw_asset import RawAsset
from app.services.asset_text_service import (
    build_multimodal_canonical_text,
    build_multimodal_fallback_text,
    normalize_multimodal_list,
)


def test_build_multimodal_canonical_text_includes_core_sections() -> None:
    asset = RawAsset(
        id="asset-1",
        user_id="user-1",
        asset_type="image",
        source_type="manual",
        title="白板会议照片",
        status="uploaded",
    )

    text = build_multimodal_canonical_text(
        asset,
        {
            "canonical_text": "张三和李四站在白板前讨论图谱拆分。",
            "short_summary": "会议内容被拍摄记录。",
            "observed_people": ["张三", "李四"],
            "observed_time": ["2026-04-18"],
            "observed_location": ["会议室A"],
            "parsing_notes": "画面中存在轻微反光。",
        },
    )

    assert "素材标题：白板会议照片" in text
    assert "规范化内容：" in text
    assert "识别人物：张三, 李四" in text
    assert "解析说明：画面中存在轻微反光。" in text


def test_build_multimodal_fallback_text_preserves_basic_metadata() -> None:
    asset = RawAsset(
        id="asset-2",
        user_id="user-1",
        asset_type="video",
        source_type="manual",
        title="启动会录像",
        mime_type="video/mp4",
        file_size=2048,
        status="uploaded",
    )

    text = build_multimodal_fallback_text(asset)

    assert "素材标题：启动会录像" in text
    assert "素材类型：video" in text
    assert "文件类型：video/mp4" in text
    assert "2048 bytes" in text


def test_normalize_multimodal_list_handles_string_and_list_inputs() -> None:
    assert normalize_multimodal_list(" 张三 ") == ["张三"]
    assert normalize_multimodal_list([" 张三 ", "", "李四"]) == ["张三", "李四"]
    assert normalize_multimodal_list(None) == []
