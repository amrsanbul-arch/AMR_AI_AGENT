import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = {
  title: "AMR AI | Instagram Manager",
  description: "لوحة إدارة محتوى Instagram — الهيكل الأولي",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ar" dir="rtl">
      <body>{children}</body>
    </html>
  );
}
