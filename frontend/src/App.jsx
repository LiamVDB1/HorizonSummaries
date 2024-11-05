// src/App.jsx
import React, { useState } from 'react';
import PromptSelector from './components/PromptSelector';
import TranscriptionViewer from './components/TranscriptionViewer';
import SummaryEditor from './components/SummaryEditor';

function App() {
  const [sessionId, setSessionId] = useState(null);

  return (
    <div className="app-container">
      <h1>Your Video Summarization Tool</h1>
      <PromptSelector setSessionId={setSessionId} />
      {sessionId && (
        <>
          <TranscriptionViewer sessionId={sessionId} />
          <SummaryEditor sessionId={sessionId} />
        </>
      )}
    </div>
  );
}

export default App;