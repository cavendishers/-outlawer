import { AuthGate } from "@/components/auth-gate";
import { Panel } from "@/components/panel";
import { UploadForm } from "@/components/upload-form";

export default function InboxPage() {
  return (
    <AuthGate>
      <main className="space-y-5">
        <section className="workbench-header">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="workbench-title">导入卷宗</h1>
                <span className="workbench-stamp bg-aqua">原始材料入口</span>
              </div>
              <p className="workbench-lede">
                先保留原始资产，再生成派生文本和结构化知识；上传与 AI 处理保持分离。
              </p>
            </div>
          </div>
        </section>

        <section className="grid gap-5 lg:grid-cols-[1.2fr_0.8fr]">
          <UploadForm />
          <Panel className="p-5" tone="info">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-xl font-black">导入规则</h2>
              <span className="workbench-stamp bg-canvas">异步处理</span>
            </div>
            <ul className="mt-4 space-y-3 text-sm font-bold leading-relaxed md:text-base">
              <li>1. 先存原始材料，再启动 AI 编排。</li>
              <li>2. 文本、图片、音频、视频会先转换为规范化文本。</li>
              <li>3. 知识抽取以任务形式执行，状态可追踪。</li>
              <li>4. 原始文件、派生文本、结构化知识、风格化故事分层保存。</li>
            </ul>
          </Panel>
        </section>
      </main>
    </AuthGate>
  );
}
