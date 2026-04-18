import { AuthGate } from "@/components/auth-gate";
import { Panel } from "@/components/panel";
import { UploadForm } from "@/components/upload-form";

export default function InboxPage() {
  return (
    <AuthGate>
      <main className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
        <UploadForm />
        <Panel className="p-6" tone="info">
          <h2 className="text-3xl font-black">收件箱协议</h2>
          <ul className="mt-5 space-y-3 text-lg font-bold leading-relaxed">
            <li>1. 先存原始材料，再启动 AI 编排。</li>
            <li>2. 支持文本、图片、音频、视频导入，媒体会先转换为规范化文本。</li>
            <li>3. 所有知识抽取都是异步执行，任务状态可追踪。</li>
            <li>4. 原始文件、派生文本、结构化知识、风格化故事分层保存。</li>
          </ul>
        </Panel>
      </main>
    </AuthGate>
  );
}
