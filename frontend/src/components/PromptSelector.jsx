// src/components/PromptSelector.jsx
import React, { useState } from 'react';
import axios from 'axios';
import {
  TextField,
  Button,
  Paper,
  Typography,
  Grid,
  MenuItem,
} from '@mui/material';

function PromptSelector({ setSessionId }) {
  const [videoUrl, setVideoUrl] = useState('');
  const [prompt, setPrompt] = useState('');
  const [numGenerations, setNumGenerations] = useState(3);
  const [availablePrompts, setAvailablePrompts] = useState([]);
  const [selectedPromptId, setSelectedPromptId] = useState('');

  // Fetch prompts from the backend
  React.useEffect(() => {
    const fetchPrompts = async () => {
      try {
        const response = await axios.get('http://localhost:8000/get_prompts');
        setAvailablePrompts(response.data.prompts);
      } catch (error) {
        console.error('Error fetching prompts:', error);
      }
    };
    fetchPrompts();
  }, []);

  const handleSubmit = async () => {
    try {
      const response = await axios.post('http://localhost:8000/process_video', {
        video_url: videoUrl,
        prompt,
        num_generations: numGenerations,
      });
      setSessionId(response.data.session_id);
    } catch (error) {
      console.error('Error starting processing:', error);
    }
  };

  return (
    <Paper elevation={3} style={{ padding: '20px', marginBottom: '20px' }}>
      <Typography variant="h5" gutterBottom>
        Start New Summarization
      </Typography>
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
            onChange={(e) => {
              setSelectedPromptId(e.target.value);
              const selectedPrompt = availablePrompts.find(
                (p) => p.id === e.target.value
              );
              setPrompt(selectedPrompt ? selectedPrompt.text : '');
            }}
          >
            {availablePrompts.map((prompt) => (
              <MenuItem key={prompt.id} value={prompt.id}>
                {prompt.name}
              </MenuItem>
            ))}
          </TextField>
        </Grid>
        <Grid item xs={12}>
          <TextField
            label="Or Enter Custom Prompt"
            variant="outlined"
            multiline
            rows={4}
            fullWidth
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
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
        <Grid item xs={12} sm={6} style={{ display: 'flex', alignItems: 'center' }}>
          <Button
            variant="contained"
            color="primary"
            fullWidth
            onClick={handleSubmit}
          >
            Process Video
          </Button>
        </Grid>
      </Grid>
    </Paper>
  );
}

export default PromptSelector;