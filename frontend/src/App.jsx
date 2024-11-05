// src/App.jsx
import React, { useState } from 'react';
import { Container, Typography } from '@mui/material';
import PromptSelector from './components/PromptSelector';
import TranscriptionViewer from './components/TranscriptionViewer';
import SummaryEditor from './components/SummaryEditor';

function App() {
  const [sessionId, setSessionId] = useState(null);

  return (
    <Container maxWidth="lg">
      <Typography variant="h3" align="center" gutterBottom>
        Horizon Summaries
      </Typography>
      <PromptSelector setSessionId={setSessionId} />
      {sessionId && (
        <>
          <TranscriptionViewer sessionId={sessionId} />
          <SummaryEditor sessionId={sessionId} />
        </>
      )}
    </Container>
  );
}

export default App;