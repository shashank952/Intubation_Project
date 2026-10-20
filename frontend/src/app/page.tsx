'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { getToken } from '@/lib/api';
import { isLocalHost } from '@/lib/localDemo';

export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    if (getToken() || isLocalHost()) {
      router.replace('/dashboard');
    } else {
      router.replace('/login');
    }
  }, [router]);

  return null;
}
