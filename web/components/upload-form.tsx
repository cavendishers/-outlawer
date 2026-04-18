"use client";

import { ChangeEvent, FormEvent, useState } from "react";

import { apiFetch, apiFormFetch } from "@/lib/api";
import { Panel } from "@/components/panel";

type UploadResult = {
  id: string;
  title: string;
};

const mediaOptions = [
  { value: "text", label: "文本", accept: "" },
  { value: "image", label: "图片", accept: "image/*" },
  { value: "audio", label: "音频", accept: "audio/*" },
  { value: "video", label: "视频", accept: "video/*" },
];

export function UploadForm() {
  const [title, setTitle] = useState("启动会记录");
  const [assetType, setAssetType] = useState("text");
  const [originalText, setOriginalText] = useState("2026-04-18 张三和李四在会议室A召开项目启动会，讨论图谱与导入流程。");
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<string>("");

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const nextFile = event.target.files?.[0] ?? null;
    setFile(nextFile);
    if (nextFile && !title.trim()) {
      const filename = nextFile.name.replace(/\.[^.]+$/, "");
      setTitle(filename || "未命名素材");
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus("正在归档原始记录...");
    const formData = new FormData();
    formData.append("title", title);
    formData.append("asset_type", assetType);
    if (assetType === "text") {
      formData.append("original_text", originalText);
    } else if (file) {
      formData.append("file", file);
    }
    const asset = await apiFormFetch<UploadResult>("/assets/upload", formData);
    setStatus("素材已入库，正在生成规范化内容并启动知识编排...");
    const note = await apiFetch<{ note_id: string; job_id: string }>("/notes", {
      method: "POST",
      body: JSON.stringify({ asset_id: asset.id }),
    });
    setStatus(`任务已创建。note=${note.note_id} / job=${note.job_id}`);
  }

  return (
    <Panel className="p-6" tone="default">
      <h2 className="text-3xl font-black uppercase">导入新卷宗</h2>
      <form className="mt-6 flex flex-col gap-4" onSubmit={handleSubmit}>
        <label className="text-sm font-black uppercase tracking-[0.16em]">素材类型</label>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {mediaOptions.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => {
                setAssetType(option.value);
                setStatus("");
              }}
              className={`border-4 border-ink px-4 py-3 text-left text-base font-black shadow-brutal transition-transform hover:-translate-y-1 ${
                assetType === option.value ? "bg-neon" : "bg-white"
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
        <input
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          className="brutal-input text-lg font-semibold"
          placeholder="标题"
        />
        {assetType === "text" ? (
          <textarea
            value={originalText}
            onChange={(event) => setOriginalText(event.target.value)}
            className="brutal-input min-h-40 text-base"
            placeholder="写入文本、会议纪要或观察记录"
          />
        ) : (
          <div className="space-y-3">
            <input
              type="file"
              accept={mediaOptions.find((option) => option.value === assetType)?.accept}
              onChange={handleFileChange}
              className="brutal-input w-full text-base file:mr-4 file:border-0 file:bg-neon file:px-3 file:py-2 file:font-black"
            />
            <p className="text-sm font-bold leading-relaxed">
              {file
                ? `已选择：${file.name} (${Math.max(1, Math.round(file.size / 1024))} KB)`
                : "上传后会先生成规范化文本，再进入人物、事件、关系和时间线抽取。"}
            </p>
          </div>
        )}
        <button className="brutal-action brutal-action-primary w-fit text-lg">
          投递到知识引擎
        </button>
      </form>
      {status ? <p className="mt-5 text-sm font-bold">{status}</p> : null}
    </Panel>
  );
}
