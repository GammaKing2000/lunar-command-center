import { ReactNode } from 'react';
import { SidebarProvider, SidebarTrigger, SidebarInset } from '@/components/ui/sidebar';
import { AppSidebar } from './AppSidebar';

interface AppLayoutProps {
  children: ReactNode;
  isConnected?: boolean;
}

export function AppLayout({ children, isConnected = false }: AppLayoutProps) {
  return (
    <SidebarProvider defaultOpen={true}>
      <div className="min-h-screen flex w-full bg-background grid-bg">
        <AppSidebar isConnected={isConnected} />
        <SidebarInset className="flex-1">
          <header className="h-10 flex items-center border-b border-border/30 bg-card/30 backdrop-blur-sm px-4">
            <SidebarTrigger className="text-muted-foreground hover:text-foreground" />
          </header>
          <main className="flex-1 overflow-auto">
            {children}
          </main>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
}
