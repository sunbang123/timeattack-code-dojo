import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const siteUrl =
  process.env.NEXT_PUBLIC_SITE_URL ??
  (process.env.VERCEL_PROJECT_PRODUCTION_URL
    ? `https://${process.env.VERCEL_PROJECT_PRODUCTION_URL}`
    : process.env.VERCEL_URL
      ? `https://${process.env.VERCEL_URL}`
      : "http://localhost:3000");

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "Timeattack Code Dojo",
    template: "%s · Timeattack Code Dojo",
  },
  description: "제한 시간 안에 집중하고, 제출하고, 성장하는 실전 코딩 훈련장",
  applicationName: "Timeattack Code Dojo",
  manifest: "/manifest.webmanifest",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "Code Dojo",
  },
  icons: {
    icon: [{ url: "/timeattack-code-dojo-icon.png", type: "image/png" }],
    shortcut: "/timeattack-code-dojo-icon.png",
    apple: "/timeattack-code-dojo-icon.png",
  },
  openGraph: {
    title: "Timeattack Code Dojo",
    description: "제한 시간 안에 집중하고, 제출하고, 성장하는 실전 코딩 훈련장",
    siteName: "Timeattack Code Dojo",
    locale: "ko_KR",
    type: "website",
    images: [
      {
        url: "/og.png",
        width: 1672,
        height: 941,
        alt: "네온 사이버 전사와 Timeattack Code Dojo 타이틀",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Timeattack Code Dojo",
    description: "제한 시간 안에, 끝까지 푼다.",
    images: ["/og.png"],
  },
};

export const viewport: Viewport = {
  colorScheme: "dark",
  themeColor: "#07091b",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko" className={`${geistSans.variable} ${geistMono.variable}`}>
      <body>{children}</body>
    </html>
  );
}
