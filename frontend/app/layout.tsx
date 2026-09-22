import "./globals.css";
import "leaflet/dist/leaflet.css";
import type { Metadata } from "next";
export const metadata: Metadata = {
  title: "ŞimşekLog | Fleet Command",
  description: "Lojistik operasyon merkezi",
  icons: { icon: "/favicon.svg", shortcut: "/favicon.svg", apple: "/favicon.svg" },
};
export default function Layout({ children }: { children: React.ReactNode }) { return <html lang="tr"><body>{children}</body></html>; }
