import './styles/tailwind.css';
import React, { useState, useEffect } from 'react';
import LearningSession from './components/LearningSession';
import { Card, CardContent, CardHeader, CardTitle } from './components/ui/card';
import { Input } from './components/ui/input';
import { Button } from './components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './components/ui/table';
import { Badge } from './components/ui/badge';
import { AlertCircle, Search, Bug, ChevronRight } from 'lucide-react';

const App = () => {
  const [userId, setUserId] = useState('');
  const [userSessions, setUserSessions] = useState([]);
  const [selectedSessionId, setSelectedSessionId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sessionSubskills, setSessionSubskills] = useState({});

  // Handle key press for Enter
  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (userId.trim()) {
        fetchSessionsByUserId();
      }
    }
  };

  // Function to fetch subskills for a session
  const fetchSessionSubskills = async (practicesessionId) => {
    try {
      const response = await fetch(`/api/session/${practicesessionId}/subskills`);
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      const data = await response.json();
      
      if (data.success && Array.isArray(data.subskills)) {
        setSessionSubskills(prev => ({
          ...prev,
          [practicesessionId]: data.subskills
        }));
      }
    } catch (error) {
      console.error(`Error fetching subskills for session ${practicesessionId}:`, error);
    }
  };

  // Function to get last 4 digits of session ID or chat code
  const getLastFourDigits = (str) => {
    if (!str) return 'N/A';
    return str.slice(-4);
  };

  // Function to fetch sessions by user ID
  const fetchSessionsByUserId = () => {
    if (!userId.trim()) {
      setError('Please enter a User ID');
      return;
    }

    setLoading(true);
    setError(null);
    
    fetch(`/api/user/${encodeURIComponent(userId)}/sessions`)
      .then(response => {
        if (!response.ok) {
          throw new Error(`API error: ${response.status}`);
        }
        return response.json();
      })
      .then(data => {
        console.log('Sessions data:', data);
        
        if (data.error) {
          console.warn('API returned error:', data.error);
          setError(data.error);
        }
        
        if (data.sessions && Array.isArray(data.sessions)) {
          setUserSessions(data.sessions);
          
          // Fetch subskills for each session
          data.sessions.forEach(session => {
            fetchSessionSubskills(session.practicesession_id);
          });
        } else {
          setUserSessions([]);
        }
        
        setLoading(false);
      })
      .catch(error => {
        console.error('Error fetching sessions:', error);
        setError(`Failed to fetch sessions: ${error.message}`);
        setLoading(false);
      });
  };

  // Function to handle session selection
  const handleSelectSession = (sessionId) => {
    setSelectedSessionId(sessionId);
    console.log(`Selected session with id: ${sessionId}`);
  };

  // Function to reset to user input
  const resetToUserIdInput = () => {
    setSelectedSessionId(null);
  };

  // Get the selected session data
  const getSelectedSession = () => {
    if (!selectedSessionId) return null;
    
    const session = userSessions.find(
      s => s.practicesession_id.toString() === selectedSessionId.toString()
    );
    
    return session ? {
      ...session,
      user_id: userId  // Ensure user_id is included
    } : null;
  };

  // If a session is selected, show the learning session
  if (selectedSessionId) {
    const sessionData = getSelectedSession();
    return (
      <div className="min-h-screen bg-gray-50">
        <LearningSession
          sessionData={sessionData}
          onBack={resetToUserIdInput}
        />
      </div>
    );
  }

  // Otherwise show the user ID input and sessions list
  return (
    <div className="min-h-screen bg-gray-50 p-6">
      {/* Loading overlay */}
      {loading && 
        <div className="fixed inset-0 bg-white bg-opacity-80 flex items-center justify-center z-50 text-lg font-semibold">
          <div className="flex items-center gap-2">
            <svg className="animate-spin h-5 w-5 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
            </svg>
            Loading...
          </div>
        </div>
      }
      
      {/* Error message */}
      {error && 
        <div className="max-w-3xl mx-auto mb-4 flex items-center gap-2 p-3 text-sm bg-red-100 border border-red-200 text-red-800 rounded-md">
          <AlertCircle className="h-4 w-4" />
          <span>{error}</span>
        </div>
      }
      
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold">CARE Mentor - Session Selector</h1>
          <Button 
            variant="outline" 
            size="sm"
            onClick={() => window.open('/api/debug', '_blank')}
            className="text-xs flex items-center gap-1"
          >
            <Bug className="h-3 w-3" />
            Debug
          </Button>
        </div>
        
        {/* User search bar with compact layout */}
        <Card className="mb-6">
          <CardContent className="pt-6">
            <div className="flex gap-2 items-center">
              <div className="flex-1">
                <Input
                  type="text"
                  placeholder="Enter User ID"
                  value={userId}
                  onChange={(e) => setUserId(e.target.value)}
                  onKeyPress={handleKeyPress}
                  className="w-full"
                />
              </div>
              <Button
                onClick={fetchSessionsByUserId}
                disabled={!userId.trim()}
                className="whitespace-nowrap"
                variant="primary"
              >
                <Search className="mr-2 h-4 w-4" />
                Find Sessions
              </Button>
            </div>
          </CardContent>
        </Card>
        
        {/* Sessions List */}
        {userSessions.length > 0 && (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle>Available Sessions for {userId}</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-16">ID</TableHead>
                    <TableHead className="w-32">Code</TableHead>
                    <TableHead className="w-1/1">Subskills in Focus</TableHead>
                    <TableHead className="text-left">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {userSessions.map(session => (
                    <TableRow key={session.practicesession_id}>
                      <TableCell>{session.practicesession_id}</TableCell>
                      <TableCell>{getLastFourDigits(session.chat_code)}</TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-2">
                          {sessionSubskills[session.practicesession_id]?.map((subskill, index) => (
                            <Badge 
                              key={index} 
                              variant="outline"
                              className="px-2 py-1 text-xs rounded-full"
                            >
                              {subskill}
                            </Badge>
                          )) || (
                            <Badge variant="outline">
                              {session.target_subskill || 'N/A'}
                            </Badge>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="text-left">
                        <Button 
                          onClick={() => handleSelectSession(session.practicesession_id)}
                          size="sm"
                          className="flex items-center"
                          variant="primary"
                        >
                          Select
                          <ChevronRight className="ml-1 h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}
        
        {/* No Sessions Message */}
        {userSessions.length === 0 && userId && !loading && (
          <Card>
            <CardContent className="pt-6">
              <div className="flex flex-col items-center justify-center p-6 text-center">
                <div className="rounded-full bg-yellow-100 p-3 mb-3">
                  <AlertCircle className="h-6 w-6 text-yellow-600" />
                </div>
                <h3 className="text-lg font-medium mb-2">No Sessions Found</h3>
                <p className="text-gray-500 mb-3">No practice sessions found for this user.</p>
                <p className="text-sm text-gray-400">Try entering a different user ID.</p>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
};

export default App;