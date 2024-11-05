// src/components/PromptSelector.jsx
import React, { useState } from 'react';
import axios from 'axios';

function PromptSelector({ setSessionId }) {
  const [videoUrl, setVideoUrl] = useState('');
  const [prompt, setPrompt] = useState('');
  const [numGenerations, setNumGenerations] = useState(3);

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
    <div className="prompt-selector">
      <h2>Start New Summarization</h2>
      <input
        type="text"
        placeholder="Enter video URL"
        value={videoUrl}
        onChange={(e) => setVideoUrl(e.target.value)}
      />
      <textarea
        placeholder="Enter your prompt"
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
      />
      <input
        type="number"
        min="1"
        value={numGenerations}
        onChange={(e) => setNumGenerations(e.target.value)}
      />
      <button onClick={handleSubmit}>Process Video</button>
    </div>
  );
}

export default PromptSelector;