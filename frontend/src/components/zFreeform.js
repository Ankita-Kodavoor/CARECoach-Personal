import React, { useState, useEffect, useRef } from 'react';
import '../styles/LearningStyles.css';

// Function to format message text with bold tags and newlines
const formatMessageText = (text, onOptionClick) => {
  if (!text) return '';
  
  // Check if the text contains option patterns
  const optionPattern = /Option [A-Z]:\s*(.*?)(?=Option [A-Z]:|$)/gs;
  const hasOptions = text.match(/Option [A-Z]/g)?.length >= 2;
  
  if (hasOptions) {
    // Extract the text before the options
    const beforeOptions = text.split(/Option [A-Z]:/)[0].trim();
    
    // Find all options
    const options = [];
    let match;
    while ((match = optionPattern.exec(text)) !== null) {
      const optionLetter = text.substring(match.index, match.index + 8).trim();
      const optionText = match[1].trim();
      options.push({ letter: optionLetter, text: optionText });
    }
    
    // Return formatted content with options as bubbles
    return (
      <>
        {beforeOptions && (
          <div className="message-regular-text">
            {formatRegularText(beforeOptions)}
          </div>
        )}
        <div className="options-container" style={{ 
          display: 'flex', 
          flexDirection: 'column', 
          gap: '10px',
          marginTop: '10px' 
        }}>
          {options.map((option, index) => (
            <div 
              key={index} 
              className="option-bubble" 
              style={{
                backgroundColor: '#f0f4f8',
                borderRadius: '12px',
                padding: '10px 15px',
                boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
                border: '1px solid #e1e4e8',
                cursor: 'pointer',
                transition: 'transform 0.2s, background-color 0.2s',
                maxWidth: '85%',
                alignSelf: 'flex-start'
              }}
              onClick={() => onOptionClick && onOptionClick(`${option.letter} ${option.text}`)}
              onMouseOver={(e) => e.currentTarget.style.transform = 'scale(1.02)'}
              onMouseOut={(e) => e.currentTarget.style.transform = 'scale(1)'}
            >
              <div style={{ display: 'flex', alignItems: 'center' }}>
                <span style={{ fontWeight: 'bold', marginRight: '8px' }}>{option.letter}</span>
                <span>{formatRegularText(option.text)}</span>
              </div>
            </div>
          ))}
        </div>
      </>
    );
  }
  
  // If no options, process normally
  return formatRegularText(text);
};

// Helper function for regular text formatting (bold and newlines)
const formatRegularText = (text) => {
  if (!text) return '';
  
  // Remove unwanted < and > characters that aren't part of formatting tags
  // Replace standalone < or > that aren't part of a tag with empty string
  const cleanedText = text.replace(/(?<!\<[^\>]+)\<(?!\s*[^\<]+\>)/g, "").replace(/(?<!\<[^\>]+)\>(?!\s*[^\<]+\>)/g, "");
  
  // First split by newlines to handle \n
  return cleanedText.split('\n').map((line, lineIndex) => {
    // For each line, process the <> tags for bold formatting
    const formattedLine = line.split(/<([^>]+)>/).map((part, partIndex) => {
      // Even indices are regular text, odd indices are the content between < >
      return partIndex % 2 === 0 ? part : <strong key={`part-${lineIndex}-${partIndex}`}>{part}</strong>;
    });
    
    // Return each line with appropriate React elements
    return (
      <React.Fragment key={`line-${lineIndex}`}>
        {lineIndex > 0 && <br />}{/* No space between elements */}
        {formattedLine}
      </React.Fragment>
    );
  });
};

// Freeform component with utterance rewind display using existing styles
const Freeform = ({ practicesession_id, user_id }) => {
  const [messages, setMessages] = useState([]);
  const [currentMessage, setCurrentMessage] = useState("");
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [utteranceRewind, setUtteranceRewind] = useState([]);
  const messagesEndRef = useRef(null);
  const webSocketRef = useRef(null);
  const connectionAttemptedRef = useRef(false);
  const textareaRef = useRef(null);
  
  // Scroll to bottom of messages
  const scrollToBottom = () => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Handle text input when entered into text box
  const handleMessageChange = (e) => {
    setCurrentMessage(e.target.value);
  };
  
  // Handle key press in the textarea
  const handleKeyPress = (e) => {
    // Check if Enter was pressed without Shift key
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault(); // Prevent default behavior (new line)
      if (currentMessage.trim() !== '' && isConnected && !isLoading) {
        sendMessage(e); // Send the message
      }
    }
  };
  
  // Handle option click - sends the option text as a message
  const handleOptionClick = (optionText) => {
    if (!isConnected || isLoading) return;
    
    // Set the message text
    setCurrentMessage(optionText);
    
    // Send it automatically
    setTimeout(() => {
      if (webSocketRef.current && webSocketRef.current.readyState === WebSocket.OPEN) {
        // Add user message to UI immediately
        setMessages(prev => [...prev, {
          text: optionText,
          isUser: true,
          timestamp: new Date(),
          id: `user-${Date.now()}`
        }]);
        
        // Set loading state
        setIsLoading(true);
        
        // Send via WebSocket
        webSocketRef.current.send(optionText);
        
        // Clear the input
        setCurrentMessage("");
      }
    }, 0);
  };
  
  // Fetch utterance rewind
  useEffect(() => {
    if (!practicesession_id) return;
    
    // Fetch the utterance rewind from the server
    const fetchUtteranceRewind = async () => {
      try {
        const response = await fetch(`/api/utterance-rewind/${practicesession_id}`);
        if (response.ok) {
          const data = await response.json();
          if (data.success && data.utteranceRewind) {
            try {
              // Parse the JSON string into an array of objects
              const rewindData = JSON.parse(data.utteranceRewind);
              setUtteranceRewind(rewindData);
            } catch (parseError) {
              console.error("Error parsing utterance rewind JSON:", parseError);
              setUtteranceRewind([]);
            }
          }
        } else {
          console.error("Failed to fetch utterance rewind");
        }
      } catch (error) {
        console.error("Error fetching utterance rewind:", error);
      }
    };
    
    fetchUtteranceRewind();
  }, [practicesession_id]);

  // Setup WebSocket connection
  useEffect(() => {
    // Only attempt connection once
    if (connectionAttemptedRef.current) return;
    if (!practicesession_id) {
      console.error("No practicesession_id provided");
      return;
    }
    
    connectionAttemptedRef.current = true;
    console.log(`Connecting to WebSocket with practicesession_id: ${practicesession_id}`);
    
    // Create WebSocket connection
    const wsProtocol = window.location.protocol === "https:" ? "wss://" : "ws://";
    // Use current hostname with port 5000
    const wsUrl = `${wsProtocol}${window.location.hostname}:5000/ws/session/${practicesession_id}`;
    
    console.log("Attempting WebSocket connection to:", wsUrl);
    
    const ws = new WebSocket(wsUrl);
    webSocketRef.current = ws;

    ws.onopen = () => {
      console.log("WebSocket Connected!");
      setIsConnected(true);
      // Focus on the textarea after connection
      if (textareaRef.current) {
        textareaRef.current.focus();
      }
    };

    ws.onerror = (error) => {
      console.error("WebSocket Error:", error);
      setIsConnected(false);
      setMessages(prev => [...prev, {
        text: "Error connecting to the server. Please try again later.",
        isUser: false,
        timestamp: new Date(),
        id: `error-${Date.now()}`
      }]);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("Message received:", data);

        setMessages(prev => [...prev, {
          text: data.message,
          isUser: false,
          timestamp: new Date(data.timestamp || Date.now()),
          id: `system-${Date.now()}-${Math.random()}`
        }]);
        
        setIsLoading(false);
        
        // Focus on textarea after receiving a message
        if (textareaRef.current) {
          textareaRef.current.focus();
        }
      } catch (error) {
        console.error("Error parsing message:", error);
        setIsLoading(false);
      }
    };

    ws.onclose = (event) => {
      console.log(`WebSocket Disconnected. Code: ${event.code}`);
      setIsConnected(false);
    };

    return () => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close(1000, "Component unmounting");
      }
    };
  }, [practicesession_id]);

  // Send message function
  const sendMessage = (e) => {
    e.preventDefault();
    if (currentMessage.trim() === "" || !isConnected || isLoading) return;

    const messageText = currentMessage.trim();
    setIsLoading(true);

    // Add user message to UI immediately
    setMessages(prev => [...prev, {
      text: messageText,
      isUser: true,
      timestamp: new Date(),
      id: `user-${Date.now()}`
    }]);

    // Send via WebSocket
    if (webSocketRef.current && webSocketRef.current.readyState === WebSocket.OPEN) {
      webSocketRef.current.send(messageText);
    } else {
      console.error("WebSocket is not open. Message not sent.");
      setMessages(prev => [...prev, {
        text: "Error: Connection lost. Please refresh the page.",
        isUser: false,
        timestamp: new Date(),
        id: `error-${Date.now()}`
      }]);
      setIsLoading(false);
    }

    // Reset input
    setCurrentMessage("");
  };

  return (
    <div className="chat-container">
      {utteranceRewind.length > 0 && (
        <div className="chat-messages" style={{ marginBottom: '20px', maxHeight: '200px', overflowY: 'auto' }}>
          <h4 style={{ padding: '10px', margin: '0', backgroundColor: '#f0f0f0', borderRadius: '5px 5px 0 0' }}>Previous Conversation Context:</h4>
          
          {utteranceRewind.map((item, index) => (
            <div
              key={item.id || index}
              className={`message-item ${item.role.toLowerCase() === 'helper' ? 'user' : 'system'}`}
              style={item.isTarget ? { backgroundColor: 'rgba(255, 248, 225, 0.3)' } : {}}
            >
              <div className="message-bubble">
                <div className="message-role">
                  {item.role}
                  {item.isTarget && " (Focus on this response)"}
                </div>
                <div className="message-text">
                  {formatMessageText(item.utterance)}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    
      <div className="chat-messages">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`message-item ${message.isUser ? 'user' : 'system'}`}
          >
            <div className="message-bubble">
              <div className="message-role">
                {message.isUser ? 'You' : 'Practice Mentor'}
              </div>
              <div className="message-text">
                {message.isUser ? 
                  formatRegularText(message.text) : 
                  formatMessageText(message.text, handleOptionClick)}
              </div>
              <div className="message-time">
                {message.timestamp instanceof Date && !isNaN(message.timestamp)
                  ? message.timestamp.toLocaleTimeString([], { 
                      hour: '2-digit', 
                      minute: '2-digit' 
                    })
                  : "Invalid Time"}
              </div>
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={sendMessage} className="chat-input-form">
        <div className="chat-input-container">
          <textarea
            ref={textareaRef}
            value={currentMessage}
            onChange={handleMessageChange}
            onKeyPress={handleKeyPress}
            placeholder="Type your message here... (Press Enter to send, Shift+Enter for new line)"
            className="chat-input"
            disabled={!isConnected || isLoading}
          />
        </div>
        <button 
          type="submit" 
          className="submit-button"
          disabled={!isConnected || isLoading || currentMessage.trim() === ""}
        >
          {isLoading ? "Sending..." : "Send"}
        </button>
      </form>
      
      {!isConnected && messages.length === 0 && (
        <div className="connection-status-container">
          <div className="auto-reconnect-indicator">
            <div className="loading-animals">
              <span className="animal">🐱</span>
              <span className="animal">🐶</span>
              <span className="animal">🐰</span>
            </div>
            <span>Connecting...</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default Freeform;