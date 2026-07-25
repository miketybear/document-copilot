import { Route, Routes } from 'react-router'

import { RequireAuth } from '@/components/RequireAuth'
import { SignIn } from '@/pages/auth/SignIn'
import { ChatPage } from '@/pages/chat/ChatPage'
import { NewChat } from '@/pages/chat/NewChat'

function App() {
  return (
    <Routes>
      <Route path="/sign-in" element={<SignIn />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <NewChat />
          </RequireAuth>
        }
      />
      <Route
        path="/chat/:threadId"
        element={
          <RequireAuth>
            <ChatPage />
          </RequireAuth>
        }
      />
    </Routes>
  )
}

export default App
