import { Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from './AppLayout'
import { AuthProvider } from './auth/AuthContext'
import { LoginPage } from './auth/LoginPage'
import { ProtectedRoute } from './auth/ProtectedRoute'
import { BriefPage } from './features/briefs/BriefPage'
import { CapturePage } from './features/capture/CapturePage'
import { UnmatchedListPage } from './features/capture/UnmatchedListPage'
import { CommitmentsDuePage } from './features/commitments/CommitmentsDuePage'
import { HomePage } from './features/home/HomePage'
import { QAChatPage } from './features/qa/QAChatPage'

export function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <AppLayout>
                <Routes>
                  <Route path="/" element={<HomePage />} />
                  <Route path="/capture" element={<CapturePage />} />
                  <Route path="/unmatched" element={<UnmatchedListPage />} />
                  <Route path="/ask" element={<QAChatPage />} />
                  <Route path="/briefs" element={<BriefPage />} />
                  <Route path="/commitments" element={<CommitmentsDuePage />} />
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
              </AppLayout>
            </ProtectedRoute>
          }
        />
      </Routes>
    </AuthProvider>
  )
}
