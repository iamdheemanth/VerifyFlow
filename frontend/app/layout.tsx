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
        className={`${geistSans.variable} ${geistMono.variable} bg-[#F7F3EE] text-[#1A1410] font-sans antialiased`}
      >
        <AuthProvider>
          <SidebarShell />
          <main className="md:ml-56 min-h-screen">
            <div className="page-enter">{children}</div>
          </main>
        </AuthProvider>
      </body>
    </html>
  )
}
