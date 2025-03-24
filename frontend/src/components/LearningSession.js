import React, { useEffect, useState, useCallback } from 'react';
import Freeform from './Freeform';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { ArrowLeft, Trophy } from 'lucide-react';

const LearningSession = ({ sessionData, onBack }) => {
  const [sessionUserData, setSessionUserData] = useState(null);
  const [subskillProgress, setSubskillProgress] = useState({
    current: null,
    total: 0,
    completed: []
  });

  // Function to fetch subskill progress with error handling
  const fetchSubskillProgress = useCallback(async (practiceSessionId) => {
    try {
      const response = await fetch(`/api/subskill-progress/${practiceSessionId}`);
      if (!response.ok) {
        throw new Error('Failed to fetch subskill progress');
      }
      
      const data = await response.json();
      if (data.success && data.subskillProgress) {
        console.log("Subskill progress updated:", data.subskillProgress);
        setSubskillProgress(data.subskillProgress);
      } else {
        console.warn('Failed to get subskill progress:', data.error);
      }
    } catch (error) {
      console.error('Error fetching subskill progress:', error);
    }
  }, []);

  // Fetch initial session data and progress
  useEffect(() => {
    if (sessionData && sessionData.practicesession_id) {
      setSessionUserData(sessionData);
      fetchSubskillProgress(sessionData.practicesession_id);
    }
  }, [sessionData, fetchSubskillProgress]);

  // Set up polling to check for updates (every 5 seconds)
  useEffect(() => {
    if (!sessionData || !sessionData.practicesession_id) return;
    
    // Initial fetch
    fetchSubskillProgress(sessionData.practicesession_id);
    
    // Set up polling interval
    const intervalId = setInterval(() => {
      fetchSubskillProgress(sessionData.practicesession_id);
    }, 5000);
    
    // Clean up interval on unmount
    return () => {
      clearInterval(intervalId);
    };
  }, [sessionData, fetchSubskillProgress]);

  if (!sessionData || !sessionData.practicesession_id) {
    return (
      <div className="min-h-screen p-6 bg-gradient-to-br from-blue-400 to-purple-400 flex flex-col items-center justify-center">
        <Card className="p-6 text-center">
          <CardContent className="pt-6">
            <div className="text-red-500 font-medium mb-4">
              No valid session data available. Please select a different session.
            </div>
            <Button 
              onClick={onBack} 
              variant="outline"
              className="rounded-full aspect-square p-0 w-10 h-10"
              size="icon"
            >
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Calculate progress percentage
  const progressPercentage = subskillProgress.total > 0 
    ? Math.round((subskillProgress.completed.length / subskillProgress.total) * 100) 
    : 0;

  // Get the current subskill - use the one from the API response first, fall back to sessionData
  const currentSubskill = subskillProgress.current || sessionData.target_subskill;

  return (
    <div className="min-h-screen p-6 bg-gradient-to-br from-blue-400 to-purple-400 flex flex-col items-center">
      {/* Back Button - Positioned absolutely */}
      <Button 
        onClick={onBack} 
        variant="default"
        className="absolute top-6 left-6 w-10 h-10 p-0 rounded-full shadow-md"
        size="icon"
        aria-label="Back to Sessions"
      >
        <ArrowLeft className="h-5 w-5" />
      </Button>
      
      {/* Main content wrapper - removed title */}
      <div className="w-full max-w-7xl mb-6">
        {/* Two-column layout with adjusted widths */}
        <div className="flex flex-col lg:flex-row gap-6 justify-between">
          {/* Chat Interface - Wider */}
          <div className="flex-1 lg:max-w-[calc(100%-350px)]">
            <Freeform 
              practicesession_id={sessionData.practicesession_id} 
              user_id={sessionData.user_id} 
              onProgressUpdate={() => fetchSubskillProgress(sessionData.practicesession_id)}
            />
          </div>
          
          {/* Progress Card - Wider sidebar */}
          <div className="w-full lg:w-80">
            <Card className="h-full">
              <CardContent className="pt-4 px-4">
                <div className="flex items-center gap-2 mb-3">
                  <Trophy className="h-5 w-5 text-amber-400" />
                  <h3 className="text-lg font-semibold">Your Progress</h3>
                </div>
                
                <div className="mb-6">
                  <div className="text-left text-sm text-gray-600 mb-2">
                    {subskillProgress.completed.length} of {subskillProgress.total} completed
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-4">
                    <div 
                      className="bg-green-500 h-4 rounded-full" 
                      style={{ width: `${progressPercentage}%` }}
                    ></div>
                  </div>
                </div>
                
                {/* Completed Skills - Now displayed FIRST */}
                {subskillProgress.completed && subskillProgress.completed.length > 0 && (
                  <div className="space-y-2 mb-4">
                    {subskillProgress.completed.map((skill, index) => (
                      <div key={`completed-${index}`} className="flex items-start justify-between">
                        <span>{skill}</span>
                        <div className="flex-shrink-0">
                          <Badge className="bg-green-100 text-green-800">✓</Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
                
                {/* Current Skill - Now at the BOTTOM */}
                {currentSubskill && !subskillProgress.completed.includes(currentSubskill) && (
                  <div className="mt-2">
                    <div className="flex items-start justify-between">
                      <span className="font-medium">{currentSubskill}</span>
                      <div className="flex-shrink-0">
                        <Badge className="bg-blue-100 text-blue-800">Current</Badge>
                      </div>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LearningSession;