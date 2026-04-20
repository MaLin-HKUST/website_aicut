import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Website AICut",
  description: "Minimal login and admin bootstrap slice",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <body suppressHydrationWarning>{children}</body>
    </html>
  );
}
