import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react';
import { NotificationsContext, type NotificationKind } from './notifications';

interface Notification {
  id: number;
  message: string;
  kind: NotificationKind;
}

const AUTO_DISMISS_MS = 6000;
const MAX_VISIBLE = 4;

export function NotificationsProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<Notification[]>([]);
  const nextId = useRef(1);

  const dismiss = useCallback((id: number) => {
    setItems((current) => current.filter((item) => item.id !== id));
  }, []);

  const notify = useCallback((message: string, kind: NotificationKind = 'info') => {
    const id = nextId.current++;
    setItems((current) => [...current, { id, message, kind }].slice(-MAX_VISIBLE));
  }, []);

  return (
    <NotificationsContext.Provider value={notify}>
      {children}
      <div className="notifications" aria-live="polite">
        {items.map((item) => (
          <NotificationItem key={item.id} item={item} onDismiss={dismiss} />
        ))}
      </div>
    </NotificationsContext.Provider>
  );
}

function NotificationItem({
  item,
  onDismiss,
}: {
  item: Notification;
  onDismiss: (id: number) => void;
}) {
  useEffect(() => {
    const timer = window.setTimeout(() => onDismiss(item.id), AUTO_DISMISS_MS);
    return () => window.clearTimeout(timer);
  }, [item.id, onDismiss]);

  return (
    <div className={`notification notification--${item.kind}`} role={item.kind === 'error' ? 'alert' : 'status'}>
      <span>{item.message}</span>
      <button type="button" className="link-button" onClick={() => onDismiss(item.id)} aria-label="Dismiss">
        ×
      </button>
    </div>
  );
}
