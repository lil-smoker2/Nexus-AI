import {
  createContext,
  useContext,
  useState,
  useCallback,
  ReactNode,
} from 'react';

export type NotificationType = 'info' | 'success' | 'warning' | 'error';

export interface NotificationItem {
  id: string;
  type: NotificationType;
  title: string;
  message?: string;
  duration?: number;
}

interface NotificationContextValue {
  notifications: NotificationItem[];
  addNotification: (notification: Omit<NotificationItem, 'id'>) => void;
  removeNotification: (id: string) => void;
}

const NotificationContext = createContext<NotificationContextValue | undefined>(
  undefined
);

export function NotificationProvider({
  children,
}: {
  children: ReactNode;
}) {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);

  const addNotification = useCallback(
    (notification: Omit<NotificationItem, 'id'>) => {
      const id = Math.random().toString(36).slice(2);
      setNotifications((prev) => [...prev, { ...notification, id }]);
      if ((notification.duration ?? 5000) > 0) {
        setTimeout(() => {
          removeNotification(id);
        }, notification.duration ?? 5000);
      }
    },
    []
  );

  const removeNotification = useCallback((id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  }, []);

  return (
    <NotificationContext.Provider value={{ notifications, addNotification, removeNotification }}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 pointer-events-none">
        {notifications.map((n) => (
          <NotificationItem
            key={n.id}
            notification={n}
            onDismiss={() => removeNotification(n.id)}
          />
        ))}
      </div>
    </NotificationContext.Provider>
  );
}

export function useNotifications() {
  const ctx = useContext(NotificationContext);
  if (!ctx) {
    throw new Error('useNotifications must be used within NotificationProvider');
  }
  return ctx;
}

function NotificationItem({
  notification,
  onDismiss,
}: {
  notification: NotificationItem;
  onDismiss: () => void;
}) {
  const typeConfig: Record<
    NotificationType,
    { bg: string; text: string; icon: string }
  > = {
    info: { bg: 'bg-blue-500', text: 'text-blue-500', icon: 'ℹ️' },
    success: { bg: 'bg-emerald-500', text: 'text-emerald-500', icon: '✅' },
    warning: { bg: 'bg-amber-500', text: 'text-amber-500', icon: '⚠️' },
    error: { bg: 'bg-rose-500', text: 'text-rose-500', icon: '🚨' },
  };

  const config = typeConfig[notification.type];

  return (
    <div
      className={`w-80 rounded-lg border border-input bg-card text-card-foreground shadow-xl p-4 animate-in slide-in-from-bottom-4 duration-300`}
    >
      <div className="flex items-start gap-3">
        <span className={config.text}>{config.icon}</span>
        <div className="flex-1 space-y-1">
          <h4 className="font-semibold">{notification.title}</h4>
          {notification.message && (
            <p className="text-sm text-muted-foreground">
              {notification.message}
            </p>
          )}
        </div>
        <button
          onClick={onDismiss}
          className="text-muted-foreground hover:text-foreground"
        >
          <span>✕</span>
        </button>
      </div>
      {notification.duration && notification.duration > 0 && (
        <div
          className="h-1 w-full bg-secondary rounded-full mt-2 overflow-hidden"
        >
          <div
            className={`${config.bg} h-full animate-[shrink_5000ms_forwards] origin-right`}
            style={{
              animationDuration: `${notification.duration}ms`,
            }}
          />
        </div>
      )}
    </div>
  );
}
