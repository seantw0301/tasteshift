import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TasteShift",
  description: "Know your crowd. Choose your products. Stock with confidence.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
