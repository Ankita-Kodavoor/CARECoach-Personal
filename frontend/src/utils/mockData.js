const exampleData = {
    practicesession_id: 1,
    
    knowledgeBite: {
      practicesession_id: 1,
      generated_knowledge_bite: "React components are reusable pieces of code that return React elements describing what should appear on the screen. Components can be defined as functions or classes. Function components are simpler and more modern, while class components provide additional features like lifecycle methods. Each component should ideally follow the single responsibility principle, handling only one aspect of the UI.",
      timestamp: "2025-02-17T14:32:00Z",
      helpful: true
    },
    
    mcq: {
      practicesession_id: 1,
      generated_mcq: "What is the main advantage of using function components over class components in modern React development?",
      optionA: "Function components can use state while class components cannot",
      optionB: "Function components are simpler and can use hooks",
      optionC: "Function components automatically optimize rendering",
      mcq_correct_answer: "B",
      mcq_answer_recorded: null,
      mcq_feedback: "Function components are indeed simpler and, with the introduction of Hooks in React 16.8, they can use state and other React features that were previously only available in class components. This has made function components the preferred way to write components in modern React development.",
      mcq_generated_time: "2025-02-17T14:35:00Z",
      mcq_activity_time: null
    }
  };
  
  export default exampleData;