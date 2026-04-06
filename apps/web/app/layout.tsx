import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Website AICut",
  description: "Minimal login and admin bootstrap slice",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

