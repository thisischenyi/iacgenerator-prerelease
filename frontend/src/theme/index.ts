import { createTheme } from '@mui/material/styles';

// Accenture brand colors
export const brandColors = {
  purple: '#A100FF',
  purpleDark: '#8800D6',
  purpleLight: '#D080FF',
  black: '#000000',
  white: '#FFFFFF',
  gray: '#F2F2F2',
  textPrimary: '#1A1A1A',
  textSecondary: '#666666',
};

const theme = createTheme({
  palette: {
    primary: {
      main: brandColors.purple,
      dark: brandColors.purpleDark,
      light: brandColors.purpleLight,
      contrastText: '#fff',
    },
    secondary: {
      main: '#000000', // Accenture secondary is often black
    },
    background: {
      default: '#F8F9FA', // Light gray background
      paper: '#FFFFFF',
    },
    text: {
      primary: brandColors.textPrimary,
      secondary: brandColors.textSecondary,
    },
  },
  typography: {
    fontFamily: '"Graphik", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      fontWeight: 700,
      fontSize: '2.5rem',
    },
    h2: {
      fontWeight: 700,
      fontSize: '2rem',
    },
    h3: {
      fontWeight: 600,
      fontSize: '1.75rem',
    },
    h4: {
      fontWeight: 600,
      fontSize: '1.5rem',
    },
    h5: {
      fontWeight: 600,
      fontSize: '1.25rem',
    },
    h6: {
      fontWeight: 600,
      fontSize: '1rem',
    },
    button: {
      fontWeight: 600,
      textTransform: 'none', // No uppercase buttons
    },
  },
  shape: {
    borderRadius: 8,
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 24, // Pill-shaped buttons
          padding: '8px 24px',
          boxShadow: 'none',
          '&:hover': {
            boxShadow: '0 4px 12px rgba(161, 0, 255, 0.2)',
          },
        },
        containedPrimary: {
          background: `linear-gradient(45deg, ${brandColors.purple} 30%, ${brandColors.purpleLight} 90%)`,
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.05)',
          borderRadius: 16,
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          boxShadow: '0 2px 10px rgba(0, 0, 0, 0.05)',
          backgroundColor: '#FFFFFF',
          color: '#000000',
        },
      },
    },
  },
});

export default theme;
