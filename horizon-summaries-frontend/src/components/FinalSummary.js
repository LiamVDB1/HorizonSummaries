// src/components/FinalSummary.js
import React, { useState } from 'react';
import axios from 'axios';
import { Container, Form, Button, Alert } from 'react-bootstrap';

const FinalSummary = ({ match, history }) => {
  const { sessionId } = match.params;
  const [finalSummary, setFinalSummary] = useState('');
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');

  const handleSave = async () => {
    try {
      await axios.post('http://localhost:8000/save_final_summary', {
        session_id: sessionId,
        final_summary: finalSummary
      });
      setStatus('Final summary saved successfully!');
    } catch (err) {
      console.error('Error saving final summary:', err);
      setError('Failed to save final summary. Please try again.');
    }
  };

  return (
    <Container className="mt-5">
      <h1>Final Summary</h1>
      {status && <Alert variant="success">{status}</Alert>}
      {error && <Alert variant="danger">{error}</Alert>}
      <Form.Group controlId="finalSummary">
        <Form.Label>Write your final summary:</Form.Label>
        <Form.Control
          as="textarea"
          rows={10}
          value={finalSummary}
          onChange={(e) => setFinalSummary(e.target.value)}
        />
      </Form.Group>
      <Button variant="primary" onClick={handleSave} className="mt-3">
        Save Final Summary
      </Button>
      <Button variant="secondary" onClick={() => history.push('/')} className="mt-3 ml-3">
        Start New
      </Button>
    </Container>
  );
};

export default FinalSummary;