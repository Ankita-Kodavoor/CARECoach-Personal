import React, { useState, useEffect } from "react";
import axios from "axios";

const KnowledgeBite = ({ chatCode }) => {
  const [knowledgeBite, setKnowledgeBite] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get(`/api/session/${chatCode}`)
      .then(response => {
        setKnowledgeBite(response.data.knowledgeBite);
        setLoading(false);
      })
      .catch(error => {
        console.error("Error fetching knowledge bite:", error);
        setLoading(false);
      });
  }, [chatCode]);

  if (loading) return <p>Loading knowledge bite...</p>;
  if (!knowledgeBite) return <p>No knowledge bite available.</p>;

  return (
    <div className="card">
      <h2>Knowledge Bite</h2>
      <p><strong>Concept:</strong> {knowledgeBite.concept}</p>
      <p><strong>Description:</strong> {knowledgeBite.description}</p>
    </div>
  );
};

export default KnowledgeBite;
