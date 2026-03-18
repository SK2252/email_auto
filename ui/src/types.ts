
export enum Role {
  USER = 'user',
  MODEL = 'model'
}

export interface Message {
  id: string;
  role: Role;
  content: string;
  timestamp: number;
}

export interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  createdAt: number;
}

export interface ThemeConfig {
  fontFamily: 'inter' | 'mono' | 'serif';
  primaryColor: string;
  isDarkMode: boolean;
}
