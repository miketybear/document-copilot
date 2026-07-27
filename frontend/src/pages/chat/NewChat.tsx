import { useState } from 'react'
import { useNavigate } from 'react-router'

import { ChatInput } from '@/components/chat/ChatInput'
import { SidebarTrigger } from '@/components/ui/sidebar'
import { api } from '@/lib/api'

function greeting(): string {
  const hour = new Date().getHours()
  if (hour < 12) return 'Good morning'
  if (hour < 18) return 'Good afternoon'
  return 'Good evening'
}

export function NewChat() {
  const navigate = useNavigate()
  const [creating, setCreating] = useState(false)

  async function handleSend(text: string) {
    setCreating(true)
    const thread = await api.chat.createThread()
    navigate(`/chat/${thread.id}`, { replace: true, state: { firstMessage: text } })
  }

  return (
    <div className="flex h-full flex-col">
      <div className="p-3 md:hidden">
        <SidebarTrigger />
      </div>
      <div className="flex flex-1 flex-col items-center justify-center gap-6 p-6">
        <h1 className="text-2xl font-semibold text-foreground">{greeting()}</h1>
        <div className="w-full max-w-2xl">
          <ChatInput disabled={creating} onSend={handleSend} />
        </div>
      </div>
    </div>
  )
}
