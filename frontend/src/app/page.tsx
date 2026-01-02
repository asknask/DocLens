'use client';

import { useState, useCallback } from 'react';
import UploadBox from '@/components/UploadBox';
import ActionForm from '@/components/ActionForm';
import ResultsTabs from '@/components/ResultsTabs';
import LimitsNotice from '@/components/LimitsNotice';
import { ThemeToggle } from '@/components/ThemeToggle';
import {
  uploadFile,
  runAction,
  pollJobStatus,
  FileMetadata,
  LimitsInfo,
  ActionType,
  JobStatus,
  ApiError,
  getActionLabel,
} from '@/lib/api';

type AppState = 'idle' | 'uploading' | 'ready' | 'processing' | 'completed' | 'error';

export default function Home() {
  const [state, setState] = useState<AppState>('idle');
  const [jobId, setJobId] = useState<string | null>(null);
  const [uploadedFile, setUploadedFile] = useState<FileMetadata | null>(null);
  const [limits, setLimits] = useState<LimitsInfo | null>(null);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [processingStatus, setProcessingStatus] = useState<JobStatus | null>(null);
  const [completedAction, setCompletedAction] = useState<ActionType | null>(null);
  const [metrics, setMetrics] = useState<Record<string, unknown> | null>(null);

  const handleUpload = useCallback(async (file: File) => {
    setState('uploading');
    setError(null);
    setResult(null);

    try {
      const response = await uploadFile(file);
      setJobId(response.job_id);
      setUploadedFile(response.file);
      setLimits(response.limits);
      setState('ready');
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Failed to upload file');
      }
      setState('error');
    }
  }, []);

  const handleRunAction = useCallback(async (
    action: ActionType,
    options: Record<string, unknown>,
    refine: string
  ) => {
    if (!jobId) return;

    setState('processing');
    setError(null);
    setProcessingStatus('processing');

    try {
      await runAction({
        job_id: jobId,
        action,
        options: Object.keys(options).length > 0 ? options : undefined,
        refine: refine || undefined,
        output_format: 'descriptive',
      });

      // Poll for completion
      const finalStatus = await pollJobStatus(jobId, {
        interval: 1000,
        maxAttempts: 120,
        onProgress: (status) => setProcessingStatus(status),
      });

      if (finalStatus.status === 'completed' && finalStatus.result) {
        setResult(finalStatus.result);
        setCompletedAction(finalStatus.action);
        setMetrics(finalStatus.metrics as unknown as Record<string, unknown>);
        setState('completed');
      } else if (finalStatus.error) {
        setError(finalStatus.error.message);
        setState('error');
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Processing failed');
      }
      setState('error');
    }
  }, [jobId]);

  const handleReset = useCallback(() => {
    setState('idle');
    setJobId(null);
    setUploadedFile(null);
    setResult(null);
    setError(null);
    setProcessingStatus(null);
    setCompletedAction(null);
    setMetrics(null);
  }, []);

  const handleNewAnalysis = useCallback(() => {
    setResult(null);
    setError(null);
    setProcessingStatus(null);
    setCompletedAction(null);
    setMetrics(null);
    setState('ready');
  }, []);

  return (
    <div className="min-h-screen bg-background text-foreground transition-colors duration-300">
      <div className="relative z-10">
        {/* Header */}
        <header className="border-b border-border bg-background/50 backdrop-blur-xl">
          <div className="max-w-5xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-600 to-fuchsia-600 flex items-center justify-center shadow-lg shadow-violet-500/20">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <div>
                <h1 className="text-xl font-bold">DocLens</h1>
                <p className="text-xs text-muted-foreground">AI Document Analyzer</p>
              </div>
            </div>

            <div className="flex items-center gap-4">
              {state !== 'idle' && (
                <button
                  onClick={handleReset}
                  className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
                >
                  Start Over
                </button>
              )}
              <ThemeToggle />
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="max-w-5xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
          {/* Hero Section - Only show on idle */}
          {state === 'idle' && (
            <div className="text-center mb-12">
              <h2 className="text-3xl sm:text-4xl font-bold mb-4">
                Analyze Documents with AI
              </h2>
              <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                Upload PDFs, DOCX files, or images. Get instant summaries,
                extract structured data, classify documents, and more.
              </p>
            </div>
          )}

          <div className="space-y-8">
            {/* Upload Section */}
            {(state === 'idle' || state === 'uploading' || state === 'error') && (
              <UploadBox
                onUpload={handleUpload}
                isUploading={state === 'uploading'}
                uploadedFile={null}
                error={state === 'error' ? error : null}
              />
            )}

            {/* Ready State - Show file and action form */}
            {(state === 'ready' || state === 'processing') && (
              <>
                <UploadBox
                  onUpload={handleUpload}
                  isUploading={false}
                  uploadedFile={uploadedFile}
                  error={null}
                />

                <ActionForm
                  onSubmit={handleRunAction}
                  isProcessing={state === 'processing'}
                  disabled={false}
                />

                {state === 'processing' && (
                  <div className="text-center py-8">
                    <div className="inline-flex items-center gap-3 px-6 py-3 bg-muted rounded-full">
                      <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                      <span className="text-muted-foreground">
                        {processingStatus === 'processing' ? 'Analyzing document...' : 'Preparing...'}
                      </span>
                    </div>
                  </div>
                )}
              </>
            )}

            {/* Completed State - Show results */}
            {state === 'completed' && result && (
              <>
                <UploadBox
                  onUpload={handleUpload}
                  isUploading={false}
                  uploadedFile={uploadedFile}
                  error={null}
                />

                <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-4 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-emerald-500/20 flex items-center justify-center">
                      <svg className="w-5 h-5 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                    <div>
                      <p className="font-medium">
                        {completedAction ? getActionLabel(completedAction) : 'Analysis'} Complete
                      </p>
                      {metrics && (
                        <p className="text-sm text-muted-foreground">
                          Completed in {(metrics.total_time_ms as number) / 1000}s
                          {metrics.vision_pages ? ` • ${metrics.vision_pages} images processed` : ''}
                        </p>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={handleNewAnalysis}
                    className="px-4 py-2 bg-secondary hover:bg-secondary/80 text-secondary-foreground rounded-lg transition-colors text-sm"
                  >
                    Run Another
                  </button>
                </div>

                <ResultsTabs
                  jobId={jobId!}
                  action={completedAction!}
                  descriptiveResult={result}
                />
              </>
            )}

            {/* Error State with results */}
            {state === 'error' && error && uploadedFile && (
              <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-red-500/20 flex items-center justify-center">
                    <svg className="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </div>
                  <div>
                    <p className="font-medium">Error</p>
                    <p className="text-sm text-red-500">{error}</p>
                  </div>
                </div>
              </div>
            )}

            {/* Limits Notice */}
            {limits && (
              <LimitsNotice limits={limits} />
            )}
          </div>
        </main>

        {/* Footer */}
        <footer className="border-t border-border mt-12">
          <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6 text-center text-sm text-muted-foreground">
            <p>DocLens - An AI powered document analysis tool (POC).</p>
            <p>Some features may not work as expected. Send feedback to <a href="mailto:asimonwave@gmail.com">asimonwave@gmail.com</a></p>
            <br />
            <p className="text-xs">Created by Asim</p>
          </div>
        </footer>
      </div>
    </div>
  );
}
