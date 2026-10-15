import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { App } from './App';
import { Sesion } from './auth/Sesion';
import { configurarAWS } from './config';
import './styles.css';

configurarAWS();
const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false, refetchOnWindowFocus: false },
    mutations: { retry: false },
  },
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <Sesion>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </Sesion>
    </QueryClientProvider>
  </React.StrictMode>,
);
