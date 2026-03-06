import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { sendChatMessage } from '../api/chat';
import type { ChatResponse, Candidate } from '../types/api';
import './ChatPage.css';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  response?: ChatResponse;
}

const CHAT_STORAGE_KEY = 'hr_chat_messages';

// Helper functions for localStorage persistence
const saveMessagesToStorage = (messages: ChatMessage[]) => {
  try {
    const serialized = messages.map((msg) => ({
      ...msg,
      timestamp: msg.timestamp.toISOString(),
    }));
    localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(serialized));
  } catch (error) {
    console.error('Failed to save messages to localStorage:', error);
  }
};

const loadMessagesFromStorage = (): ChatMessage[] => {
  try {
    const stored = localStorage.getItem(CHAT_STORAGE_KEY);
    if (!stored) return [];
    
    const parsed = JSON.parse(stored);
    return parsed.map((msg: any) => ({
      ...msg,
      timestamp: new Date(msg.timestamp),
    }));
  } catch (error) {
    console.error('Failed to load messages from localStorage:', error);
    return [];
  }
};

export default function ChatPage() {
  const navigate = useNavigate();
  const [messages, setMessages] = useState<ChatMessage[]>(() => loadMessagesFromStorage());
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Save messages whenever they change
  useEffect(() => {
    if (messages.length > 0) {
      saveMessagesToStorage(messages);
    }
  }, [messages]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleClearChat = () => {
    if (window.confirm('Are you sure you want to clear the chat history?')) {
      setMessages([]);
      localStorage.removeItem(CHAT_STORAGE_KEY);
    }
  };

  const handleSend = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      role: 'user',
      content: inputValue.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);
    setError(null);

    try {
      const response = await sendChatMessage(userMessage.content);
      
      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: response.reply,
        timestamp: new Date(),
        response: response,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err: any) {
      setError(
        err.response?.data?.detail || err.message || 'Failed to send message. Please try again.'
      );
      const errorMessage: ChatMessage = {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const formatFilters = (filters: ChatResponse['filters']) => {
    const activeFilters: string[] = [];
    
    if (filters.position) activeFilters.push(`Position: ${filters.position}`);
    if (filters.nationality) activeFilters.push(`Nationality: ${filters.nationality}`);
    if (filters.min_years_experience !== null) {
      activeFilters.push(`Min Experience: ${filters.min_years_experience} years`);
    }
    if (filters.max_years_experience !== null) {
      activeFilters.push(`Max Experience: ${filters.max_years_experience} years`);
    }
    if (filters.min_expected_salary !== null) {
      activeFilters.push(`Min Salary: $${filters.min_expected_salary}`);
    }
    if (filters.max_expected_salary !== null) {
      activeFilters.push(`Max Salary: $${filters.max_expected_salary}`);
    }
    if (filters.current_address) activeFilters.push(`Location: ${filters.current_address}`);

    return activeFilters;
  };

  return (
    <div className="chat-page">
      <div className="chat-header">
        <div className="chat-header-top">
          <div>
            <h1>AI Candidate Search</h1>
            <p className="chat-subtitle">
              Ask questions in natural language to find candidates. For example: "Show me Lebanese
              backend engineers with 5+ years of experience"
            </p>
          </div>
          {messages.length > 0 && (
            <button onClick={handleClearChat} className="clear-chat-button">
              Clear Chat
            </button>
          )}
        </div>
      </div>

      <div className="chat-container">
        <div className="messages-container">
          {messages.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">💬</div>
              <h2>Start a conversation</h2>
              <p>Ask me anything about candidates in the database.</p>
            </div>
          ) : (
            <div className="messages-list">
              {messages.map((message, idx) => (
                <div key={idx} className={`message ${message.role}`}>
                  <div className="message-content">
                    <div className="message-header">
                      <span className="message-role">
                        {message.role === 'user' ? 'You' : 'Assistant'}
                      </span>
                      <span className="message-time">
                        {message.timestamp.toLocaleTimeString([], {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                    </div>
                    <div className="message-text">{message.content}</div>

                    {message.response && (
                      <div className="response-details">
                        {message.response.aggregations && (
                          <div className="aggregations-section">
                            <strong>Statistics:</strong>
                            <div className="aggregations-grid">
                              {message.response.aggregations.total_count !== null && (
                                <div className="aggregation-item">
                                  <span className="aggregation-label">Total Candidates:</span>
                                  <span className="aggregation-value">
                                    {message.response.aggregations.total_count}
                                  </span>
                                </div>
                              )}
                              {message.response.aggregations.avg_salary !== null && (
                                <div className="aggregation-item">
                                  <span className="aggregation-label">Average Salary:</span>
                                  <span className="aggregation-value">
                                    ${message.response.aggregations.avg_salary.toLocaleString()} USD
                                  </span>
                                </div>
                              )}
                              {message.response.aggregations.avg_experience !== null && (
                                <div className="aggregation-item">
                                  <span className="aggregation-label">Average Experience:</span>
                                  <span className="aggregation-value">
                                    {message.response.aggregations.avg_experience} years
                                  </span>
                                </div>
                              )}
                              {message.response.aggregations.min_salary !== null && (
                                <div className="aggregation-item">
                                  <span className="aggregation-label">Min Salary:</span>
                                  <span className="aggregation-value">
                                    ${message.response.aggregations.min_salary.toLocaleString()} USD
                                  </span>
                                </div>
                              )}
                              {message.response.aggregations.max_salary !== null && (
                                <div className="aggregation-item">
                                  <span className="aggregation-label">Max Salary:</span>
                                  <span className="aggregation-value">
                                    ${message.response.aggregations.max_salary.toLocaleString()} USD
                                  </span>
                                </div>
                              )}
                              {message.response.aggregations.min_experience !== null && (
                                <div className="aggregation-item">
                                  <span className="aggregation-label">Min Experience:</span>
                                  <span className="aggregation-value">
                                    {message.response.aggregations.min_experience} years
                                  </span>
                                </div>
                              )}
                              {message.response.aggregations.max_experience !== null && (
                                <div className="aggregation-item">
                                  <span className="aggregation-label">Max Experience:</span>
                                  <span className="aggregation-value">
                                    {message.response.aggregations.max_experience} years
                                  </span>
                                </div>
                              )}
                            </div>
                          </div>
                        )}

                        <div className="filters-applied">
                          <strong>Filters Applied:</strong>
                          <div className="filters-tags">
                            {formatFilters(message.response.filters).map((filter, i) => (
                              <span key={i} className="filter-tag">
                                {filter}
                              </span>
                            ))}
                          </div>
                        </div>

                        {message.response.total_matches > 0 && !message.response.aggregations && (
                          <div className="matches-info">
                            <strong>{message.response.total_matches}</strong> candidate
                            {message.response.total_matches !== 1 ? 's' : ''} found
                          </div>
                        )}

                        {message.response.top_candidates.length > 0 && (
                          <div className="candidates-preview">
                            <h3>Top Matches:</h3>
                            <div className="candidates-grid">
                              {message.response.top_candidates.map((candidate) => (
                                <div
                                  key={candidate.id}
                                className="candidate-card"
                                onClick={() => navigate(`/candidates/${candidate.id}`, { state: { fromChat: true } })}
                              >
                                  <div className="candidate-name">{candidate.full_name || 'N/A'}</div>
                                  <div className="candidate-details">
                                    {candidate.position && (
                                      <span className="candidate-detail">{candidate.position}</span>
                                    )}
                                    {candidate.nationality && (
                                      <span className="candidate-detail">
                                        {candidate.nationality}
                                      </span>
                                    )}
                                    {candidate.years_experience !== null && (
                                      <span className="candidate-detail">
                                        {candidate.years_experience} years exp.
                                      </span>
                                    )}
                                    {candidate.expected_salary !== null && (
                                      <span className="candidate-detail">
                                        ${candidate.expected_salary.toLocaleString()}
                                      </span>
                                    )}
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="message assistant">
                  <div className="message-content">
                    <div className="message-text">
                      <span className="typing-indicator">Thinking...</span>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {error && (
          <div className="error-banner" role="alert">
            {error}
          </div>
        )}

        <div className="input-container">
          <textarea
            ref={inputRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask about candidates... (Press Enter to send, Shift+Enter for new line)"
            className="chat-input"
            rows={3}
            disabled={isLoading}
          />
          <button
            onClick={handleSend}
            disabled={!inputValue.trim() || isLoading}
            className="send-button"
          >
            {isLoading ? 'Sending...' : 'Send'}
          </button>
        </div>
      </div>
    </div>
  );
}
