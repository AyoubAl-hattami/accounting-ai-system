# Free Public Local Demo Tunnel

Show the app to someone who is not in the room, from your own laptop, over a
single temporary public link, for free.

```powershell
cd C:\ayoub\accounting-ai-system
.\scripts\start-public-demo.ps1
```

You get one URL:

```text
https://<random>.trycloudflare.com
```

That single link serves the UI, the API, the platform pages, the onboarding
handover link, and client login.

---

## 1. What this is, and what it is not

**It is** a temporary demo tunnel. Cloudflare Quick Tunnel opens an outbound
connection from your laptop and gives you a throwaway `trycloudflare.com`
hostname that forwards to your local dev server. No account, no domain, no
credit card, no router port forwarding.

**It is not** production hosting. Specifically:

| | Public demo tunnel | Real deployment |
| --- | --- | --- |
| Uptime | Only while your laptop is awake and this window is open | Always |
| URL | New random URL on every run | Your own domain |
| Server | Vite dev server + Uvicorn without `--reload` | Built assets behind a real web server |
| Database | Whatever is on your laptop | Managed, backed up |
| Suitable for | Sales demos, showing a feature to a colleague, remote walkthroughs | Paying clients |

When a client starts depending on the system, move to a VPS with a real domain.
Do not hand a `trycloudflare.com` link to a paying customer.

---

## 2. Requirements

- Your laptop stays awake and online for the whole demo.
- PostgreSQL running locally, `backend\.env` present with a working
  `DATABASE_URL` (see [Local Demo Quickstart](local-demo-quickstart.md)).
- `backend\.venv` created with the requirements installed.
- Node.js on `PATH` or installed at `C:\nodejs`.
- `cloudflared` installed.

Install `cloudflared` once:

```powershell
winget install -e --id Cloudflare.cloudflared --accept-package-agreements --accept-source-agreements
```

Then **open a new terminal** so the updated `PATH` is picked up, and check:

```powershell
cloudflared --version
```

---

## 3. Start the demo

```powershell
cd C:\ayoub\accounting-ai-system
.\scripts\start-public-demo.ps1
```

The script:

1. Checks `cloudflared`, Node, `backend\.venv`, `backend\.env`, and that ports
   5173 and 8010 are free.
2. Installs `frontend\node_modules` if it is missing.
3. Starts the Vite dev server on `127.0.0.1:5173` with the API base set to `/api`.
4. Starts a Cloudflare Quick Tunnel pointing at `http://127.0.0.1:5173` and waits
   for the generated URL to appear in the tunnel log.
5. Runs `alembic upgrade head`.
6. Starts the backend on `127.0.0.1:8010` with `APP_ENV=development`,
   `AI_JOURNAL_PROVIDER=rules`, and `APP_PUBLIC_URL` set to the captured URL.
7. Prints a summary and opens the public URL in your browser.

Everything runs from this one window. Backend logs stay in front of you.

**To stop:** press `Ctrl+C`. The script stops the frontend and the tunnel on its
way out.

### Options

| Parameter | Purpose |
| --- | --- |
| `-BackendPort 8010` | Change the local backend port. The Vite proxy follows it. |
| `-FrontendPort 5173` | Change the local frontend port. The tunnel follows it. |
| `-NoOpen` | Do not open the public URL in the browser. |
| `-PublicUrl <url>` | Skip the Quick Tunnel and use a URL you already serve (named tunnel, reverse proxy, real domain). Whatever serves it must forward to the frontend port. |
| `-SkipMigrations` | Skip `alembic upgrade head`. |

Nothing is ever written to `backend\.env` or `frontend\.env`. `APP_PUBLIC_URL`
and the frontend API base are set on the child processes only, for the lifetime
of the demo.

---

## 4. The one-link architecture

```text
                    https://<random>.trycloudflare.com
                                   |
                                   v
                    Vite dev server  127.0.0.1:5173
                       |                        |
              /  and everything else        /api/*
                       |                        |
                       v                        v
                 React SPA            strip /api, forward to
                                       127.0.0.1:8010
```

The frontend runs with `VITE_API_BASE_URL=/api`, so every request is relative:

| Browser requests | Vite forwards to |
| --- | --- |
| `/api/auth/login` | `http://127.0.0.1:8010/auth/login` |
| `/api/companies` | `http://127.0.0.1:8010/companies` |
| `/api/platform/subscriptions` | `http://127.0.0.1:8010/platform/subscriptions` |
| `/api/health` | `http://127.0.0.1:8010/health` |

Two consequences worth understanding:

**There is no CORS.** The browser only ever talks to one origin, so
`CORS_ORIGINS` in `backend\.env` does not need the tunnel hostname. This is why
the demo needs one link instead of two.

**`/api` is a prefix, not a route.** The backend mounts its routers at the root
(`/auth`, `/companies`, `/platform/...`) and the proxy strips `/api` before
forwarding. The prefix exists so that the API cannot shadow client-side routes:
`/auth/change-temporary-password` is a React route served by the SPA, while
`/api/auth/login` is the backend. Proxying `/auth` directly would break the
forced password-change screen.

### Normal development is unchanged

`frontend\.env` still holds `VITE_API_BASE_URL=http://127.0.0.1:8010`, and
`.\scripts\dev-start-frontend.ps1` and `.\scripts\dev-start-backend.ps1` behave
exactly as before. The `/api` proxy is present in the dev server either way but
unused, because the normal configuration points at the backend directly.

The demo also sets `VITE_PUBLIC_DEMO=1`, which allows the `*.trycloudflare.com`
hostname through Vite's host check and tells the HMR client that the browser
reaches it over `wss` on port 443. Without that variable the host check stays
strict, so ordinary `npm run dev` is not reachable through a tunnel.

---

## 5. Demo checklists

### Login

1. Open the public URL from another device — a phone on mobile data is the best
   test, because it cannot reach your laptop any other way.
2. Log in with your platform admin account.
3. Open the browser dev tools Network tab and confirm requests go to
   `https://<random>.trycloudflare.com/api/...` and **not** to `http://127.0.0.1:8010`.
4. Check the API directly: `https://<random>.trycloudflare.com/api/health` should
   return `{"status":"ok","service":"accounting-ai-backend"}`.
5. The dashboard loads with data.

### Platform pages (platform admin only)

1. `/platform/subscriptions` opens and lists tenants.
2. `/platform/onboarding` opens.
3. Sign in as a company user instead and confirm the **Platform** group is not in
   the sidebar.

### Client onboarding and handover

1. From `/platform/onboarding`, create a throwaway test client.
2. On the success screen, check the handover message shows the public URL
   (`https://<random>.trycloudflare.com`) and **not** the
   `[add your domain here]` placeholder. See
   [Secure Client Handover](../product/secure-client-handover.md).
3. The temporary password is shown once. Copy it before leaving the screen.
4. Open the public URL in a private window and log in as the new client admin.
5. The forced password change appears at `/auth/change-temporary-password` and
   nothing else opens until it is done.
6. After the change, the client lands on the dashboard.
7. Confirm the client cannot see the **Platform** group.

---

## 6. APP_PUBLIC_URL and handover messages

The backend cannot infer the domain it is served behind, so the handover message
prints whatever `APP_PUBLIC_URL` says, or `[add your domain here]` when it is
unset.

The start script captures the tunnel URL from the `cloudflared` log and passes it
to the backend process as `APP_PUBLIC_URL`, so handover messages contain a link
the client can actually open. This is automatic — you do not have to edit
`backend\.env`, and the script deliberately does not.

If the capture fails, the script says so loudly, prints the tail of the tunnel
log, and starts the backend anyway. Handover messages then show the placeholder.
Read the URL out of the log and restart with it:

```powershell
.\scripts\start-public-demo.ps1 -PublicUrl https://<the-url-you-found>.trycloudflare.com
```

Because the URL changes on every run, any handover message you sent from an
earlier session is already dead. Send handover details during the same session
you generated them in.

---

## 7. Stopping

Press `Ctrl+C` in the script window. The frontend and the tunnel are stopped
automatically.

If the window was killed hard — closed with the X button, or the machine
crashed — the dev server can survive and keep holding port 5173. Clean it up:

```powershell
.\scripts\stop-public-demo.ps1
```

That script stops only the processes the start script recorded, and only when the
recorded name and start time still match, so a reused PID belonging to something
else is left alone. It never sweeps `node` / `python` / `cloudflared` by name.

---

## 8. Troubleshooting

**`cloudflared` is not recognized**

It is not installed, or the terminal predates the install. Install it and open a
new terminal:

```powershell
winget install -e --id Cloudflare.cloudflared --accept-package-agreements --accept-source-agreements
```

**`Port 5173 is already in use` / `Port 8010 is already in use`**

Another dev server is running. Stop it, or pick different ports:

```powershell
Get-NetTCPConnection -LocalPort 5173 | Select-Object OwningProcess
.\scripts\start-public-demo.ps1 -FrontendPort 5273 -BackendPort 8110
```

If the leftovers came from a previous demo, run `.\scripts\stop-public-demo.ps1`.

**Frontend did not start listening**

The script prints the tail of the Vite log and the full log path. The usual cause
is a broken `node_modules`; delete it and let the script reinstall.

**Backend refuses to start**

PostgreSQL is not running, or `DATABASE_URL` points at a database that does not
exist. `alembic upgrade head` fails first with a connection error:

```powershell
Get-Service postgresql*
Start-Service postgresql-x64-18
```

**The tunnel URL was not captured**

The script warns, prints the tunnel log tail, and keeps going. If `cloudflared`
exited, check whether outbound traffic is blocked by a corporate firewall or VPN.
If it is running but slow, read the URL from
`%TEMP%\accounting-ai-public-demo\tunnel.err.log` and restart with `-PublicUrl`.

**`Blocked request. This host is not allowed.`**

Vite's host check rejected the hostname. The demo script allows
`*.trycloudflare.com` automatically, and the hostname of any `-PublicUrl` you
pass. If you started the frontend some other way, that allowance is not active —
use the demo script.

**Login fails through the public URL but works locally**

Check the Network tab. If requests are going to `http://127.0.0.1:8010` then the
frontend is not using the `/api` base — it was started by
`dev-start-frontend.ps1` rather than the demo script, or `frontend\.env` is
overriding it. Only the demo script sets `VITE_API_BASE_URL=/api`.

Also note that failed logins are rate limited (`AUTH_FAILED_LOGIN_LIMIT`,
default 5 per minute). Wait a minute and retry.

**CORS error in the console**

The demo should never produce one, because everything is same-origin. A CORS
error means the frontend is calling an absolute backend URL — same cause and fix
as above.

**API calls go to 127.0.0.1 from the client's device**

Same cause again. `127.0.0.1` on their device is *their* machine, so it will
never work. The API base must be `/api`.

**HMR / websocket errors in the console**

Cosmetic. The app works; only hot reload is affected. It can happen when
`-PublicUrl` serves plain `http` or a non-standard port, since the demo assumes
`https` on 443. Reload the page manually after editing code.

**The tunnel closed, or the URL changed**

Expected. Quick Tunnel URLs are per-run and have no uptime guarantee. Restart the
script and send the new link. Anyone holding the old link gets nothing.

---

## 9. Security warnings

- **Anyone with the link can reach the login page.** It is a public URL on the
  internet, not an unlisted one. Treat it as exposed.
- **Do not put real or sensitive client data behind it.** Demo it with seeded
  demo data. See [Local Demo Quickstart](local-demo-quickstart.md).
- **Use a strong platform admin password.** `admin@example.com` / `Password123`
  are documented, shared, local-only credentials. Never expose an account using
  them through a public tunnel.
- **Never share platform admin credentials with a client.** Platform admins can
  see and suspend every tenant. Onboard the client a normal company admin
  instead.
- **Do not leave the demo running unattended.** Stop it when the call ends. The
  link stays live as long as the window is open.
- **Move to a real VPS and domain before anyone pays for this.** Tunnel demos are
  for showing, not for serving.

---

## See also

- [Local Demo Quickstart](local-demo-quickstart.md) — prerequisites, seed data,
  demo walkthrough
- [Secure Client Handover](../product/secure-client-handover.md) — what the
  handover message contains and why
- [Client Onboarding Wizard](../product/client-onboarding-wizard.md)
