import { Gauge, Rocket, Moon, Radio } from 'lucide-react';
import { NavLink } from '@/components/NavLink';
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarHeader,
  SidebarFooter,
  useSidebar,
} from '@/components/ui/sidebar';

const navItems = [
  { title: 'Dashboard', url: '/', icon: Gauge, description: 'Manual Control' },
  { title: 'Missions', url: '/missions', icon: Rocket, description: 'Automation' },
];

interface AppSidebarProps {
  isConnected?: boolean;
}

export function AppSidebar({ isConnected = false }: AppSidebarProps) {
  const { state } = useSidebar();
  const isCollapsed = state === 'collapsed';

  return (
    <Sidebar 
      className="border-r border-border/30 bg-card/50 backdrop-blur-xl"
      collapsible="icon"
    >
      <SidebarHeader className="border-b border-border/30 p-4">
        <div className="flex items-center gap-3">
          <div className="relative">
            <Moon className="w-8 h-8 text-primary" />
            <div className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-primary animate-pulse" />
          </div>
          {!isCollapsed && (
            <div className="flex flex-col">
              <span className="font-display text-sm font-bold tracking-wider text-foreground">
                LUNAR OPS
              </span>
              <span className="text-[10px] text-muted-foreground font-mono">
                MISSION CONTROL v2.0
              </span>
            </div>
          )}
        </div>
      </SidebarHeader>

      <SidebarContent className="p-2">
        <SidebarGroup>
          <SidebarGroupLabel className="text-[10px] text-muted-foreground font-mono tracking-widest px-2">
            OPERATIONS
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {navItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild tooltip={item.title}>
                    <NavLink
                      to={item.url}
                      end={item.url === '/'}
                      className="flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 text-muted-foreground hover:text-foreground hover:bg-primary/10 group"
                      activeClassName="bg-primary/20 text-primary border border-primary/30 shadow-[0_0_15px_-3px_hsl(var(--primary)/0.3)]"
                    >
                      <item.icon className="w-5 h-5 shrink-0 group-hover:text-primary transition-colors" />
                      {!isCollapsed && (
                        <div className="flex flex-col">
                          <span className="text-sm font-semibold">{item.title}</span>
                          <span className="text-[10px] text-muted-foreground/70 font-mono">
                            {item.description}
                          </span>
                        </div>
                      )}
                    </NavLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="border-t border-border/30 p-4">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-success animate-pulse' : 'bg-destructive'}`} />
          {!isCollapsed && (
            <div className="flex items-center gap-2">
              <Radio className="w-3 h-3 text-muted-foreground" />
              <span className="text-[10px] text-muted-foreground font-mono">
                {isConnected ? 'UPLINK ACTIVE' : 'NO SIGNAL'}
              </span>
            </div>
          )}
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}
