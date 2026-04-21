import Link from "next/link";

export default function NotFoundPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-stone-50 px-6 py-16 text-stone-900">
      <div className="w-full max-w-xl rounded-[32px] border border-stone-200 bg-white p-10 shadow-[0_24px_80px_rgba(41,31,22,0.08)]">
        <p className="text-sm font-medium tracking-[0.2em] text-stone-500">404</p>
        <h1 className="mt-3 text-4xl font-semibold tracking-tight">页面不存在</h1>
        <p className="mt-4 text-base leading-7 text-stone-600">
          当前页面不存在，或链接已经失效。你可以返回首页，或者直接进入智能剪气口继续处理任务。
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            href="/welcome"
            className="inline-flex items-center justify-center rounded-full bg-stone-900 px-5 py-3 text-sm font-medium text-white transition hover:bg-stone-800"
          >
            返回首页
          </Link>
          <Link
            href="/smart-cut"
            className="inline-flex items-center justify-center rounded-full border border-stone-300 px-5 py-3 text-sm font-medium text-stone-700 transition hover:border-stone-400 hover:text-stone-900"
          >
            进入智能剪气口
          </Link>
        </div>
      </div>
    </main>
  );
}
