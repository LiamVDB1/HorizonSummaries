// src/components/TranscriptionViewer.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import SearchBar from './SearchBar';

function TranscriptionViewer({ sessionId }) {
  const [transcription, setTranscription] = useState('');
  const [searchResults, setSearchResults] = useState([]);

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
          } else {
            await new Promise((resolve) => setTimeout(resolve, 2000));
          }
        } while (status !== 'completed');
      } catch (error) {
        console.error('Error fetching transcription:', error);
      }
    };

    fetchTranscription();
  }, [sessionId]);

  const handleSearch = async (searchTerm) => {
    try {
      const response = await axios.post(
        `http://localhost:8000/search_transcription/${sessionId}`,
        { search_term: searchTerm }
      );
      setSearchResults(response.data.matching_lines);
    } catch (error) {
      console.error('Error searching transcription:', error);
    }
  };

  return (
    <div className="transcription-viewer">
      <h2>Transcription</h2>
      <SearchBar onSearch={handleSearch} />
      {searchResults.length > 0 ? (
        <div>
          <h3>Search Results:</h3>
          <ul>
            {searchResults.map((line, index) => (
              <li key={index}>{line}</li>
            ))}
          </ul>
        </div>
      ) : (
        <pre>{transcription}</pre>
      )}
    </div>
  );
}

export default TranscriptionViewer;