import React, { useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { ChatContainer } from '../components/chat/ChatContainer';

export const GuidePage: React.FC = () => {
  const location = useLocation();

  useEffect(() => {
    // If arriving from a destination card with initialPrompt
    const initialPrompt = location.state?.initialPrompt;
    if (initialPrompt) {
      window.history.replaceState({}, document.title);
    }
  }, [location]);

  return <ChatContainer />;
};
