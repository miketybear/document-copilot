import { Route, Routes } from 'react-router'

import { RequireAdmin } from '@/components/RequireAdmin'
import { RequireAuth } from '@/components/RequireAuth'
import { AppShell } from '@/components/layout/AppShell'
import { SignIn } from '@/pages/auth/SignIn'
import { ChatPage } from '@/pages/chat/ChatPage'
import { NewChat } from '@/pages/chat/NewChat'
import { ConnectionsPage } from '@/pages/settings/ConnectionsPage'

function App() {
  return (
    <Routes>
      <Route path="/sign-in" element={<SignIn />} />
      <Route
        element={
          <RequireAuth>
            <AppShell />
          </RequireAuth>
        }
      >
        <Route path="/" element={<NewChat />} />
        <Route path="/chat/:threadId" element={<ChatPage />} />
        <Route
          path="/settings/connections"
          element={
            <RequireAdmin>
              <ConnectionsPage />
            </RequireAdmin>
          }
        />
      </Route>
    </Routes>
  )
}

export default App
