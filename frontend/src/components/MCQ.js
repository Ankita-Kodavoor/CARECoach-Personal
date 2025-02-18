import React, { useState, useEffect } from "react";
import axios from "axios";

const MCQ = ({ chatCode }) => {
  const [mcq, setMcq] = useState(null);
  const [selectedOption, setSelectedOption] = useState("");
  const [result, setResult] = useState("");

  useEffect(() => {
    axios.get(`/api/session/${chatCode}`)
      .then(response => {
        setMcq(response.data.mcq);
      })
      .catch(error => console.error("Error fetching MCQ:", error));
  }, [chatCode]);

  const handleSubmit = () => {
    if (!selectedOption) {
      setResult("⚠️ Please select an answer.");
      return;
    }

    axios.post("/api/submit-answer", {
      chatCode,
      selectedOption
    })
    .then(response => setResult(response.data.feedback))
    .catch(error => console.error("Error submitting answer:", error));
  };

  if (!mcq) return <p>Loading MCQ...</p>;

  return (
    <div className="card">
      <h2>{mcq.clientStatement}</h2>
      {mcq.options.map((option) => (
        <label key={option.id}>
          <input 
            type="radio" 
            name="mcq" 
            value={option.id} 
            onChange={() => setSelectedOption(option.id)} 
          />
          {option.text}
        </label>
      ))}
      <button onClick={handleSubmit}>Submit</button>
      <p><strong>{result}</strong></p>
    </div>
  );
};

export default MCQ;
