// src/components/TranscriptionViewer.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Paper,
  Typography,
  TextField,
  List,
  ListItem,
  ListItemText,
  CircularProgress,
} from '@mui/material';

function TranscriptionViewer({ sessionId }) {
  const [transcription, setTranscription] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [matchingLines, setMatchingLines] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchTranscription = async () => {
      try {
        let status;
        do {
          const statusResponse = await axios.get(
            `http://localhost:8000/get_status/${sessionId}`
          );
          status = statusResponse.data.status;
          if (status === 'completed') {
            const resultResponse = await axios.get(
              `http://localhost:8000/get_results/${sessionId}`
            );
            setTranscription(resultResponse.data.transcription);
            setLoading(false);
          } else if (status === 'error') {
            setLoading(false);
            console.error('Error processing transcription');
            break;
          } else {
            await new Promise((resolve) => setTimeout(resolve, 2000));
          }
        } while (status !== 'completed');
      } catch (error) {
        setLoading(false);
        console.error('Error fetching transcription:', error);
      }
    };

    fetchTranscription();
  }, [sessionId]);

  const handleSearchChange = async (e) => {
    setSearchTerm(e.target.value);
    if (e.target.value.trim() === '') {
      setMatchingLines([]);
      return;
    }
    try {
      const response = await axios.post(
        `http://localhost:8000/search_transcription/${sessionId}`,
        { search_term: e.target.value }
      );
      setMatchingLines(response.data.matching_lines);
    } catch (error) {
      console.error('Error searching transcription:', error);
    }
  };

  return (
    <Paper elevation={3} style={{ padding: '20px', marginBottom: '20px' }}>
      <Typography variant="h5" gutterBottom>
        Transcription
      </Typography>
      {loading ? (
        <div style={{ textAlign: 'center' }}>
          <CircularProgress />
          <Typography variant="body1">Processing...</Typography>
        </div>
      ) : (
        <>
          <TextField
            label="Search Transcription"
            variant="outlined"
            fullWidth
            value={searchTerm}
            onChange={handleSearchChange}
            style={{ marginBottom: '20px' }}
          />
          {matchingLines.length > 0 ? (
            <List>
              {matchingLines.map((line, index) => (
                <ListItem key={index}>
                  <ListItemText primary={line} />
                </ListItem>
              ))}
            </List>
          ) : (
            <Typography variant="body1" style={{ whiteSpace: 'pre-wrap' }}>
              {transcription}
            </Typography>
          )}
        </>
      )}
    </Paper>
  );
}

export default TranscriptionViewer;