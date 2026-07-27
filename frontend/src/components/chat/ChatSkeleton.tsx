import { Skeleton } from '@/components/ui/skeleton'

export function ChatSkeleton() {
  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex items-center gap-2 border-b border-border px-3 py-3.5 md:px-7">
        <Skeleton className="h-4 w-40" />
      </div>

      <div className="mx-auto flex w-full min-h-0 max-w-2xl flex-1 flex-col gap-6 overflow-hidden p-6">
        <Skeleton className="ml-auto h-9 w-2/5 rounded-2xl rounded-br-sm" />

        <div className="flex max-w-[85%] flex-col gap-2">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-11/12" />
          <Skeleton className="h-4 w-3/5" />
        </div>

        <Skeleton className="ml-auto h-9 w-1/3 rounded-2xl rounded-br-sm" />

        <div className="flex max-w-[85%] flex-col gap-2">
          <Skeleton className="h-4 w-10/12" />
          <Skeleton className="h-4 w-2/5" />
        </div>
      </div>
    </div>
  )
}
