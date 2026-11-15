import * as React from 'react';
import { cn } from '@/lib/utils';

interface ModalProps extends React.HTMLAttributes<HTMLDivElement> {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
}

function CloseIcon() {
  return (
    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
    </svg>
  );
}

export function Modal({ isOpen, onClose, title, children }: ModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="fixed inset-0 bg-black/80 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />
      <div className="relative w-full max-w-lg mx-4 transform">
        <div className="bg-card text-card-foreground rounded-xl border border-input shadow-2xl p-6">
          <div className="flex items-center justify-between mb-4">
            {title && (
              <h2 className="text-lg font-semibold">{title}</h2>
            )}
            <button
              onClick={onClose}
              className="text-muted-foreground hover:text-foreground"
            >
              <CloseIcon />
            </button>
          </div>
          <div>{children}</div>
        </div>
      </div>
    </div>
  );
}

export interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'info' | 'success' | 'warning' | 'error';
  title?: string;
  description?: string;
}

export function Alert({
  className,
  variant = 'info',
  title,
  description,
  ...props
}: AlertProps) {
  const variants = {
    info: 'bg-blue-50 border-blue-200 text-blue-900 dark:bg-blue-900/20 dark:text-blue-100 dark:border-blue-800',
    success: 'bg-emerald-50 border-emerald-200 text-emerald-900 dark:bg-emerald-900/20 dark:text-emerald-100 dark:border-emerald-800',
    warning: 'bg-amber-50 border-amber-200 text-amber-900 dark:bg-amber-900/20 dark:text-amber-100 dark:border-amber-800',
    error: 'bg-rose-50 border-rose-200 text-rose-900 dark:bg-rose-900/20 dark:text-rose-100 dark:border-rose-800',
  };

  return (
    <div
      className={cn(
        'relative rounded-lg border p-4 [&>svg]:absolute [&>svg]:left-3.5 [&>svg]:top-3.5 [&>svg]:text-current [&>svg+div]:pl-7',
        variants[variant],
        className
      )}
      {...props}
    >
      {title && (
        <h3 className="font-medium">{title}</h3>
      )}
      {description && (
        <p className="text-sm">{description}</p>
      )}
    </div>
  );
}

export interface LoadingSpinnerProps extends React.SVGProps<SVGSVGElement> {
  size?: number;
}

export function LoadingSpinner({ size = 40, className }: LoadingSpinnerProps) {
  return (
    <svg
      className={cn('animate-spin', className)}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <circle
        cx="12"
        cy="12"
        r="9.5"
        stroke="currentColor"
        strokeWidth="3"
        opacity="0.25"
      />
      <path
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
        stroke="currentColor"
        strokeWidth="3"
      />
    </svg>
  );
}

export interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
}

export function EmptyState({
  title,
  description,
  icon,
  action,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      {icon && <div className="mb-4 opacity-50">{icon}</div>}
      <h3 className="text-lg font-medium">{title}</h3>
      {description && (
        <p className="text-muted-foreground mt-2 max-w-xs mx-auto">
          {description}
        </p>
      )}
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}

export interface NotificationProps {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message?: string;
  duration?: number;
  onDismiss: () => void;
}

const TYPE_CONFIG: Record<
  NotificationProps['type'],
  { bg: string; text: string; icon: string }
> = {
  info: { bg: 'bg-blue-500', text: 'text-blue-500', icon: 'ℹ️' },
  success: { bg: 'bg-emerald-500', text: 'text-emerald-500', icon: '✅' },
  warning: { bg: 'bg-amber-500', text: 'text-amber-500', icon: '⚠️' },
  error: { bg: 'bg-rose-500', text: 'text-rose-500', icon: '🚨' },
};

export function Notification({
  id,
  type,
  title,
  message,
  duration = 5000,
  onDismiss,
}: NotificationProps) {
  const config = TYPE_CONFIG[type];

  return (
    <div
      key={id}
      className={`fixed bottom-4 right-4 z-50 w-80 rounded-lg border border-input bg-card text-card-foreground shadow-xl p-4 animate-in slide-in-from-bottom-4 duration-300`}
    >
      <div className="flex items-start gap-3">
        <span className={config.text}>{config.icon}</span>
        <div className="flex-1 space-y-1">
          <h4 className="font-semibold">{title}</h4>
          {message && <p className="text-sm text-muted-foreground">{message}</p>}
        </div>
        <button
          onClick={onDismiss}
          className="text-muted-foreground hover:text-foreground"
        >
          <CloseIcon />
        </button>
      </div>
      {duration > 0 && (
        <div
          className="h-1 w-full bg-secondary rounded-full mt-2 overflow-hidden"
        >
          <div
            className={`${config.bg} h-full animate-[shrink_5000ms_forwards] origin-right`}
            style={{ animationDuration: `${duration}ms` }}
          />
        </div>
      )}
    </div>
  );
}
