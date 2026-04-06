"use client";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

const sidebarItems = ["文案生成语音", "视频剪辑", "素材管理", "任务列表", "账户中心"];
const subItems = ["图片增强", "局部重绘", "智能扩图"];
const taskItems = [
  { name: "品牌口播第 12 条", status: "生成中" },
  { name: "短视频重剪第 03 条", status: "排队中" },
  { name: "产品介绍第 07 条", status: "已完成" },
];

function TopStats({ tone }: { tone: "warm" | "slate" | "ink" }) {
  const tones = {
    warm: "border-[#dcc8b3] bg-[#f6efe5] text-[#2a1d16]",
    slate: "border-[#cfd5df] bg-[#f3f6fa] text-[#16202a]",
    ink: "border-white/10 bg-white/5 text-white",
  } as const;

  return (
    <div className={`grid gap-3 rounded-[26px] border p-4 ${tones[tone]} md:grid-cols-4`}>
      <div>
        <p className="text-xs uppercase tracking-[0.24em] opacity-60">已剪辑</p>
        <p className="mt-2 text-2xl font-semibold">128</p>
      </div>
      <div>
        <p className="text-xs uppercase tracking-[0.24em] opacity-60">剩余条数</p>
        <p className="mt-2 text-2xl font-semibold">72</p>
      </div>
      <div>
        <p className="text-xs uppercase tracking-[0.24em] opacity-60">执行中任务</p>
        <p className="mt-2 text-2xl font-semibold">3</p>
      </div>
      <div>
        <p className="text-xs uppercase tracking-[0.24em] opacity-60">当前账号</p>
        <p className="mt-2 text-lg font-semibold">malin13</p>
      </div>
    </div>
  );
}

function Sidebar({ accentClass, mutedClass }: { accentClass: string; mutedClass: string }) {
  return (
    <aside className="space-y-3">
      <div className={`rounded-[28px] p-4 ${mutedClass}`}>
        <p className="text-xs uppercase tracking-[0.28em] opacity-60">功能</p>
        <div className="mt-4 space-y-2">
          {sidebarItems.map((item, index) => (
            <div
              key={item}
              className={`rounded-[18px] px-4 py-3 text-sm ${index === 0 ? accentClass : "bg-white/60 text-current dark:bg-white/5"}`}
            >
              {item}
            </div>
          ))}
        </div>
      </div>

      <div className={`rounded-[28px] p-4 ${mutedClass}`}>
        <p className="text-xs uppercase tracking-[0.28em] opacity-60">任务列表</p>
        <div className="mt-4 space-y-2">
          {taskItems.map((task) => (
            <div key={task.name} className="rounded-[18px] bg-white/70 px-4 py-3 text-sm dark:bg-white/5">
              <p className="font-medium">{task.name}</p>
              <p className="mt-1 text-xs opacity-60">{task.status}</p>
            </div>
          ))}
        </div>
      </div>
    </aside>
  );
}

function PreviewWarm() {
  return (
    <Card className="overflow-hidden border-[#dbc7b0] bg-[#fbf5ec] p-5">
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-stone-500">方向 A</p>
            <h2 className="mt-2 text-2xl font-semibold text-[#241913]" style={{ fontFamily: "Georgia, serif" }}>
              温润工具台
            </h2>
          </div>
          <div className="rounded-full border border-[#d7c4ae] bg-white px-4 py-2 text-xs text-stone-500">浅色高级感</div>
        </div>

        <TopStats tone="warm" />

        <div className="grid gap-4 lg:grid-cols-[240px_minmax(0,1fr)]">
          <Sidebar accentClass="bg-[#2a1d16] text-stone-100" mutedClass="bg-[#f3e8da] text-[#2a1d16]" />

          <div className="space-y-4">
            <div className="rounded-[28px] border border-[#dcc7af] bg-white px-5 py-4">
              <p className="text-xs uppercase tracking-[0.28em] text-stone-500">返回上一层</p>
              <p className="mt-2 text-sm text-stone-600">AI工具 / 音频工作台 / 文案生成语音</p>
            </div>

            <div className="rounded-[30px] border border-[#dcc7af] bg-white p-6">
              <div className="grid gap-4 xl:grid-cols-[1.12fr_0.88fr]">
                <div>
                  <p className="text-xs uppercase tracking-[0.28em] text-stone-500">主操作区</p>
                  <h3 className="mt-3 text-3xl font-semibold text-[#241913]" style={{ fontFamily: "Georgia, serif" }}>
                    文案生成语音
                  </h3>
                  <div className="mt-5 rounded-[24px] bg-[#faf3ea] p-4">
                    <p className="text-sm text-stone-500">音色AITOKEN消耗：128</p>
                    <div className="mt-4 min-h-[220px] rounded-[22px] border border-dashed border-[#d8c6b3] bg-white p-4 text-stone-400">
                      这里是大输入框
                    </div>
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="rounded-[24px] bg-[#2a1d16] p-4 text-stone-100">
                    <p className="text-xs uppercase tracking-[0.28em] text-stone-300">固定音色</p>
                    <p className="mt-3 text-xl font-semibold">MiniMax HD 口播音色</p>
                  </div>
                  <div className="rounded-[24px] border border-[#dcc7af] bg-[#f7efe5] p-4">
                    <p className="text-sm text-stone-500">结果区</p>
                    <div className="mt-4 h-[132px] rounded-[20px] bg-white" />
                  </div>
                  <Button className="h-12 w-full text-base">生成音频</Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}

function PreviewSlate() {
  return (
    <Card className="overflow-hidden border-[#cbd4df] bg-[#eef3f8] p-5">
      <div className="space-y-4 text-[#17202a]">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-slate-500">方向 B</p>
            <h2 className="mt-2 text-2xl font-semibold" style={{ fontFamily: "\"Trebuchet MS\", \"Segoe UI\", sans-serif" }}>
              冷静后台台面
            </h2>
          </div>
          <div className="rounded-full border border-[#c6d0dc] bg-white px-4 py-2 text-xs text-slate-500">中文运营后台</div>
        </div>

        <TopStats tone="slate" />

        <div className="grid gap-4 lg:grid-cols-[240px_minmax(0,1fr)]">
          <Sidebar accentClass="bg-[#18364e] text-white" mutedClass="bg-[#dfe8f0] text-[#17202a]" />

          <div className="space-y-4">
            <div className="rounded-[24px] border border-[#c8d2dc] bg-white px-5 py-4">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-xs uppercase tracking-[0.28em] text-slate-500">二级选项</p>
                  <p className="mt-2 text-sm text-slate-600">音频工具 / 语音生成 / 口播场景</p>
                </div>
                <Button className="h-10 px-5" variant="secondary">
                  返回上一层
                </Button>
              </div>
              <div className="mt-4 grid gap-3 md:grid-cols-3">
                {subItems.map((item, index) => (
                  <div key={item} className={`rounded-[18px] px-4 py-3 text-sm ${index === 0 ? "bg-[#18364e] text-white" : "bg-[#eef3f7] text-slate-600"}`}>
                    {item}
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-[28px] border border-[#c8d2dc] bg-white p-6">
              <p className="text-xs uppercase tracking-[0.28em] text-slate-500">任务操作页</p>
              <div className="mt-4 grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
                <div className="rounded-[24px] bg-[#f3f7fb] p-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-2xl font-semibold">文案生成语音</h3>
                    <p className="text-sm text-slate-500">音色AITOKEN消耗：128</p>
                  </div>
                  <div className="mt-4 min-h-[260px] rounded-[20px] border border-dashed border-[#c8d2dc] bg-white p-4 text-slate-400">
                    这里是主输入区
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="rounded-[24px] bg-[#18364e] p-4 text-white">
                    <p className="text-xs uppercase tracking-[0.28em] text-slate-300">状态</p>
                    <p className="mt-3 text-lg font-semibold">当前执行 3 个任务</p>
                  </div>
                  <div className="rounded-[24px] border border-[#c8d2dc] bg-[#f6f9fc] p-4">
                    <p className="text-sm text-slate-500">结果预览</p>
                    <div className="mt-4 h-[124px] rounded-[20px] bg-white" />
                  </div>
                  <Button className="h-12 w-full bg-[#18364e] text-base hover:bg-[#102739]">生成音频</Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}

function PreviewInk() {
  return (
    <Card className="overflow-hidden border-[#1f262d] bg-[#11161b] p-5 text-white">
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-stone-400">方向 C</p>
            <h2 className="mt-2 text-2xl font-semibold" style={{ fontFamily: "\"Avenir Next\", \"PingFang SC\", sans-serif" }}>
              深色控制舱
            </h2>
          </div>
          <div className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-xs text-stone-300">更像 AI Studio</div>
        </div>

        <TopStats tone="ink" />

        <div className="grid gap-4 lg:grid-cols-[240px_minmax(0,1fr)]">
          <Sidebar accentClass="bg-[#d98a52] text-[#17120f]" mutedClass="bg-[#171d23] text-white" />

          <div className="space-y-4">
            <div className="rounded-[24px] border border-white/10 bg-[#171d23] px-5 py-4">
              <p className="text-xs uppercase tracking-[0.28em] text-stone-400">返回层级</p>
              <p className="mt-2 text-sm text-stone-300">工作流 / 音频生成 / 固定音色 / 文案生成语音</p>
            </div>

            <div className="rounded-[28px] border border-white/10 bg-[#171d23] p-6">
              <div className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
                <div className="space-y-4">
                  <div className="rounded-[24px] bg-[#0f1317] p-4">
                    <p className="text-xs uppercase tracking-[0.28em] text-stone-400">工作台指标</p>
                    <p className="mt-3 text-2xl font-semibold">音色AITOKEN消耗：128</p>
                  </div>
                  <div className="rounded-[24px] bg-[#0f1317] p-4">
                    <p className="text-xs uppercase tracking-[0.28em] text-stone-400">当前音色</p>
                    <p className="mt-3 text-xl font-semibold">MiniMax HD Narration</p>
                  </div>
                  <Button className="h-12 w-full bg-[#d98a52] text-base text-[#17120f] hover:bg-[#c67a43]">生成音频</Button>
                </div>

                <div className="space-y-4">
                  <div className="rounded-[24px] bg-[#0f1317] p-4">
                    <p className="text-xs uppercase tracking-[0.28em] text-stone-400">文案输入</p>
                    <div className="mt-4 min-h-[206px] rounded-[20px] border border-dashed border-white/10 bg-[#171d23] p-4 text-stone-500">
                      这里是大输入框
                    </div>
                  </div>
                  <div className="rounded-[24px] bg-[#0f1317] p-4">
                    <p className="text-xs uppercase tracking-[0.28em] text-stone-400">输出结果</p>
                    <div className="mt-4 h-[96px] rounded-[20px] bg-[#171d23]" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}

export default function DesignPreviewPage() {
  return (
    <main className="min-h-screen bg-[#f3efe8] p-4 lg:p-8">
      <div className="mx-auto max-w-[1600px] space-y-6">
        <section className="rounded-[32px] bg-white p-6 shadow-panel">
          <p className="text-xs uppercase tracking-[0.32em] text-stone-500">Design Preview</p>
          <h1 className="mt-3 text-3xl font-semibold text-[#201713]">中文工具台方向预览</h1>
          <p className="mt-4 max-w-3xl text-sm leading-7 text-stone-600">
            这不是正式功能页，只是给你先看结构和视觉方向。三套方案都保留你要求的左侧功能列表、顶部冻结信息、二级页返回层级和任务列表。
          </p>
        </section>

        <div className="space-y-6">
          <PreviewWarm />
          <PreviewSlate />
          <PreviewInk />
        </div>
      </div>
    </main>
  );
}
