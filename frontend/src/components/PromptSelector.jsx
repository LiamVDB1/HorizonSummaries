// src/components/PromptSelector.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  TextField,
  Button,
  Paper,
  Typography,
  Grid,
  MenuItem,
  Alert,
  CircularProgress,
} from '@mui/material';

function PromptSelector({ setSessionId }) {
  const [videoUrl, setVideoUrl] = useState('');
  const [promptContent, setPromptContent] = useState('');
  const [numGenerations, setNumGenerations] = useState(3);
  const [availablePrompts, setAvailablePrompts] = useState([]);
  const [selectedPromptId, setSelectedPromptId] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const REACT_APP_BACKEND_URL = "http://localhost:8000";

  // Fetch prompts from the backend
  useEffect(() => {
    const fetchPrompts = async () => {
      try {
        const response = await axios.get(`${REACT_APP_BACKEND_URL}/get_prompts`);
        setAvailablePrompts(response.data);
      } catch (err) {
        console.error('Error fetching prompts:', err);
        setError('Failed to load prompts. Please try again later.');
      }
    };
    fetchPrompts();
  }, []);

  const handleSubmit = async () => {
    // Basic validation
    if (!videoUrl.trim()) {
      setError('Video URL is required.');
      return;
    }

    /*
    if (!promptContent.trim()) {
      setError('Prompt is required.');
      return;
    }*/

    setError('');
    setLoading(true);

    try {
      const response = await axios.post(`${REACT_APP_BACKEND_URL}/process_video`, {
        video_url: videoUrl,
        prompt: promptContent,
        num_generations: numGenerations,
      });
      setSessionId(response.data.session_id);
    } catch (err) {
      console.error('Error starting processing:', err);
      setError('Failed to process video. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handlePromptSelection = (e) => {
    const selectedId = e.target.value;
    setSelectedPromptId(selectedId);
    if (selectedId) {
      const selectedPrompt = availablePrompts.find((p) => p.id === selectedId);
      setPromptContent(selectedPrompt ? selectedPrompt.content : '');
    } else {
      setPromptContent('');
    }
  };

  const handleCustomPromptChange = (e) => {
    setPromptContent(e.target.value);
    if (e.target.value) {
      setSelectedPromptId('');
    }
  };

  return (
    <Paper elevation={3} sx={{ padding: 3, marginBottom: 3 }}>
      <Typography variant="h5" gutterBottom>
        Start New Summarization
      </Typography>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      <Grid container spacing={2}>
        <Grid item xs={12}>
          <TextField
            label="Video URL"
            variant="outlined"
            fullWidth
            value={videoUrl}
            onChange={(e) => setVideoUrl(e.target.value)}
          />
        </Grid>
        <Grid item xs={12}>
          <TextField
            label="Select Prompt"
            variant="outlined"
            select
            fullWidth
            value={selectedPromptId}
            onChange={handlePromptSelection}
          >
            <MenuItem value="">
              <em>None</em>
            </MenuItem>
            {availablePrompts.map((prompt) => (
              <MenuItem key={prompt.id} value={prompt.id}>
                {prompt.content}
              </MenuItem>
            ))}
          </TextField>
        </Grid>
        <Grid item xs={12}>
          <Typography align="center" variant="subtitle1">
            OR
          </Typography>
        </Grid>
        <Grid item xs={12}>
          <TextField
            label="Enter Custom Prompt"
            variant="outlined"
            multiline
            rows={4}
            fullWidth
            value={promptContent}
            onChange={handleCustomPromptChange}
            placeholder="Type your custom prompt here..."
          />
        </Grid>
        <Grid item xs={12} sm={6}>
          <TextField
            label="Number of Generations"
            type="number"
            variant="outlined"
            fullWidth
            inputProps={{ min: 1 }}
            value={numGenerations}
            onChange={(e) => setNumGenerations(Number(e.target.value))}
          />
        </Grid>
        <Grid item xs={12} sm={6} sx={{ display: 'flex', alignItems: 'center' }}>
          <Button
            variant="contained"
            color="primary"
            fullWidth
            onClick={handleSubmit}
            disabled={loading}
            startIcon={loading && <CircularProgress size={20} />}
          >
            {loading ? 'Processing...' : 'Process Video'}
          </Button>
        </Grid>
      </Grid>
    </Paper>
  );
}

export default PromptSelector;