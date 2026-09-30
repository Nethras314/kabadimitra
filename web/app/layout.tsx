import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Kabadi Mitra',
  description: 'Collector-first e-waste bridge',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{ margin: 0, fontFamily: 'system-ui, sans-serif' }}>
        <nav style={{ padding: '10px 16px', borderBottom: '1px solid #e5e7eb' }}>
          <a href="/" style={{ marginRight: 16, color: '#14532d' }}>Dashboard</a>
          <a href="/admin" style={{ color: '#14532d' }}>Admin</a>
        </nav>
        {children}
      </body>
    </html>
  );
}
