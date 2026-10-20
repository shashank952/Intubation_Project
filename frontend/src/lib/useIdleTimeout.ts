'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  clearToken,
  getToken,
  getIdleTimeoutSeconds,
  getWarningSeconds,
  heartbeat,
  logout,
} from '@/lib/api';

const ACTIVITY_EVENTS = ['mousedown', 'mousemove', 'keydown', 'scroll', 'touchstart'] as const;
const ACTIVITY_THROTTLE_MS = 5000;
const TICK_MS = 5000;

function redirectToLogin(): void {
  if (typeof window === 'undefined') return;
  if (window.location.pathname.startsWith('/login')) return;
  window.location.assign('/login?reason=idle');
}

export function useIdleTimeout(enabled: boolean) {
  const [warning, setWarning] = useState(false);
  const [secondsLeft, setSecondsLeft] = useState(0);
  const lastActivityRef = useRef<number>(Date.now());
  const warningRef = useRef(false);
  const endedRef = useRef(false);

  const endSession = useCallback(() => {
    if (endedRef.current) return;
    endedRef.current = true;
    warningRef.current = false;
    setWarning(false);
    void logout();
    clearToken();
    redirectToLogin();
  }, []);

  const staySignedIn = useCallback(async () => {
    try {
      await heartbeat();
      lastActivityRef.current = Date.now();
      warningRef.current = false;
      setWarning(false);
      setSecondsLeft(0);
    } catch {
      endSession();
    }
  }, [endSession]);

  useEffect(() => {
    if (!enabled || !getToken()) return;

    const idleMs = getIdleTimeoutSeconds() * 1000;
    const warningMs = Math.min(getWarningSeconds() * 1000, idleMs / 2);
    lastActivityRef.current = Date.now();
    warningRef.current = false;
    endedRef.current = false;

    const tick = () => {
      if (endedRef.current) return;
      const idleFor = Date.now() - lastActivityRef.current;
      if (idleFor >= idleMs) {
        endSession();
        return;
      }
      if (idleFor >= idleMs - warningMs) {
        warningRef.current = true;
        setWarning(true);
        setSecondsLeft(Math.max(0, Math.ceil((idleMs - idleFor) / 1000)));
      } else if (warningRef.current) {
        warningRef.current = false;
        setWarning(false);
      }
    };

    const onVisibilityChange = () => {
      if (!document.hidden) tick();
    };

    const onStorage = (event: StorageEvent) => {
      if (event.key === 'access_token' && !event.newValue) redirectToLogin();
    };

    let lastEventAt = 0;
    const onActivity = () => {
      if (warningRef.current) return;
      const now = Date.now();
      if (now - lastEventAt < ACTIVITY_THROTTLE_MS) return;
      lastEventAt = now;
      lastActivityRef.current = now;
    };

    ACTIVITY_EVENTS.forEach((name) =>
      window.addEventListener(name, onActivity, { passive: true })
    );
    document.addEventListener('visibilitychange', onVisibilityChange);
    window.addEventListener('storage', onStorage);
    const intervalId = window.setInterval(tick, TICK_MS);

    return () => {
      ACTIVITY_EVENTS.forEach((name) => window.removeEventListener(name, onActivity));
      document.removeEventListener('visibilitychange', onVisibilityChange);
      window.removeEventListener('storage', onStorage);
      window.clearInterval(intervalId);
    };
  }, [enabled, endSession]);

  return { warning, secondsLeft, staySignedIn, logOutNow: endSession };
}
