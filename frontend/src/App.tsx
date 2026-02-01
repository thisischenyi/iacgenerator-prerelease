import { ThemeProvider } from '@mui/material/styles';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import MainLayout from './components/layout/MainLayout';
import theme from './theme';
import ChatPage from './pages/ChatPage';
import UploadPage from './pages/UploadPage';
import PolicyPage from './pages/PolicyPage';
import SettingsPage from './pages/SettingsPage';

function App() {
  return (
    <ThemeProvider theme={theme}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<MainLayout />}>
            <Route index element={<ChatPage />} />
            <Route path="upload" element={<UploadPage />} />
            <Route path="policies" element={<PolicyPage />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;
