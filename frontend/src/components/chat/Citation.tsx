import { useState } from 'react'

import type { CitationData } from '@/lib/citations'

const EXCERPT_PREVIEW_LENGTH = 220

function CitationCard({ citation, highlighted }: { citation: CitationData; highlighted: boolean }) {
  const [expanded, setExpanded] = useState(false)
  const isLong = citation.excerpt.length > EXCERPT_PREVIEW_LENGTH
  const shownExcerpt =
    expanded || !isLong ? citation.excerpt : `${citation.excerpt.slice(0, EXCERPT_PREVIEW_LENGTH)}…`

  return (
    <div
      id={`citation-${citation.chunkId}`}
      className={`border-b border-border p-3 text-sm last:border-b-0 ${highlighted ? 'bg-accent' : ''}`}
    >
      <p className="font-medium text-foreground">{citation.documentTitle}</p>
      <p className="font-mono text-xs text-muted-foreground tabular-nums">
        {[citation.department, citation.version && `v${citation.version}`, citation.effectiveDate]
          .filter(Boolean)
          .join(' · ')}
      </p>
      {citation.headingPath.length > 0 && (
        <p className="mt-1 text-xs text-primary">{citation.headingPath.join(' › ')}</p>
      )}
      <p className="mt-1.5 whitespace-pre-wrap text-muted-foreground">{shownExcerpt}</p>
      {isLong && (
        <button
          type="button"
          className="mt-1 text-xs font-medium text-primary underline"
          onClick={() => setExpanded((v) => !v)}
        >
          {expanded ? 'Show less' : 'Show more'}
        </button>
      )}
    </div>
  )
}

export function CitationCluster({ citations }: { citations: CitationData[] }) {
  const [open, setOpen] = useState(false)
  const [highlighted, setHighlighted] = useState<string | null>(null)

  if (citations.length === 0) return null

  function reveal(chunkId: string) {
    setOpen(true)
    setHighlighted(chunkId)
  }

  return (
    <div className="mr-auto flex max-w-[80%] flex-col gap-1.5">
      <div className="flex flex-wrap items-center gap-1.5">
        {citations.map((citation, i) => (
          <button
            key={citation.chunkId}
            type="button"
            aria-label={`Show source ${i + 1}: ${citation.documentTitle}`}
            className="flex size-[18px] items-center justify-center rounded-full bg-accent font-mono text-[11px] tabular-nums text-primary hover:bg-primary hover:text-primary-foreground"
            onClick={() => reveal(citation.chunkId)}
          >
            {i + 1}
          </button>
        ))}
        <button
          type="button"
          className="text-xs text-muted-foreground underline hover:text-primary"
          onClick={() => setOpen((v) => !v)}
        >
          {open ? 'Hide sources' : `Show sources (${citations.length})`}
        </button>
      </div>

      {open && (
        <div className="overflow-hidden rounded-md border border-border">
          <div className="border-b border-border bg-muted px-3 py-1.5 text-[11px] font-medium tracking-wide text-muted-foreground uppercase">
            Sources
          </div>
          {citations.map((citation) => (
            <CitationCard
              key={citation.chunkId}
              citation={citation}
              highlighted={citation.chunkId === highlighted}
            />
          ))}
        </div>
      )}
    </div>
  )
}
