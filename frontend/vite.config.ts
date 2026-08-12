import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

const DEFAULT_PROXY_TARGET = 'http://127.0.0.1:8010'

/**
 * The dev server proxies `/api/*` to the backend and strips the prefix, because
 * the backend mounts its routers at the root (`/auth`, `/companies`, ...).  The
 * prefix exists so a single origin can serve both the SPA and the API without
 * the API shadowing client-side routes — `/auth/change-temporary-password` is a
 * React route, `/api/auth/login` is the backend.
 */
function stripApiPrefix(path: string): string {
  return path.replace(/^\/api/, '') || '/'
}

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', 'VITE_')
  if (mode === 'production') {
    if (env.VITE_PUBLIC_DEMO === '1') {
      throw new Error('VITE_PUBLIC_DEMO is forbidden in production builds')
    }
    const apiBase = (env.VITE_API_BASE_URL || '/api').trim()
    if (/^http:\/\/(?:localhost|127\.0\.0\.1)(?::|\/|$)/i.test(apiBase)) {
      throw new Error('Production VITE_API_BASE_URL must not target localhost')
    }
  }

  // Quick-tunnel demo only. Vite rejects unknown Host headers to block DNS
  // rebinding, so the tunnel hostname has to be allowed explicitly, and HMR has
  // to be told the browser reaches it over https/443 rather than the local port.
  const publicDemo = env.VITE_PUBLIC_DEMO === '1'
  const extraAllowedHosts = (env.VITE_PUBLIC_DEMO_ALLOWED_HOSTS ?? '')
    .split(',')
    .map((host) => host.trim())
    .filter(Boolean)

  return {
    plugins: [react()],
    server: {
      proxy: {
        '/api': {
          target: env.VITE_DEV_API_PROXY_TARGET || DEFAULT_PROXY_TARGET,
          changeOrigin: true,
          rewrite: stripApiPrefix,
        },
      },
      ...(publicDemo
        ? {
            allowedHosts: ['.trycloudflare.com', ...extraAllowedHosts],
            hmr: { clientPort: 443, protocol: 'wss' as const },
          }
        : {}),
    },
  }
})
