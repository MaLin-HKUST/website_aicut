"use client";

import { ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

type NavItem = {
  label: string;
  href?: string;
  active?: boolean;
  onClick?: () => void;
};

export function UserWorkspaceShell({
  title = "Audio Workspace",
  children,
  onLogout,
}: {
  title?: string;
  children: ReactNode;
  onLogout?: () => void | Promise<void>;
}) {
  const router = useRouter();
  const pathname = usePathname();

  const items: NavItem[] = [
    { label: "Dashboard", href: "/welcome", active: pathname === "/welcome" },
    { label: "Smart Cut", href: "/smart-cut", active: pathname.startsWith("/smart-cut") },
    { label: "Queue", href: "/tasks", active: pathname.startsWith("/tasks") },
    { label: "TTS", href: "/tts", active: pathname.startsWith("/tts") },
  ];

  return (
    <main className="min-h-screen bg-[#f6efe4] p-4 lg:p-8">
      <div className="mx-auto grid max-w-7xl gap-5 xl:grid-cols-[0.78fr_1.22fr]">
        <Card className="rounded-[32px] border-[#d8cfbf] bg-[#242a35] p-6 text-stone-100 shadow-panel">
          <p className="text-sm uppercase tracking-[0.3em] text-stone-300">{title}</p>
          <div className="mt-8 space-y-3">
            {items.map((item) => (
              <button
                key={item.label}
                className={`block w-full rounded-[18px] px-4 py-3 text-left text-sm font-medium transition ${
                  item.active ? "bg-[#34415f] text-white" : "text-stone-300 hover:bg-white/5"
                }`}
                onClick={() => {
                  if (item.onClick) {
                    item.onClick();
                    return;
                  }
                  if (item.href) router.push(item.href);
                }}
                type="button"
              >
                {item.label}
              </button>
            ))}
          </div>
          <div className="mt-8 pt-6">
            <Button
              className="w-full justify-start rounded-[18px] bg-white/5 px-4 py-3 text-sm font-medium text-stone-300 hover:bg-white/10"
              onClick={() => void onLogout?.()}
              type="button"
              variant="ghost"
            >
              Logout
            </Button>
          </div>
        </Card>

        <div className="space-y-5">{children}</div>
      </div>
    </main>
  );
}
