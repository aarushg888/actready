import { useRef, useState } from 'react'
import type { EvidenceType } from '@/lib/types'
import { EVIDENCE_TYPE_OPTIONS, inferEvidenceType } from './evidenceTypes'
import { useUploadEvidence } from '@/lib/api'
import { Button } from '@/components/ui/Button'
import { Spinner } from '@/components/ui/Spinner'
import { UploadCloud, AlertCircle } from 'lucide-react'
import { cn } from '@/lib/utils'

/**
 * Drag-drop / picker upload (INT-4). Maps suffix → engine type, lets the user
 * override, then POSTs multipart. The parent renders ingest-status polling for
 * the returned artifact id (so this component stays purely the upload step).
 */
export function UploadDropzone({ onUploaded }: { onUploaded: (artifactId: string) => void }) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const [type, setType] = useState<EvidenceType | ''>('')
  const upload = useUploadEvidence()

  const onFiles = (files: FileList | null) => {
    const f = files?.[0]
    if (!f) return
    setFile(f)
    setType(inferEvidenceType(f.name) ?? '')
  }

  const submit = async () => {
    if (!file) return
    const artifact = await upload.mutateAsync({
      file,
      evidence_type: type || undefined,
    })
    onUploaded(artifact.id)
  }

  return (
    <div className="space-y-3">
      <div
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragging(false)
          onFiles(e.dataTransfer.files)
        }}
        onClick={() => inputRef.current?.click()}
        className={cn(
          'flex cursor-pointer flex-col items-center justify-center gap-2 rounded-card border-2 border-dashed px-4 py-8 text-center transition-colors',
          dragging ? 'border-primary bg-primary/5' : 'border-border bg-muted/30 hover:bg-muted/50',
        )}
      >
        <UploadCloud className="h-7 w-7 text-muted-foreground" />
        <p className="text-sm font-medium">Drop a model card, eval JSON, or incident CSV</p>
        <p className="text-[12px] text-muted-foreground">.yaml · .yml · .json · .csv</p>
        <input
          ref={inputRef}
          type="file"
          accept=".yaml,.yml,.json,.csv"
          className="hidden"
          onChange={(e) => onFiles(e.target.files)}
        />
      </div>

      {file && (
        <div className="rounded-card border border-border p-3">
          <div className="mb-2 flex items-center justify-between">
            <span className="truncate font-mono text-[13px]">{file.name}</span>
            <span className="font-mono text-[12px] text-muted-foreground">
              {(file.size / 1024).toFixed(1)} KB
            </span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {EVIDENCE_TYPE_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => setType(opt.value)}
                className={cn(
                  'rounded-chip border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide',
                  type === opt.value
                    ? 'border-primary bg-primary text-primary-foreground'
                    : 'border-border bg-white text-muted-foreground hover:bg-muted',
                )}
              >
                {opt.label}
              </button>
            ))}
          </div>
          <Button className="mt-3 w-full" onClick={submit} disabled={upload.isPending}>
            {upload.isPending ? <Spinner /> : null}
            Upload & ingest
          </Button>
          {upload.isError && (
            <p className="mt-2 flex items-center gap-1 text-[12px] text-status-missing">
              <AlertCircle className="h-3.5 w-3.5" />
              {upload.error instanceof Error ? upload.error.message : 'Upload failed'}
            </p>
          )}
        </div>
      )}
    </div>
  )
}
