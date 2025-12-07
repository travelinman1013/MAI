import { X, FileText, File } from 'lucide-react'
import { Button } from '@/components/ui/button'
import type { UploadedFile } from './FileUploadZone'

interface FilePreviewProps {
  file: UploadedFile
  onRemove: () => void
}

export function FilePreview({ file, onRemove }: FilePreviewProps) {
  const getFileIcon = () => {
    const ext = file.file.name.split('.').pop()?.toLowerCase()
    if (['pdf', 'doc', 'docx', 'txt', 'md'].includes(ext || '')) {
      return <FileText className="h-6 w-6" />
    }
    return <File className="h-6 w-6" />
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return (
    <div className="relative group">
      {file.type === 'image' && file.preview ? (
        <div className="relative">
          <img
            src={file.preview}
            alt={file.file.name}
            className="h-16 w-16 object-cover rounded-md border border-border"
          />
          <Button
            type="button"
            variant="destructive"
            size="icon"
            className="absolute -top-2 -right-2 h-5 w-5 opacity-0 group-hover:opacity-100 transition-opacity"
            onClick={onRemove}
          >
            <X className="h-3 w-3" />
          </Button>
        </div>
      ) : (
        <div className="relative flex items-center gap-2 p-2 rounded-md border border-border bg-muted">
          <div className="text-muted-foreground">
            {getFileIcon()}
          </div>
          <div className="flex flex-col min-w-0">
            <span className="text-xs font-medium truncate max-w-[100px]">
              {file.file.name}
            </span>
            <span className="text-xs text-muted-foreground">
              {formatFileSize(file.file.size)}
            </span>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-5 w-5 ml-auto opacity-0 group-hover:opacity-100 transition-opacity"
            onClick={onRemove}
          >
            <X className="h-3 w-3" />
          </Button>
        </div>
      )}
    </div>
  )
}
