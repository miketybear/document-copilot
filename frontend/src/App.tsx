import { Route, Routes } from 'react-router'

import { RequireAuth } from '@/components/RequireAuth'
import { Home } from '@/pages/Home'
import { SignIn } from '@/pages/auth/SignIn'

function App() {
  return (
    <Routes>
      <Route path="/sign-in" element={<SignIn />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <Home />
          </RequireAuth>
        }
      />
    </Routes>
  )
}

export default App
