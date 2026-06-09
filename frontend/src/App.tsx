import { AuthProvider } from './auth/AuthContext';
import { I18nProvider } from './i18n';
import AppRoutes from './routes/AppRoutes';

export default function App() {
  return (
    <I18nProvider>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </I18nProvider>
  );
}
