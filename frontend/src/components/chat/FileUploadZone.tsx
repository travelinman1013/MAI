import { useState, useRef, ReactNode, DragEvent, ChangeEvent } from 'react'
import { cn } from '@/lib/utils'
import { Upload, Paperclip } from 'lucide-react'
import { Button } from '@/components/ui/button'

export interface UploadedFile {
  id: string
  file: File
  preview?: string
  type: 'image' | 'document'
}

interface FileUploadZoneProps {
  children: ReactNode
  onFilesAdded: (files: UploadedFile[]) => void
  accept?: string
  maxFiles?: number
}

export function FileUploadZone({
  children,
  onFilesAdded,
  accept = 'image/*,.pdf,.txt,.md,.doc,.docx',
  maxFiles = 10,
}: FileUploadZoneProps) {
  const [isDragging, setIsDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const processFiles = async (fileList: FileList | File[]) => {
    const files = Array.from(fileList).slice(0, maxFiles)
    const uploadedFiles: UploadedFile[] = await Promise.all(
      files.map(async (file) => {
        const isImage = file.type.startsWith('image/')
        let preview: string | undefined

        if (isImage) {
          preview = await new Promise((resolve) => {
            const reader = new FileReader()
            reader.onloadend = () => resolve(reader.result as string)
            reader.readAsDataURL(file)
          })
        }

        return {
          id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          file,
          preview,
          type: isImage ? 'image' : 'document',
        }
      })
    )
    onFilesAdded(uploadedFiles)
  }

  const handleDragOver = (e: DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(true)
  }

  const handleDragLeave = (e: DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }

  const handleDrop = async (e: DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)

    const files = e.dataTransfer?.files
    if (files && files.length > 0) {
      await processFiles(files)
    }
  }

  const handleFileSelect = async (e: ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files && files.length > 0) {
      await processFiles(files)
    }
    e.target.value = ''
  }

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={cn(
        'relative rounded-lg transition-all',
        isDragging && 'ring-2 ring-primary ring-dashed bg-primary/5'
      )}
    >
      {isDragging && (
        <div className="absolute inset-0 bg-primary/10 flex items-center justify-center z-10 rounded-lg">
          <div className="flex flex-col items-center gap-2 text-primary">
            <Upload className="h-8 w-8" />
            <span className="text-sm font-medium">Drop files here</span>
          </div>
        </div>
      )}

      <input
        ref={inputRef}
        type="file"
        multiple
        accept={accept}
        onChange={handleFileSelect}
        className="hidden"
      />

      {children}

      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="absolute left-2 bottom-2"
        onClick={() => inputRef.current?.click()}
      >
        <Paperclip className="h-4 w-4" />
      </Button>
    </div>
  )
}
