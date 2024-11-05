// src/components/SummaryEditor.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';

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
    <div className="summary-editor">
      <h2>Summaries</h2>
      <div className="summaries">
        {summaries.map((summary, index) => (
          <textarea
            key={index}
            defaultValue={summary}
            readOnly
          />
        ))}
      </div>
      <h3>Final Summary</h3>
      <textarea
        value={finalSummary}
        onChange={(e) => setFinalSummary(e.target.value)}
      />
      <button onClick={handleSave}>Save Final Summary</button>
    </div>
  );
}

export default SummaryEditor;