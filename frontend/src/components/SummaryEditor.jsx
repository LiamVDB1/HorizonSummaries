// src/components/SummaryEditor.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Paper,
  Typography,
  TextField,
  Button,
  Grid,
} from '@mui/material';

function SummaryEditor({ sessionId }) {
  const [summaries, setSummaries] = useState([]);
  const [finalSummary, setFinalSummary] = useState('');

  useEffect(() => {
    const fetchSummaries = async () => {
      try {
        const response = await axios.get(
          `http://localhost:8000/get_results/${sessionId}`
        );
        setSummaries(response.data.summaries);
      } catch (error) {
        console.error('Error fetching summaries:', error);
      }
    };

    fetchSummaries();
  }, [sessionId]);

  const handleSave = async () => {
    try {
      await axios.post(
        `http://localhost:8000/save_final_summary/${sessionId}`,
        { final_summary: finalSummary }
      );
      alert('Final summary saved successfully.');
    } catch (error) {
      console.error('Error saving final summary:', error);
    }
  };

  return (
    <Paper elevation={3} style={{ padding: '20px', marginBottom: '20px' }}>
      <Typography variant="h5" gutterBottom>
        Generated Summaries
      </Typography>
      <Grid container spacing={2}>
          {Object.entries(summaries).map(([label, summary], index) => (
            <Grid item xs={12} sm={6} key={index}>
              <TextField
                label={label}
                variant="outlined"
                multiline
                rows={6}
                fullWidth
                value={summary}
                InputProps={{
                  readOnly: true,
                }}
              />
            </Grid>
          ))}
      </Grid>
      <Typography variant="h6" style={{ marginTop: '20px' }}>
        Final Summary
      </Typography>
      <TextField
        variant="outlined"
        multiline
        rows={6}
        fullWidth
        value={finalSummary}
        onChange={(e) => setFinalSummary(e.target.value)}
        style={{ marginBottom: '20px' }}
      />
      <Button variant="contained" color="primary" onClick={handleSave}>
        Save Final Summary
      </Button>
    </Paper>
  );
}

export default SummaryEditor;