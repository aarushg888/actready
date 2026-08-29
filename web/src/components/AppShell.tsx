import { Outlet } from 'react-router-dom'
import { Sidebar } from '@/components/Sidebar'
import { TopBar } from '@/components/TopBar'

export function AppShell() {
  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto w-full max-w-content px-6 py-6">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
