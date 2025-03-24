import React from "react";

const Subskill = ({ subskill }) => {
  console.log("Subskill received:", subskill); // Debug log
  
  if (!subskill) {
    return <div className="card knowledge-bite-card">No subskill available</div>;
  }

  return (
    <div className="card knowledge-bite-card">
      <h2>💡 Tip </h2>
      <div className="knowledge-bite-content">
        <p className="knowledge-bite-text">Your concept to master is {subskill}</p>
      </div>
    </div>
  );
};

export default Subskill;