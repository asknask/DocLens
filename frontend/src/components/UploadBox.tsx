'use client';

import { useState, useCallback } from 'react';
import { FileMetadata, formatFileSize } from '@/lib/api';

interface UploadBoxProps {
    onUpload: (file: File) => Promise<void>;
    isUploading: boolean;
    uploadedFile: FileMetadata | null;
    error: string | null;
}

const ACCEPTED_TYPES = {
    'application/pdf': ['.pdf'],
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    'image/jpeg': ['.jpg', '.jpeg'],
    'image/png': ['.png'],
    'image/webp': ['.webp'],
    'image/gif': ['.gif'],
    'text/plain': ['.txt'],
};

const ACCEPTED_EXTENSIONS = Object.values(ACCEPTED_TYPES).flat();

export default function UploadBox({
    onUpload,
    isUploading,
    uploadedFile,
    error
}: UploadBoxProps) {
    const [isDragging, setIsDragging] = useState(false);
    const [localError, setLocalError] = useState<string | null>(null);

    const validateFile = (file: File): boolean => {
        const ext = '.' + file.name.split('.').pop()?.toLowerCase();

        if (!ACCEPTED_EXTENSIONS.includes(ext)) {
            setLocalError(`Unsupported file type. Accepted: PDF, DOCX, TXT, JPEG, PNG, WebP, GIF`);
            return false;
        }

        // 20MB limit check client-side
        if (file.size > 20 * 1024 * 1024) {
            setLocalError('File too large. Maximum size is 20MB.');
            return false;
        }

        setLocalError(null);
        return true;
    };

    const handleFile = useCallback(async (file: File) => {
        if (validateFile(file)) {
            await onUpload(file);
        }
    }, [onUpload]);

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);

        const file = e.dataTransfer.files[0];
        if (file) {
            handleFile(file);
        }
    }, [handleFile]);

    const handleDragOver = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(true);
    }, []);

    const handleDragLeave = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
    }, []);

    const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            handleFile(file);
        }
    }, [handleFile]);

    const displayError = error || localError;

    if (uploadedFile) {
        return (
            <div className="bg-gradient-to-br from-emerald-500/10 to-teal-500/10 rounded-2xl p-6 border border-emerald-500/30">
                <div className="flex items-center gap-4">
                    <div className="w-14 h-14 rounded-xl bg-emerald-500/20 flex items-center justify-center">
                        <svg className="w-7 h-7 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                    </div>
                    <div className="flex-1 min-w-0">
                        <h3 className="text-lg font-semibold text-foreground truncate">{uploadedFile.filename}</h3>
                        <div className="flex items-center gap-3 text-sm text-muted-foreground mt-1">
                            <span className="px-2 py-0.5 bg-emerald-500/20 rounded text-emerald-500 font-medium text-xs">
                                {uploadedFile.file_type}
                            </span>
                            <span>{formatFileSize(uploadedFile.size_bytes)}</span>
                            {uploadedFile.page_count && (
                                <span>{uploadedFile.page_count} pages</span>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            className={`
        relative rounded-2xl border-2 border-dashed transition-all duration-300 cursor-pointer
        ${isDragging
                    ? 'border-violet-400 bg-violet-500/10 scale-[1.02]'
                    : 'border-slate-700 hover:border-violet-500/50 hover:bg-slate-800/50'
                }
        ${isUploading ? 'pointer-events-none opacity-70' : ''}
      `}
        >
            <input
                type="file"
                accept={Object.keys(ACCEPTED_TYPES).join(',')}
                onChange={handleInputChange}
                disabled={isUploading}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                id="file-upload"
            />

            <div className="p-10 text-center">
                {isUploading ? (
                    <>
                        <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-violet-500/20 flex items-center justify-center">
                            <svg className="w-8 h-8 text-violet-400 animate-spin" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                            </svg>
                        </div>
                        <p className="text-lg font-medium text-foreground">Uploading...</p>
                    </>
                ) : (
                    <>
                        <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-violet-500/20 to-fuchsia-500/20 flex items-center justify-center">
                            <svg className="w-8 h-8 text-violet-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                            </svg>
                        </div>
                        <p className="text-lg font-medium text-foreground mb-2">
                            {isDragging ? 'Drop your file here' : 'Drag & drop or click to upload'}
                        </p>
                        <p className="text-sm text-muted-foreground">
                            PDF, DOCX, TXT, JPEG, PNG, WebP, GIF • Max 20MB
                        </p>
                    </>
                )}

                {displayError && (
                    <div className="mt-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
                        <p className="text-sm text-red-400">{displayError}</p>
                    </div>
                )}
            </div>
        </div>
    );
}
