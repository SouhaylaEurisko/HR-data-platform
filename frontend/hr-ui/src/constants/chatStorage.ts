/** Keys used by ChatPage; cleared on login/signup/logout so each session starts on "new chat". */
export const CHAT_MESSAGES_KEY = 'hr_chat_messages';
export const CHAT_ACTIVE_CONVERSATION_KEY = 'hr_chat_active_conversation_id';

export function clearChatLocalStorage(): void {
  try {
    localStorage.removeItem(CHAT_MESSAGES_KEY);
    localStorage.removeItem(CHAT_ACTIVE_CONVERSATION_KEY);
  } catch {
    /* ignore */
  }
}
