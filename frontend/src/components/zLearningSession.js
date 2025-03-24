import React, { useEffect, useState } from 'react';
import '../styles/LearningStyles.css';
import Freeform from './Freeform';
import './styles/tailwind.css';

const LearningSession = ({ sessionData, onBack }) => {
  const [sessionUserData, setSessionUserData] = useState(null);

  useEffect(() => {
    // When sessionData changes, fetch the full session details from the database
    if (sessionData && sessionData.practicesession_id) {
      fetchSessionDetails(sessionData.practicesession_id);
    }
  }, [sessionData]);

  const fetchSessionDetails = async (practiceSessionId) => {
    try {
      // Try to get database connection
      const response = await fetch(`/api/debug`);
      if (!response.ok) {
        throw new Error('Failed to connect to server');
      }
      
      // Set the session data with what we have from the parent component
      setSessionUserData(sessionData);
    } catch (error) {
      console.error('Error fetching session details:', error);
    }
  };

  if (!sessionData || !sessionData.practicesession_id) {
    return (
      <div className="learning-session-container">
        <div className="error-message">
          No valid session data available. Please select a different session.
        </div>
        <button onClick={onBack} className="back-button">
          Back to Sessions
        </button>
      </div>
    );
  }

  return (
    <div className="learning-session-container">
      {/* <h1>Practice Session {sessionData.practicesession_id}</h1> */}
      <div className="session-info">
        <p>
          <strong>User ID:</strong> {sessionData.user_id || "N/A"} |{" "}
          <strong>Skill Focus:</strong> {sessionData.target_subskill || "Open-ended questions"}
        </p>
      </div>

      <div className="cards-container-freeform">
          {/* Pass both practicesession_id and user_id to Freeform */}
          <Freeform 
            practicesession_id={sessionData.practicesession_id} 
            user_id={sessionData.user_id} 
          />
       
      </div>

      <button onClick={onBack} className="back-button">
        Back to Sessions
      </button>
    </div>
  );
};

export default LearningSession;