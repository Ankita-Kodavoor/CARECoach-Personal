// API configuration for development and production environments

const getApiBaseUrl = () => {
  // In production, use the same origin (backend and frontend are served from same domain)
  if (process.env.NODE_ENV === 'production') {
    return '';
  }
  
  // In development, use the proxy defined in package.json or a specific URL
  return process.env.REACT_APP_API_URL || 'http://localhost:5000';
};

export const API_BASE_URL = getApiBaseUrl();

// WebSocket URL must be constructed at runtime based on the current protocol and host
export const getWebSocketUrl = (path) => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  
  if (process.env.NODE_ENV === 'production') {
    // In production, use the same host but with ws(s) protocol
    return `${protocol}//${window.location.host}${path}`;
  }
  
  // In development
  const wsHost = process.env.REACT_APP_WS_HOST || 'localhost:5000';
  return `${protocol}//${wsHost}${path}`;
};
