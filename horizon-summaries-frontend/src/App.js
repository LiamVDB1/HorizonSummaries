// src/App.js
import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import Home from './components/Home';
import Results from './components/Results';
import FinalSummary from './components/FinalSummary';
import 'bootstrap/dist/css/bootstrap.min.css';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/results/:sessionId" element={<Results />} />
        <Route path="/final-summary/:sessionId" element={<FinalSummary />} />
        <Route path="/" element={<Home />} />
      </Routes>
    </Router>
  );
}

export default App;