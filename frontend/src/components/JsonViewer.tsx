'use client';

import { useState, useCallback } from 'react';

interface JsonViewerProps {
    data: Record<string, unknown>;
    title?: string;
}

export default function JsonViewer({ data, title }: JsonViewerProps) {
    const [isExpanded, setIsExpanded] = useState(true);
    const [expandAll, setExpandAll] = useState(false);
    const [copied, setCopied] = useState(false);

    const copyToClipboard = useCallback(async () => {
        try {
            await navigator.clipboard.writeText(JSON.stringify(data, null, 2));
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch (err) {
            console.error('Failed to copy:', err);
        }
    }, [data]);

    return (
        <div className="bg-muted rounded-2xl border border-border overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 bg-muted/50 border-b border-border">
                <div className="flex items-center gap-3">
                    <button
                        onClick={() => setIsExpanded(!isExpanded)}
                        className="p-1 hover:bg-muted rounded transition-colors"
                    >
                        <svg
                            className={`w-5 h-5 text-muted-foreground transition-transform ${isExpanded ? 'rotate-90' : ''}`}
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                        >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                    </button>
                    <span className="font-medium text-foreground">{title || 'Result'}</span>
                    <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">JSON</span>
                </div>

                <div className="flex items-center gap-2">
                    <button
                        onClick={() => setExpandAll(!expandAll)}
                        className="flex items-center gap-1 px-3 py-1.5 text-sm bg-muted hover:bg-muted/80 rounded-lg transition-colors text-muted-foreground"
                    >
                        {expandAll ? 'Collapse' : 'Expand'}
                    </button>
                    <button
                        onClick={copyToClipboard}
                        className="flex items-center gap-2 px-3 py-1.5 text-sm bg-muted hover:bg-muted/80 rounded-lg transition-colors"
                    >
                        {copied ? (
                            <>
                                <svg className="w-4 h-4 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                </svg>
                                <span className="text-emerald-500">Copied!</span>
                            </>
                        ) : (
                            <>
                                <svg className="w-4 h-4 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                                </svg>
                                <span className="text-muted-foreground">Copy</span>
                            </>
                        )}
                    </button>
                </div>
            </div>

            {/* Content */}
            {isExpanded && (
                <div className="p-4 overflow-x-auto font-mono text-sm">
                    <JsonTree data={data} expandAll={expandAll} />
                </div>
            )}
        </div>
    );
}

// Recursive JSON Tree Component
function JsonTree({ data, depth = 0, expandAll = false }: { data: unknown; depth?: number; expandAll?: boolean }) {
    const indent = depth * 16;

    if (data === null) {
        return <span className="text-muted-foreground">null</span>;
    }

    if (typeof data === 'boolean') {
        return <span className="text-amber-500 dark:text-amber-400">{data.toString()}</span>;
    }

    if (typeof data === 'number') {
        return <span className="text-cyan-600 dark:text-cyan-400">{data}</span>;
    }

    if (typeof data === 'string') {
        // Check if it's a long string
        if (data.length > 100 && !expandAll) {
            return (
                <span className="text-emerald-600 dark:text-emerald-400">
                    &quot;{data.slice(0, 100)}...&quot;
                    <span className="text-muted-foreground text-xs ml-1">({data.length} chars)</span>
                </span>
            );
        }
        return <span className="text-emerald-600 dark:text-emerald-400">&quot;{data}&quot;</span>;
    }

    if (Array.isArray(data)) {
        if (data.length === 0) {
            return <span className="text-muted-foreground">[]</span>;
        }

        return (
            <div>
                <span className="text-muted-foreground">[</span>
                {data.map((item, index) => (
                    <div key={index} style={{ marginLeft: indent + 16 }} className="py-0.5">
                        <JsonTree data={item} depth={depth + 1} expandAll={expandAll} />
                        {index < data.length - 1 && <span className="text-muted-foreground">,</span>}
                    </div>
                ))}
                <span className="text-muted-foreground" style={{ marginLeft: indent }}>]</span>
            </div>
        );
    }

    if (typeof data === 'object') {
        const entries = Object.entries(data as Record<string, unknown>);

        if (entries.length === 0) {
            return <span className="text-muted-foreground">{'{}'}</span>;
        }

        return (
            <div>
                <span className="text-muted-foreground">{'{'}</span>
                {entries.map(([key, value], index) => (
                    <div key={key} style={{ marginLeft: indent + 16 }} className="py-0.5">
                        <span className="text-violet-600 dark:text-violet-400">&quot;{key}&quot;</span>
                        <span className="text-muted-foreground">: </span>
                        <JsonTree data={value} depth={depth + 1} expandAll={expandAll} />
                        {index < entries.length - 1 && <span className="text-muted-foreground">,</span>}
                    </div>
                ))}
                <span className="text-muted-foreground" style={{ marginLeft: indent }}>{'}'}</span>
            </div>
        );
    }

    return <span className="text-muted-foreground">{String(data)}</span>;
}
