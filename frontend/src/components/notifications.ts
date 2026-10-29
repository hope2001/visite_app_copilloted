import { createContext, useContext } from 'react';

export type NotificationKind = 'success' | 'error' | 'info';
export type Notify = (message: string, kind?: NotificationKind) => void;

export const NotificationsContext = createContext<Notify | null>(null);

export function useNotify(): Notify {
  const notify = useContext(NotificationsContext);
  if (!notify) throw new Error('useNotify must be used inside <NotificationsProvider>');
  return notify;
}
