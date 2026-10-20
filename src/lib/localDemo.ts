const LOCAL_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0', '::1'];
const PRIVATE_PREFIXES = ['192.168.', '10.'];

export function isLocalHost(): boolean {
  if (typeof window === 'undefined') return false;
  if (process.env.NEXT_PUBLIC_LOCAL_DEMO === 'false') return false;
  const host = window.location.hostname;
  return (
    LOCAL_HOSTS.includes(host) ||
    host.endsWith('.local') ||
    PRIVATE_PREFIXES.some((prefix) => host.startsWith(prefix))
  );
}

export const LOCAL_DEMO_USER = { email: 'local.demo@airwaymd', role: 'admin' };

export function ensureLocalSession(): void {
  if (!isLocalHost()) return;
  if (!window.localStorage.getItem('access_token')) {
    window.localStorage.setItem('access_token', 'local-demo-token');
  }
  if (!window.localStorage.getItem('user')) {
    window.localStorage.setItem('user', JSON.stringify(LOCAL_DEMO_USER));
  }
}
