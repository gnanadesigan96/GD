import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import SessionList from './pages/SessionList';
import SessionPlayer from './pages/SessionPlayer';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<SessionList />} />
        <Route path="/session/:id" element={<SessionPlayer />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);
