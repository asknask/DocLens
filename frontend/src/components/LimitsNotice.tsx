'use client';

import { useState } from 'react';
import { LimitsInfo } from '@/lib/api';

interface LimitsNoticeProps {
    limits: LimitsInfo | null;
}

export default function LimitsNotice({ limits }: LimitsNoticeProps) {
    const [isExpanded, setIsExpanded] = useState(false);

    if (!limits) return null;

    return (
        <div className="bg-muted/50 rounded-xl border border-border overflow-hidden">
            <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-muted transition-colors"
            >
                <div className="flex items-center gap-2">
                    <svg className="w-5 h-5 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span className="text-sm font-medium text-foreground">Usage Limits</span>
                </div>
                <div className="flex items-center gap-3">
                    {limits.uploads_remaining !== null && (
                        <span className="text-xs text-muted-foreground">
                            {limits.uploads_remaining} uploads left
                        </span>
                    )}
                    <svg
                        className={`w-4 h-4 text-muted-foreground transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                    >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                </div>
            </button>

            {isExpanded && (
                <div className="px-4 py-3 border-t border-border space-y-3">
                    <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                            <span className="text-muted-foreground">Max File Size</span>
                            <span className="block text-foreground font-medium">{limits.max_file_size_mb} MB</span>
                        </div>
                        <div>
                            <span className="text-muted-foreground">Max PDF Pages</span>
                            <span className="block text-foreground font-medium">{limits.max_pages} pages</span>
                        </div>
                        <div>
                            <span className="text-muted-foreground">Uploads Remaining</span>
                            <span className="block text-foreground font-medium">
                                {limits.uploads_remaining ?? '—'} / hour
                            </span>
                        </div>
                        <div>
                            <span className="text-muted-foreground">Runs Remaining</span>
                            <span className="block text-foreground font-medium">
                                {limits.runs_remaining ?? '—'} / hour
                            </span>
                        </div>
                    </div>

                    <p className="text-xs text-muted-foreground">
                        Rate limits reset every hour. Jobs expire after 60 minutes.
                    </p>
                </div>
            )}
        </div>
    );
}
