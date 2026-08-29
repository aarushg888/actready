import { Routes, Route, Navigate } from 'react-router-dom'
import { ProtectedRoute } from '@/components/ProtectedRoute'
import { AppShell } from '@/components/AppShell'
import { ControlDrawer } from '@/features/controls/ControlDrawer'
import { LoginPage, RegisterPage } from '@/features/auth/LoginPage'
import { ReadinessPage } from '@/features/scorecard/ReadinessPage'
import { ControlsPage } from '@/features/controls/ControlsPage'
import { EvidencePage } from '@/features/evidence/EvidencePage'
import { ExportPage } from '@/features/export/ExportPage'

export function App() {
  return (
    <>
      <Routes>
        {/* Auth (unprotected) */}
        <Route path="/auth/login" element={<LoginPage />} />
        <Route path="/auth/register" element={<RegisterPage />} />

        {/* App shell (protected) */}
        <Route
          element={
            <ProtectedRoute>
              <AppShell />
            </ProtectedRoute>
          }
        >
          <Route path="/readiness" element={<ReadinessPage />} />
          <Route path="/controls" element={<ControlsPage />} />
          <Route path="/evidence" element={<EvidencePage />} />
          <Route path="/export" element={<ExportPage />} />
        </Route>

        <Route path="*" element={<Navigate to="/readiness" replace />} />
      </Routes>

      {/* Detail drawer renders above the shell regardless of route */}
      <ControlDrawer />
    </>
  )
}
