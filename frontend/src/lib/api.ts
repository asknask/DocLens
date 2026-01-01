/**
 * DocLens API Client
 * Handles all API communication with the backend
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ============== Types ==============

export type ActionType = 'summarize' | 'extract_structured' | 'classify' | 'qa' | 'transform';

export type JobStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'rate_limited';

export interface FileMetadata {
    filename: string;
    content_type: string;
    size_bytes: number;
    file_type: string;
    page_count: number | null;
    char_count: number | null;
    image_count: number | null;
}

export interface LimitsInfo {
    max_file_size_mb: number;
    max_pages: number;
    max_chars: number;
    uploads_remaining: number | null;
    runs_remaining: number | null;
}

export interface UploadResponse {
    job_id: string;
    status: JobStatus;
    file: FileMetadata;
    limits: LimitsInfo;
    created_at: string;
    expires_at: string;
}

export interface RunRequest {
    job_id: string;
    action: ActionType;
    options?: Record<string, unknown>;
    refine?: string;
    output_format?: 'descriptive' | 'json';
}

export interface RunResponse {
    job_id: string;
    status: JobStatus;
    action: ActionType;
    message: string | null;
}

export interface ErrorDetail {
    code: string;
    message: string;
    details?: Record<string, unknown>;
}

export interface ProcessingMetrics {
    extraction_time_ms: number | null;
    vision_time_ms: number | null;
    action_time_ms: number | null;
    total_time_ms: number | null;
    pages_processed: number | null;
    vision_pages: number | null;
    tokens_used: number | null;
}

export interface JobStatusResponse {
    job_id: string;
    status: JobStatus;
    action: ActionType | null;
    result: Record<string, unknown> | null;
    error: ErrorDetail | null;
    metrics: ProcessingMetrics | null;
    created_at: string;
    updated_at: string;
}

// ============== API Error ==============

export class ApiError extends Error {
    constructor(
        public status: number,
        public code: string,
        message: string,
        public details?: Record<string, unknown>
    ) {
        super(message);
        this.name = 'ApiError';
    }
}

// ============== API Functions ==============

/**
 * Upload a file for analysis
 */
export async function uploadFile(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}/api/upload`, {
        method: 'POST',
        body: formData,
    });

    if (!response.ok) {
        const error = await response.json();
        throw new ApiError(
            response.status,
            error.error || 'upload_failed',
            error.message || error.detail || 'Upload failed',
            error.details
        );
    }

    return response.json();
}

/**
 * Run an analysis action on an uploaded document
 */
export async function runAction(request: RunRequest): Promise<RunResponse> {
    const response = await fetch(`${API_BASE_URL}/api/run`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new ApiError(
            response.status,
            error.error || 'run_failed',
            error.message || error.detail || 'Action failed',
            error.details
        );
    }

    return response.json();
}

/**
 * Get the status and result of a job
 */
export async function getJobStatus(jobId: string): Promise<JobStatusResponse> {
    const response = await fetch(`${API_BASE_URL}/api/job/${jobId}`);

    if (!response.ok) {
        const error = await response.json();
        throw new ApiError(
            response.status,
            error.error || 'status_failed',
            error.message || error.detail || 'Failed to get job status',
            error.details
        );
    }

    return response.json();
}

/**
 * Poll for job completion
 */
export async function pollJobStatus(
    jobId: string,
    options: {
        interval?: number;
        maxAttempts?: number;
        onProgress?: (status: JobStatus) => void;
    } = {}
): Promise<JobStatusResponse> {
    const { interval = 1000, maxAttempts = 120, onProgress } = options;

    let attempts = 0;

    while (attempts < maxAttempts) {
        const status = await getJobStatus(jobId);

        if (onProgress) {
            onProgress(status.status);
        }

        if (status.status === 'completed' || status.status === 'failed') {
            return status;
        }

        attempts++;
        await new Promise(resolve => setTimeout(resolve, interval));
    }

    throw new ApiError(408, 'timeout', 'Polling timed out');
}

// ============== Helpers ==============

export function formatFileSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function getActionLabel(action: ActionType): string {
    const labels: Record<ActionType, string> = {
        summarize: 'Summarize',
        extract_structured: 'Extract Data',
        classify: 'Classify',
        qa: 'Q&A',
        transform: 'Transform',
    };
    return labels[action];
}

export function getActionDescription(action: ActionType): string {
    const descriptions: Record<ActionType, string> = {
        summarize: 'Generate a summary with key findings and bullet points',
        extract_structured: 'Extract entities, dates, amounts, and other structured data',
        classify: 'Classify the document type (invoice, contract, resume, etc.)',
        qa: 'Ask questions about the document content',
        transform: 'Transform the document to a different format',
    };
    return descriptions[action];
}
