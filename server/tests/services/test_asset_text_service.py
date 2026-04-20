from app.models.raw_asset import RawAsset
from app.services.asset_text_service import (
    build_multimodal_canonical_text,
    build_multimodal_fallback_text,
    merge_multimodal_payloads,
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
            "observed_scene": ["会议现场", "白板讨论"],
            "observed_objects": ["白板", "演示文稿"],
            "observed_actions": ["讨论", "讲解"],
            "document_type": "会议现场照片",
            "image_layout": "横向 1600x900",
            "parsing_notes": "画面中存在轻微反光。",
        },
    )

    assert "素材标题：白板会议照片" in text
    assert "规范化内容：" in text
    assert "识别人物：张三, 李四" in text
    assert "识别场景：会议现场, 白板讨论" in text
    assert "识别物件：白板, 演示文稿" in text
    assert "识别动作：讨论, 讲解" in text
    assert "文档类型：会议现场照片" in text
    assert "画面布局：横向 1600x900" in text
    assert "解析说明：画面中存在轻微反光。" in text


def test_build_multimodal_canonical_text_includes_source_attribution() -> None:
    asset = RawAsset(
        id="asset-3",
        user_id="user-1",
        asset_type="video",
        source_type="manual",
        title="启动会录像",
        status="uploaded",
    )

    text = build_multimodal_canonical_text(
        asset,
        {
            "canonical_text": "张三在会议室 A 汇报启动计划。",
            "source_attribution": [
                {
                    "source_type": "video_frame_ocr",
                    "label": "frame_01",
                    "timecode": "00:00:03",
                    "text": "项目启动会 2026-04-18",
                    "confidence": 0.6,
                    "evidence_type": "direct_observation",
                },
                {
                    "source_type": "video_audio_transcript",
                    "label": "audio_track",
                    "timecode": None,
                    "text": "张三汇报了图谱拆分方案。",
                    "confidence": 0.72,
                    "evidence_type": "direct_observation",
                },
            ],
        },
    )

    assert "来源片段：" in text
    assert "- [直接证据] frame_01@00:00:03: 项目启动会 2026-04-18" in text
    assert "- [直接证据] audio_track: 张三汇报了图谱拆分方案。" in text


def test_build_multimodal_canonical_text_includes_video_scene_segments() -> None:
    asset = RawAsset(
        id="asset-4",
        user_id="user-1",
        asset_type="video",
        source_type="manual",
        title="启动会录像",
        status="uploaded",
    )

    text = build_multimodal_canonical_text(
        asset,
        {
            "canonical_text": "张三与李四讨论导入流程。",
            "video_scene_segments": [
                {
                    "segment_index": 1,
                    "start_timecode": "00:00:00",
                    "end_timecode": "00:00:06",
                    "frame_label": "scene_01",
                    "ocr_text": "项目启动会 2026-04-18",
                    "confidence": 0.6,
                    "evidence_type": "direct_observation",
                },
                {
                    "segment_index": 2,
                    "start_timecode": "00:00:06",
                    "end_timecode": "00:00:12",
                    "label": "scene_02",
                    "description": "两位参与者围绕白板讨论。",
                    "inferred_context": "可能正在确认导入流程。",
                    "confidence": 0.52,
                    "evidence_type": "model_inference",
                },
            ],
        },
    )

    assert "视频片段证据：" in text
    assert "- [直接证据] scene_01@00:00:00-00:00:06: 项目启动会 2026-04-18" in text
    assert "- [模型推断] scene_02@00:00:06-00:00:12: 可能正在确认导入流程。；两位参与者围绕白板讨论。" in text


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


def test_merge_multimodal_payloads_combines_local_and_ai_observations() -> None:
    merged = merge_multimodal_payloads(
        {
            "canonical_text": "画面文字：项目启动会",
            "short_summary": "本地 OCR 识别出会议主题。",
            "observed_people": ["张三"],
            "observed_time": ["2026-04-18"],
            "observed_scene": ["会议现场"],
            "observed_objects": ["白板"],
            "document_type": "会议现场照片",
            "image_layout": "横向 1600x900",
            "parsing_notes": "本地 OCR 提取。",
            "source_attribution": [
                {
                    "source_type": "video_frame_ocr",
                    "label": "frame_01",
                    "timecode": "00:00:03",
                    "text": "项目启动会",
                    "confidence": 0.6,
                    "evidence_type": "direct_observation",
                }
            ],
            "video_scene_segments": [
                {
                    "segment_index": 1,
                    "start_timecode": "00:00:00",
                    "end_timecode": "00:00:06",
                    "frame_label": "scene_01",
                    "ocr_text": "项目启动会",
                    "confidence": 0.6,
                    "evidence_type": "direct_observation",
                }
            ],
            "confidence": 0.6,
        },
        {
            "canonical_text": "张三在会议室 A 讲解图谱拆分计划。",
            "short_summary": "AI 补充了人物和地点上下文。",
            "observed_people": ["张三", "李四"],
            "observed_location": ["会议室A"],
            "observed_scene": ["会议现场", "投影演示"],
            "observed_objects": ["白板", "投影幕布"],
            "observed_actions": ["讲解"],
            "parsing_notes": "AI 识别出现场发言内容。",
            "source_attribution": [
                {
                    "source_type": "video_audio_transcript",
                    "label": "audio_track",
                    "timecode": None,
                    "text": "张三在会议室 A 讲解图谱拆分计划。",
                    "confidence": 0.74,
                    "evidence_type": "direct_observation",
                }
            ],
            "video_scene_segments": [
                {
                    "segment_index": 2,
                    "start_timecode": "00:00:06",
                    "end_timecode": "00:00:12",
                    "label": "scene_02",
                    "description": "会议现场有投影和白板。",
                    "inferred_context": "张三可能正在讲解图谱拆分计划。",
                    "confidence": 0.64,
                    "evidence_type": "model_inference",
                }
            ],
            "confidence": 0.74,
        },
    )

    assert merged["canonical_text"] == "张三在会议室 A 讲解图谱拆分计划。"
    assert merged["observed_people"] == ["张三", "李四"]
    assert merged["observed_location"] == ["会议室A"]
    assert merged["observed_scene"] == ["会议现场", "投影演示"]
    assert merged["observed_objects"] == ["白板", "投影幕布"]
    assert merged["observed_actions"] == ["讲解"]
    assert merged["document_type"] == "会议现场照片"
    assert merged["image_layout"] == "横向 1600x900"
    assert merged["confidence"] == 0.74
    assert len(merged["source_attribution"]) == 2
    assert merged["source_attribution"][0]["evidence_type"] == "direct_observation"
    assert len(merged["video_scene_segments"]) == 2
    assert merged["video_scene_segments"][0]["observed_text"] == "项目启动会"
    assert merged["video_scene_segments"][1]["evidence_type"] == "model_inference"
