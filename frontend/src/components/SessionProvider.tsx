'use client';

import { useEffect, useState } from 'react';
import { usePathname } from 'next/navigation';
import { useIdleTimeout } from '@/lib/useIdleTimeout';
import SessionWarningModal from '@/components/SessionWarningModal';

const PUBLIC_PATHS = ['/login', '/signup', '/about'];

export default function SessionProvider() {
  const pathname = usePathname();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  const onPublicPage = PUBLIC_PATHS.some((path) => pathname?.startsWith(path));
  const enabled = mounted && !onPublicPage;
  const { warning, secondsLeft, staySignedIn, logOutNow } = useIdleTimeout(enabled);

  return (
    <SessionWarningModal
      open={warning}
      secondsLeft={secondsLeft}
      onStay={staySignedIn}
      onLogout={logOutNow}
    />
  );
}
