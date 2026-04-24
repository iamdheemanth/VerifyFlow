import localFont from "next/font/local";
import AuthProvider from "@/components/AuthProvider";
import SidebarShell from "@/components/SidebarShell";
import "./globals.css";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});
const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} bg-[#0A0A08] text-[#F5F4F0] font-sans antialiased`}
      >
        <AuthProvider>
          <SidebarShell />
          <main className="min-h-screen bg-[#0A0A08]">
            <div className="page-enter">{children}</div>
          </main>
        </AuthProvider>
      </body>
    </html>
  )
}
