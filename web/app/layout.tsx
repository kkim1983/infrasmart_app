import type { Metadata } from 'next';
import './globals.css';
import { Providers } from '@/components/Providers';

export const metadata: Metadata = {
  title: 'InfraSmart',
  description: '시설물 안전점검 플랫폼',
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1" />
      </head>
      <body className="bg-white min-h-screen">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
