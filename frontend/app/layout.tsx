import { TooltipProvider } from "@/components/ui/tooltip";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono" });

export const metadata = {
  title: "FreeLaas | AI Freelancer Agent",
  description: "Automated qualification and proposal generation for 99Freelas",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${inter.variable} ${mono.variable} font-sans antialiased bg-background text-foreground min-h-screen`}
      >
        <TooltipProvider>{children}</TooltipProvider>
      </body>
    </html>
  );
}
