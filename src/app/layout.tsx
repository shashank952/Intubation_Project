import type { Metadata } from 'next';
import { Playfair_Display, Inter, JetBrains_Mono } from 'next/font/google';
import './globals.css';

const playfair = Playfair_Display({
  subsets: ['latin'],
  variable: '--font-display',
  display: 'swap',
});

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-body',
  display: 'swap',
});

const jetbrains = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'Airway MD — Airway Risk Assessment',
  description:
    'Clinical decision support tool for difficult airway prediction. Built for anesthesiologists.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${playfair.variable} ${inter.variable} ${jetbrains.variable}`} suppressHydrationWarning>
      <body className="min-h-screen bg-paper dark:bg-[#121212] font-body antialiased">
        <script
          dangerouslySetInnerHTML={{
            __html:
              "(function(){try{var r=document.documentElement;r.setAttribute('data-theme',localStorage.getItem('neo-theme')||'yellow');var d=localStorage.getItem('theme');if(d==='dark'||(!d&&window.matchMedia('(prefers-color-scheme: dark)').matches)){r.classList.add('dark');}}catch(err){}})();",
          }}
        />
        {children}
      </body>
    </html>
  );
}
