// src/components/Home.js
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Container, Form, Button, Alert } from 'react-bootstrap';
import { useNavigate } from 'react-router-dom';

const Home = () => {
  const [videoUrl, setVideoUrl] = useState('');
  const [prompt, setPrompt] = useState('');
  const [numGenerations, setNumGenerations] = useState(3);
  const [prompts, setPrompts] = useState([]);
  const [newPrompt, setNewPrompt] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    // Fetch prompts from backend
    axios.get('http://localhost:8000/get_prompts')
      .then(response => setPrompts(response.data))
      .catch(error => console.error('Error fetching prompts:', error));
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!videoUrl || !prompt || numGenerations < 1) {
      setError('Please fill in all fields correctly.');
      return;
    }
    try {
      const response = await axios.post('http://localhost:8000/process_video', {
        video_url: videoUrl,
        prompt,
        num_generations: numGenerations
      });
      const { session_id } = response.data;
      navigate(`/results/${session_id}`);
    } catch (err) {
      console.error('Error processing video:', err);
      setError('Failed to process video. Please try again.');
    }
  };

  const handleAddPrompt = async (e) => {
    e.preventDefault();
    if (!newPrompt.trim()) {
      setError('Prompt cannot be empty.');
      return;
    }
    try {
      await axios.post('http://localhost:8000/add_prompt', null, { params: { prompt: newPrompt } });
      setPrompts([...prompts, newPrompt]);
      setNewPrompt('');
      setError('');
    } catch (err) {
      console.error('Error adding prompt:', err);
      setError('Failed to add prompt. Please try again.');
    }
  };

  return (
    <Container className="mt-5">
      <h1 className="text-center mb-4">Transcription Summarizer</h1>
      {error && <Alert variant="danger">{error}</Alert>}
      <Form onSubmit={handleSubmit} className="mb-5">
        <Form.Group controlId="videoUrl" className="mb-3">
          <Form.Label>Enter .m3u8 Link:</Form.Label>
          <Form.Control
            type="text"
            value={videoUrl}
            onChange={(e) => setVideoUrl(e.target.value)}
            placeholder="https://example.com/video.m3u8"
            required
          />
        </Form.Group>
        <Form.Group controlId="prompt" className="mb-3">
          <Form.Label>Select Prompt:</Form.Label>
          <Form.Control as="select" value={prompt} onChange={(e) => setPrompt(e.target.value)} required>
            <option value="">-- Select a Prompt --</option>
            {prompts.map((p, index) => (
              <option key={index} value={p}>{p}</option>
            ))}
          </Form.Control>
        </Form.Group>
        <Form.Group controlId="numGenerations" className="mb-3">
          <Form.Label>Number of Generations:</Form.Label>
          <Form.Control
            type="number"
            value={numGenerations}
            onChange={(e) => setNumGenerations(Number(e.target.value))}
            min="1"
            max="10"
            required
          />
        </Form.Group>
        <Button variant="primary" type="submit">
          Process
        </Button>
      </Form>

      <h2 className="mb-3">Add a New Prompt</h2>
      <Form onSubmit={handleAddPrompt}>
        <Form.Group controlId="newPrompt" className="mb-3">
          <Form.Control
            as="textarea"
            rows={3}
            value={newPrompt}
            onChange={(e) => setNewPrompt(e.target.value)}
            placeholder="Enter your new prompt here..."
            required
          />
        </Form.Group>
        <Button variant="secondary" type="submit">
          Add Prompt
        </Button>
      </Form>
    </Container>
  );
};

export default Home;