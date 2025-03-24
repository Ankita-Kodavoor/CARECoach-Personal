import React, { useState, useEffect, useRef } from 'react';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Textarea } from '../components/ui/textarea';
import { Loader2, Send } from 'lucide-react';

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
          <div className="text-base leading-relaxed">
            {formatRegularText(beforeOptions)}
          </div>
        )}
        <div className="flex flex-col gap-3 mt-3">
          {options.map((option, index) => (
            <div 
              key={index} 
              className="bg-white hover:bg-gray-50 rounded-xl p-3 shadow-sm border border-gray-200 cursor-pointer transition-all duration-200 w-full self-start hover:scale-105"
              onClick={() => onOptionClick && onOptionClick(`${option.letter} ${option.text}`)}
            >
              <div className="flex items-start">
                <Badge variant="outline" className="mr-3 text-black-500 flex-shrink-0">
                  {option.letter}
                </Badge>
                <span className="text-gray-800 text-base">{formatRegularText(option.text)}</span>
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

// Helper function for formatting bold tags and newlines
const formatBoldAndNewlines = (text, keyPrefix = 'part') => {
  // First split by newlines to handle \n
  return text.split('\n').map((line, lineIndex) => {
    // For each line, process the <> tags for bold formatting
    const formattedLine = line.split(/<([^>]+)>/).map((part, partIndex) => {
      // Even indices are regular text, odd indices are the content between < >
      return partIndex % 2 === 0 ? part : <strong key={`${keyPrefix}-${lineIndex}-${partIndex}`}>{part}</strong>;
    });
    
    // Return each line with appropriate React elements
    return (
      <React.Fragment key={`line-${keyPrefix}-${lineIndex}`}>
        {lineIndex > 0 && <br />}
        {formattedLine}
      </React.Fragment>
    );
  });
};

// Helper function for regular text formatting (bold and newlines)
const formatRegularText = (text) => {
  if (!text) return '';
  
  // Replace literal '\n' strings with actual newlines
  text = text.replace(/\\n/g, '\n');
  
  // Remove unwanted < and > characters that aren't part of formatting tags
  const cleanedText = text.replace(/(?<!\<[^\>]+)\<(?!\s*[^\<]+\>)/g, "").replace(/(?<!\<[^\>]+)\>(?!\s*[^\<]+\>)/g, "");
  
  // Process [[Patient Message]] pattern
  const patternRegex = /\[\[(.*?)\]\]/g;
  
  // Split by patient message pattern first
  const parts = [];
  let lastIndex = 0;
  let match;
  
  while ((match = patternRegex.exec(cleanedText)) !== null) {
    // Add text before the match
    if (match.index > lastIndex) {
      parts.push({
        type: 'regular',
        content: cleanedText.substring(lastIndex, match.index)
      });
    }
    
    // Add the matched content (without the brackets)
    parts.push({
      type: 'patientMessage',
      content: match[1]
    });
    
    lastIndex = match.index + match[0].length;
  }
  
  // Add remaining text after last match
  if (lastIndex < cleanedText.length) {
    parts.push({
      type: 'regular',
      content: cleanedText.substring(lastIndex)
    });
  }
  
  // If no patient message pattern was found, process normally
  if (parts.length === 0) {
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
          {lineIndex > 0 && <br />}
          {formattedLine}
        </React.Fragment>
      );
    });
  }
  
  // Format parts with patient messages
  return parts.map((part, partIndex) => {
    if (part.type === 'patientMessage') {
      return (
        <div 
          key={`patient-${partIndex}`}
          className="my-2 p-3 rounded-lg bg-gradient-to-br from-amber-400 to-amber-250 shadow-sm"
        >
          {formatBoldAndNewlines(part.content)}
        </div>
      );
    } else {
      return formatBoldAndNewlines(part.content, partIndex);
    }
  });
};

// Freeform component with utterance rewind display using shadcn/ui
const Freeform = ({ practicesession_id, user_id, onProgressUpdate }) => {
  const [messages, setMessages] = useState([]);
  const [currentMessage, setCurrentMessage] = useState("");
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [utteranceRewind, setUtteranceRewind] = useState([]);
  const messagesEndRef = useRef(null);
  const webSocketRef = useRef(null);
  const connectionAttemptedRef = useRef(false);
  const textareaRef = useRef(null);
  
  // Focus the textarea when component mounts
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  }, []);
  
  // Scroll to bottom of messages
  const scrollToBottom = () => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  };

  useEffect(() => {
    scrollToBottom();
    
    // Also focus the textarea after messages update
    if (textareaRef.current && !isLoading) {
      textareaRef.current.focus();
    }
  }, [messages, isLoading]);
  
  // Handle text input when entered into text box
  const handleMessageChange = (e) => {
    setCurrentMessage(e.target.value);
  };
  
  // Handle key press in the textarea - preserving original functionality
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

  // Setup WebSocket connection - preserving original WebSocket implementation
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
        
        // Trigger progress update if callback is provided
        // This will refresh the progress data when new messages arrive
        if (onProgressUpdate && typeof onProgressUpdate === 'function') {
          onProgressUpdate();
        }
        
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
  }, [practicesession_id, onProgressUpdate]);

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
    <Card className="flex flex-col h-[700px] w-full overflow-hidden">
      {/* Previous conversation context (utterance rewind) */}
      {utteranceRewind.length > 0 && (
        <div className="flex-none overflow-y-auto max-h-[200px] mb-4 px-5 pt-2 pb-3 border-b border-gray-100">
          <h4 className="py-2 px-3 bg-gray-100 rounded-t-md text-base font-semibold mb-2">Previous Conversation Context:</h4>
          
          {utteranceRewind.map((item, index) => (
            <div
              key={item.id || index}
              className={`flex ${item.role.toLowerCase() === 'helper' ? 'justify-end' : 'justify-start'} mb-3`}
              style={item.isTarget ? { backgroundColor: 'rgba(255, 248, 225, 0.3)', padding: '8px', borderRadius: '8px' } : {}}
            >
              <div className={`max-w-[80%] p-3 rounded-lg shadow-sm ${
                item.role.toLowerCase() === 'helper' 
                  ? 'bg-blue-500 text-white' 
                  : 'bg-gradient-to-r from-amber-200 to-amber-400'
              }`}>
                <div className="font-semibold text-base mb-1">
                  {item.role}
                  {item.isTarget && " (Focus on this response)"}
                </div>
                <div className="text-base">
                  {formatMessageText(item.utterance)}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    
      {/* Main chat messages */}
      <div className="flex-1 overflow-y-auto px-5 py-4 bg-gray-50">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.isUser ? 'justify-end' : 'justify-start'} mb-4 animate-fadeIn`}
          >
            <div className={`max-w-[70%] p-4 rounded-lg shadow-sm ${
              message.isUser 
                ? 'bg-blue-500 text-white' 
                : 'bg-gradient-to-r from-amber-200 to-amber-400'
            }`}>
              <div className="flex items-center mb-2">
                <div className="text-xs uppercase tracking-wider mb-2 font-medium opacity-80">
                {message.isUser ? 'You' : 'Practice Mentor'}
                </div>
              </div>
              <div className={`${message.isUser ? 'text-white' : 'text-gray-800'} text-base`}>
                {message.isUser ? 
                  formatRegularText(message.text) : 
                  formatMessageText(message.text, handleOptionClick)}
              </div>
              <div className="text-xs opacity-70 text-right mt-2">
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

      {/* Input area */}
      <CardContent className="border-t border-gray-100 p-4 bg-white">
        <form onSubmit={sendMessage} className="relative">
          <Textarea
            ref={textareaRef}
            value={currentMessage}
            onChange={handleMessageChange}
            onKeyDown={handleKeyPress}
            placeholder="Type your message here..."
            className="w-full py-3 px-4 pr-24 min-h-[60px] max-h-[120px] resize-none bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-200 transition-all flex items-center text-base"
            disabled={!isConnected || isLoading}
            style={{ display: 'flex', alignItems: 'center' }}
            rows={2}
          />
          <Button 
            type="submit" 
            className="absolute right-2 bottom-4 rounded-full w-10 h-10 p-0 flex items-center justify-center"
            variant="default"
            disabled={!isConnected || isLoading || currentMessage.trim() === ""}
            size="icon"
          >
            {isLoading ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <Send className="h-5 w-5" />
            )}
          </Button>
        </form>
      </CardContent>
      
      {/* Connection status indicator */}
      {!isConnected && messages.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center bg-white bg-opacity-90">
          <div className="bg-gradient-to-r from-amber-200 to-amber-400 rounded-full py-3 px-6 shadow-lg flex items-center space-x-3">
            <div className="flex space-x-1">
              <span className="inline-block text-2xl animate-bounce" style={{ animationDelay: "-0.32s" }}>🐱</span>
              <span className="inline-block text-2xl animate-bounce" style={{ animationDelay: "-0.16s" }}>🐶</span>
              <span className="inline-block text-2xl animate-bounce">🐰</span>
            </div>
            <span className="font-semibold text-base text-gray-800">Generating personalised practice...</span>
          </div>
        </div>
      )}
    </Card>
  );
};

export default Freeform;