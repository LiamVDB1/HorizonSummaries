// src/components/Results.js
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Container, Spinner, Card, Button, Form, Alert } from 'react-bootstrap';
import { Link, useParams } from 'react-router-dom';

const Results = ({ match, history }) => {
  const { sessionId } = useParams();
  const [status, setStatus] = useState('processing');
  const [summaries, setSummaries] = useState([]);
  const [transcription, setTranscription] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    const checkStatus = async () => {
      try {
        const response = await axios.get(`http://localhost:8000/get_status/${sessionId}`);
        setStatus(response.data.status);
        if (response.data.status === 'completed') {
          const resultResponse = await axios.get(`http://localhost:8000/get_results/${sessionId}`);
          setSummaries(resultResponse.data.summaries);
          setTranscription(resultResponse.data.transcription);
        } else if (response.data.status === 'error') {
          setError('An error occurred during processing.');
        } else if (response.data.status === 'not_found') {
          setError('Session not found.');
        }
      } catch (err) {
        console.error('Error checking status:', err);
        setError('Failed to check status. Please try again.');
      }
    };
    const interval = setInterval(checkStatus, 5000);
    checkStatus();
    return () => clearInterval(interval);
  }, [sessionId]);

  const handleFinalize = () => {
    history.push(`/final-summary/${sessionId}`);
  };

  if (error) {
    return (
      <Container className="mt-5">
        <Alert variant="danger">{error}</Alert>
      </Container>
    );
  }

  if (status === 'processing') {
    return (
      <Container className="mt-5 text-center">
        <h1>Your request is being processed...</h1>
        <Spinner animation="border" variant="primary" className="mt-4" />
      </Container>
    );
  }

  return (
    <Container className="mt-5">
      <h1>Generated Summaries</h1>
      <div className="row">
        {summaries.map((summary, index) => (
          <div className="col-md-4 mb-3" key={index}>
            <Card>
              <Card.Header>Summary {index + 1}</Card.Header>
              <Card.Body>
                <Form.Control as="textarea" rows={5} defaultValue={summary} readOnly />
              </Card.Body>
            </Card>
          </div>
        ))}
      </div>
      <Button variant="success" onClick={handleFinalize} className="mt-3">
        Create Final Summary
      </Button>

      <h2 className="mt-5">Full Transcription</h2>
      <div className="border p-3">
        {transcription}
      </div>
    </Container>
  );
};

export default Results;