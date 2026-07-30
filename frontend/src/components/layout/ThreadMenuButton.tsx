import { Pin } from 'lucide-react'
import { useCallback, useRef, useState } from 'react'
import { Link } from 'react-router'

import { SidebarMenuButton } from '@/components/ui/sidebar'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import type { ChatThread } from '@/lib/api'

export function ThreadMenuButton({
  thread,
  isActive,
  onNavigate,
}: {
  thread: ChatThread
  isActive: boolean
  onNavigate: () => void
}) {
  const [isTruncated, setIsTruncated] = useState(false)
  const observerRef = useRef<ResizeObserver | null>(null)
  const title = thread.title ?? 'Untitled chat'

  // A callback ref (rather than useEffect) so the observer re-attaches whenever the title span's
  // underlying DOM node changes — which happens whenever isTruncated flips and this component
  // switches between rendering a plain button and a Tooltip-wrapped one (a different element type
  // at that position, so React unmounts/remounts the span instead of reusing it).
  const titleRef = useCallback((el: HTMLSpanElement | null) => {
    observerRef.current?.disconnect()
    observerRef.current = null
    if (!el) return

    const checkOverflow = () => setIsTruncated(el.scrollWidth > el.clientWidth)
    checkOverflow()

    const observer = new ResizeObserver(checkOverflow)
    observer.observe(el)
    observerRef.current = observer
  }, [])

  const content = (
    <>
      {thread.pinned_at && <Pin className="size-3.5 shrink-0 text-primary" aria-hidden="true" />}
      <span ref={titleRef} className="truncate">
        {title}
      </span>
    </>
  )

  if (!isTruncated) {
    return (
      <SidebarMenuButton isActive={isActive} render={<Link to={`/chat/${thread.id}`} onClick={onNavigate} />}>
        {content}
      </SidebarMenuButton>
    )
  }

  return (
    <Tooltip>
      <TooltipTrigger
        render={<SidebarMenuButton isActive={isActive} render={<Link to={`/chat/${thread.id}`} onClick={onNavigate} />} />}
      >
        {content}
      </TooltipTrigger>
      <TooltipContent side="right">{title}</TooltipContent>
    </Tooltip>
  )
}
