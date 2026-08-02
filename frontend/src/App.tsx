import { AuthProvider } from './auth/AuthContext';
import { I18nProvider } from './i18n';
import { ThemeProvider } from './theme';
import { ToastProvider } from './components/feedback/ToastProvider';
import AppRoutes from './routes/AppRoutes';

export default function App() {
  return (
    <ThemeProvider>
      <I18nProvider>
        <AuthProvider>
          <ToastProvider>
            <AppRoutes />
          </ToastProvider>
        </AuthProvider>
      </I18nProvider>
    </ThemeProvider>
  );
}
