import React from "react";
import KnowledgeBite from "./components/KnowledgeBite";
import MCQ from "./components/MCQ";

function App() {
  return (
    <div className="container">
      <h1>Learning App</h1>
      <KnowledgeBite chatCode="dummy_chat_001" />
      <MCQ chatCode="dummy_chat_001" />
    </div>
  );
}

export default App;
