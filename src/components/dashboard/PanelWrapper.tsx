import { ReactNode } from 'react';

interface PanelWrapperProps {
  title: string;
  children: ReactNode;
  badge?: ReactNode;
  className?: string;
}

export function PanelWrapper({ title, children, badge, className = '' }: PanelWrapperProps) {
  return (
    <div className={`glass-panel chamfer flex flex-col ${className}`}>
      <div className="panel-header">
        <h2 className="panel-title">{title}</h2>
        {badge}
      </div>
      <div className="flex-1 p-3 overflow-hidden">
        {children}
      </div>
    </div>
  );
}
