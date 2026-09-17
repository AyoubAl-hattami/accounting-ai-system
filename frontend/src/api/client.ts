import axios from 'axios';
import { getToken } from '../auth/token';
import { apiBaseUrl } from './baseUrl';

const apiClient = axios.create({
  baseURL: apiBaseUrl,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use((config) => {
  const token = getToken();

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

/* The sign-in request is the one place a 401 does not mean "your session ended".
   It means the email or password was wrong, and the login form is already
   showing that. Treating it as an expired session sent the browser to /login
   with a full page load, which unmounted the form and discarded the message it
   had just set -- so a failed sign-in appeared to do nothing at all.

   /auth/login is the only route that answers 401 for a reason other than a dead
   session. */
const SIGN_IN_PATH = '/auth/login';

export function isExpiredSession(error: unknown): boolean {
  const failure = error as {
    response?: { status?: number };
    config?: { url?: string };
  } | null;

  if (failure?.response?.status !== 401) {
    return false;
  }

  const path = (failure.config?.url ?? '').split('?')[0].replace(/\/+$/, '');
  return !path.endsWith(SIGN_IN_PATH);
}

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (isExpiredSession(error)) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }

    return Promise.reject(error);
  },
);

export default apiClient;
