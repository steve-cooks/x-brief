import type { Metadata, Viewport } from "next"
import "./globals.css"

export const metadata: Metadata = {
  title: "𝕏 Brief — Your Curated Timeline",
  description: "AI-powered 𝕏 timeline curation. Never miss what matters.",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "𝕏 Brief",
  },
}

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#FFFFFF" },
    { media: "(prefers-color-scheme: dark)", color: "#000000" },
  ],
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en">
      <head>
        <link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
      </head>
      <body className="antialiased font-[-apple-system,BlinkMacSystemFont,'SF_Pro_Display','Segoe_UI','Helvetica_Neue',Arial,sans-serif]">
        {children}
      </body>
    </html>
  )
}
