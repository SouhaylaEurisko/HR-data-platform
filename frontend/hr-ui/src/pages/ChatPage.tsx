import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    listConversations,
    getConversationById,
    sendConversationMessage,
    deleteConversation,
  } from '../api/chat';
import type {
  AgentResponseData,
  Conversation,
  ConversationWithMessages,
  SendMessageResponse,
} from '../types/api';
import chatbotLogo from '../../logo/OIP.webp';
import ConfirmationDialog from '../components/ConfirmationDialog';
import {
  CHAT_MESSAGES_KEY,
  CHAT_ACTIVE_CONVERSATION_KEY,
} from '../constants/chatStorage';
import './ChatPage.css';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  response?: AgentResponseData | null;
}

/** Comparison reply already states the pick; skip duplicate summary paragraph. */
function shouldShowResponseSummary(intent: string | undefined): boolean {
  if (!intent) return true;
  return intent !== 'candidate_comparison';
}

// Helper functions for localStorage persistence
const saveMessagesToStorage = (messages: ChatMessage[]) => {
  try {
    const serialized = messages.map((msg) => ({
      ...msg,
      timestamp: msg.timestamp.toISOString(),
    }));
    localStorage.setItem(CHAT_MESSAGES_KEY, JSON.stringify(serialized));
  } catch (error) {
    console.error('Failed to save messages to localStorage:', error);
  }
};

const loadMessagesFromStorage = (): ChatMessage[] => {
  try {
    const stored = localStorage.getItem(CHAT_MESSAGES_KEY);
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
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<number | null>(() => {
    const stored = localStorage.getItem(CHAT_ACTIVE_CONVERSATION_KEY);
    return stored ? Number(stored) : null;
  });
  const [confirmDialog, setConfirmDialog] = useState<{
    isOpen: boolean;
    type: 'clear' | 'delete' | null;
    conversationId?: number;
  }>({ isOpen: false, type: null });
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

  // Load conversations list on mount
  useEffect(() => {
    const fetchConversations = async () => {
      try {
        const data = await listConversations();
        setConversations(data);
      } catch (err) {
        console.error('Failed to load conversations', err);
      }
    };
    fetchConversations();
  }, []);

  // Persist active conversation id
  useEffect(() => {
    if (activeConversationId != null) {
      localStorage.setItem(CHAT_ACTIVE_CONVERSATION_KEY, String(activeConversationId));
    } else {
      localStorage.removeItem(CHAT_ACTIVE_CONVERSATION_KEY);
    }
  }, [activeConversationId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSelectConversation = async (conversationId: number) => {
    if (conversationId === activeConversationId) return;
    setIsLoading(true);
    setError(null);
    try {
      const conv: ConversationWithMessages = await getConversationById(conversationId);
      setActiveConversationId(conv.id);
      const mappedMessages: ChatMessage[] = (conv.messages || []).map((m) => ({
        role: m.sender,
        content: m.content,
        timestamp: new Date(m.created_at),
        response: m.response, // Include response data (filters, aggregations, candidates, etc.)
      }));
      setMessages(mappedMessages);
    } catch (err: any) {
      console.error('Failed to load conversation', err);
      setError(
        err.response?.data?.detail || err.message || 'Failed to load conversation. Please try again.'
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleNewChat = () => {
    setActiveConversationId(null);
    setMessages([]);
    localStorage.removeItem(CHAT_MESSAGES_KEY);
  };

  const handleClearChat = () => {
    setConfirmDialog({ isOpen: true, type: 'clear' });
  };

  const confirmClearChat = () => {
    setMessages([]);
    localStorage.removeItem(CHAT_MESSAGES_KEY);
    setConfirmDialog({ isOpen: false, type: null });
  };

  const handleDeleteConversation = (conversationId: number, e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent selecting the conversation when clicking delete
    setConfirmDialog({ isOpen: true, type: 'delete', conversationId });
  };

  const confirmDeleteConversation = async () => {
    if (!confirmDialog.conversationId) return;

    try {
      await deleteConversation(confirmDialog.conversationId);
      
      // If this was the active conversation, clear it
      if (confirmDialog.conversationId === activeConversationId) {
        setActiveConversationId(null);
        setMessages([]);
        localStorage.removeItem(CHAT_MESSAGES_KEY);
      }
      
      // Refresh conversations list
      const updatedConversations = await listConversations();
      setConversations(updatedConversations);
      setConfirmDialog({ isOpen: false, type: null });
    } catch (err: any) {
      console.error('Failed to delete conversation', err);
      setError(
        err.response?.data?.detail || err.message || 'Failed to delete conversation. Please try again.'
      );
      setConfirmDialog({ isOpen: false, type: null });
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
      const response: SendMessageResponse = await sendConversationMessage({
        content: userMessage.content,
        sender: 'user',
        conversation_id: activeConversationId ?? undefined,
      });

      // update active conversation id and list
      if (!activeConversationId || response.conversation_id !== activeConversationId) {
        setActiveConversationId(response.conversation_id);
      }

      // Refresh conversations list in background
      listConversations().then(setConversations).catch(() => undefined);

      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: response.reply,
        timestamp: new Date(),
        response: response.response ?? null,
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

  // No longer needed — the new response doesn't have structured filters

  return (
    <div className="chat-page">
      <div className="chat-header">
        <div className="chat-header-top">
          <div>
            <h1>AI Candidate Search</h1>
            <p className="chat-subtitle">
              Ask questions in natural language to find candidates.
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
        <aside className="chat-sidebar">
          <div className="chat-sidebar-header">
            <span className="chat-sidebar-title">Conversations</span>
            <button
              type="button"
              className="new-chat-button"
              onClick={handleNewChat}
              disabled={isLoading}
            >
              New chat
            </button>
          </div>

          <div className="conversations-list">
            {conversations.length === 0 ? (
              <div className="empty-state">
                <p>No conversations yet</p>
              </div>
            ) : (
              conversations.map((conv) => (
                <div
                  key={conv.id}
                  className={`conversation-item-wrapper ${
                    conv.id === activeConversationId ? 'active' : ''
                  }`}
                >
                  <button
                    type="button"
                    className="conversation-item"
                    onClick={() => handleSelectConversation(conv.id)}
                  >
                    <div className="conversation-item-content">
                      <span className="conversation-title">
                        {conv.title || `Conversation ${conv.id}`}
                      </span>
                      <span className="conversation-timestamp">
                        {new Date(conv.updated_at || conv.created_at).toLocaleString([], {
                          hour: '2-digit',
                          minute: '2-digit',
                          month: 'short',
                          day: '2-digit',
                        })}
                      </span>
                    </div>
                  </button>
                  <button
                    type="button"
                    className="conversation-delete-button"
                    onClick={(e) => handleDeleteConversation(conv.id, e)}
                    title="Delete conversation"
                  >
                    <svg viewBox="0 0 20 20" fill="currentColor" width="16" height="16">
                      <path
                        fillRule="evenodd"
                        d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z"
                        clipRule="evenodd"
                      />
                    </svg>
                  </button>
                </div>
              ))
            )}
          </div>
        </aside>

        <div className="messages-container">
          {messages.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">💬</div>
              <h2>Start a conversation</h2>
              <p>
                Search candidates, ask for stats, compare applicants for a role, or request HR stage feedback
                for someone by name.
              </p>
            </div>
          ) : (
            <div className="messages-list">
              {messages.map((message, idx) => (
                <div key={idx} className={`message ${message.role}`}>
                  {message.role === 'user' && (
                    <div className="message-avatar user-avatar">
                      {/* Future: Replace with <img src={userImage} alt="User" /> when user image is available */}
                      <svg viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
                        <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                      </svg>
                    </div>
                  )}
                  {message.role === 'assistant' && (
                    <div className="message-avatar assistant-avatar">
                      <img src={chatbotLogo} alt="AI Assistant" />
                    </div>
                  )}
                  <div className="message-content">
                    <div className="message-text">{message.content}</div>
                      <span className="message-time">
                        {message.timestamp.toLocaleTimeString([], {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>

                    {message.response && message.response.intent && message.response.intent !== 'chitchat' && (
                      <div className="response-details">
                        {message.response.summary && shouldShowResponseSummary(message.response.intent) && (
                          <div className="summary-section">
                            <p className="summary-text">{message.response.summary}</p>
                          </div>
                        )}

                        {/* Total found — hidden for comparison and aggregation intents */}
                        {message.response.intent !== 'candidate_comparison' &&
                          message.response.intent !== 'aggregation' &&
                          !(message.response.intent === 'filter_and_aggregation' && message.response.stats && message.response.stats.length > 0) &&
                          message.response.total_found != null &&
                          message.response.total_found > 0 && (
                          <div className="matches-info">
                            <strong>{message.response.total_found}</strong> candidate
                            {message.response.total_found !== 1 ? 's' : ''} found
                          </div>
                        )}

                        {/* Aggregation stats */}
                        {message.response.stats && message.response.stats.length > 0 && (
                          <div className="aggregations-section">
                            <strong>Statistics:</strong>
                            <div className="aggregations-grid">
                              {message.response.stats.map((stat, si) =>
                                Object.entries(stat).map(([key, value]) =>
                                  value != null ? (
                                    <div key={`${si}-${key}`} className="aggregation-item">
                                      <span className="aggregation-label">{key.replace(/_/g, ' ')}:</span>
                                      <span className="aggregation-value">
                                        {typeof value === 'number'
                                          ? value.toLocaleString(undefined, { maximumFractionDigits: 2 })
                                          : String(value)}
                                      </span>
                                    </div>
                                  ) : null
                                )
                              )}
                            </div>
                          </div>
                        )}

                        {/* Candidate rows — for aggregation with stats, show only the top result */}
                        {message.response.candidates && message.response.candidates.length > 0 &&
                          !(message.response.intent === 'aggregation') && (
                          <div className="candidates-preview">
                            <h3>
                              {message.response.intent === 'candidate_comparison'
                                ? 'Recommended candidate'
                                : (message.response.intent === 'filter_and_aggregation' && message.response.stats && message.response.stats.length > 0)
                                ? 'Top match:'
                                : 'Candidates:'}
                            </h3>
                            <div className="candidates-grid">
                              {((message.response.intent === 'filter_and_aggregation' && message.response.stats && message.response.stats.length > 0)
                                ? message.response.candidates.slice(0, 1)
                                : message.response.candidates
                              ).map((candidate: any, ci: number) => (
                                <div
                                  key={candidate.id || ci}
                                  className="candidate-card"
                                  onClick={() =>
                                    candidate.id
                                      ? navigate(`/candidates/${candidate.id}`, { state: { fromChat: true } })
                                      : undefined
                                  }
                                >
                                  <div className="candidate-name">
                                    {candidate.full_name || 'N/A'}
                                  </div>
                                  <div className="candidate-details">
                                    {candidate.applied_position && (
                                      <span className="candidate-detail">{candidate.applied_position}</span>
                                    )}
                                    {candidate.nationality && (
                                      <span className="candidate-detail">{candidate.nationality}</span>
                                    )}
                                    {candidate.years_of_experience != null && (
                                      <span className="candidate-detail">
                                        {candidate.years_of_experience} years exp.
                                      </span>
                                    )}
                                    {candidate.current_salary != null && (
                                      <span className="candidate-detail">
                                        Current: ${Number(candidate.current_salary).toLocaleString()}
                                      </span>
                                    )}
                                    {(candidate.expected_salary_remote != null || candidate.expected_salary_onsite != null) && (
                                      <span className="candidate-detail">
                                        Expected: Remote {candidate.expected_salary_remote != null ? `$${Number(candidate.expected_salary_remote).toLocaleString()}` : '—'}
                                        {' / '}
                                        Onsite {candidate.expected_salary_onsite != null ? `$${Number(candidate.expected_salary_onsite).toLocaleString()}` : '—'}
                                      </span>
                                    )}
                                    {candidate.current_address && (
                                      <span className="candidate-detail">{candidate.current_address}</span>
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
                  <div className="message-avatar assistant-avatar">
                    <img src={chatbotLogo} alt="AI Assistant" />
                  </div>
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

      {/* Confirmation Dialogs */}
      <ConfirmationDialog
        isOpen={confirmDialog.isOpen && confirmDialog.type === 'clear'}
        title="Clear Chat History"
        message="Are you sure you want to clear the chat history?"
        confirmText="Clear"
        cancelText="Cancel"
        variant="warning"
        onConfirm={confirmClearChat}
        onCancel={() => setConfirmDialog({ isOpen: false, type: null })}
      />

      <ConfirmationDialog
        isOpen={confirmDialog.isOpen && confirmDialog.type === 'delete'}
        title="Delete Conversation"
        message="Are you sure you want to delete this conversation?"
        confirmText="Delete"
        cancelText="Cancel"
        variant="danger"
        onConfirm={confirmDeleteConversation}
        onCancel={() => setConfirmDialog({ isOpen: false, type: null })}
      />
    </div>
  );
}