'use client';

import { useState, useEffect } from 'react';
import JsonViewer from './JsonViewer';
import { runAction, getJobStatus, pollJobStatus, ActionType, JobStatusResponse } from '@/lib/api';

interface ResultsTabsProps {
    jobId: string;
    action: ActionType;
    descriptiveResult: Record<string, unknown> | null;
    onJsonLoaded?: (data: Record<string, unknown>) => void;
}

export default function ResultsTabs({
    jobId,
    action,
    descriptiveResult,
    onJsonLoaded
}: ResultsTabsProps) {
    const [activeTab, setActiveTab] = useState<'description' | 'json'>('description');
    const [jsonResult, setJsonResult] = useState<Record<string, unknown> | null>(null);
    const [jsonLoading, setJsonLoading] = useState(false);
    const [jsonError, setJsonError] = useState<string | null>(null);

    // Lazy load JSON when tab is clicked
    useEffect(() => {
        if (activeTab === 'json' && !jsonResult && !jsonLoading && !jsonError) {
            loadJsonResult();
        }
    }, [activeTab]);

    const loadJsonResult = async () => {
        setJsonLoading(true);
        setJsonError(null);

        try {
            // Run the action again with JSON output format
            await runAction({
                job_id: jobId,
                action: action,
                output_format: 'json',
            });

            // Poll for completion
            const status = await pollJobStatus(jobId, {
                interval: 1000,
                maxAttempts: 60,
            });

            if (status.status === 'completed' && status.result) {
                setJsonResult(status.result);
                onJsonLoaded?.(status.result);
            } else if (status.error) {
                setJsonError(status.error.message);
            }
        } catch (err) {
            setJsonError(err instanceof Error ? err.message : 'Failed to load JSON');
        } finally {
            setJsonLoading(false);
        }
    };

    // Parse inline markdown formatting (bold, italic, code, links)
    const parseInlineMarkdown = (text: string, keyPrefix: string): React.ReactNode[] => {
        const result: React.ReactNode[] = [];
        let remaining = text;
        let partIndex = 0;

        while (remaining.length > 0) {
            // Check for bold text: **text** or __text__
            const boldMatch = remaining.match(/^(\*\*|__)(.+?)\1/);
            if (boldMatch) {
                result.push(<strong key={`${keyPrefix}-${partIndex}`} className="font-semibold text-foreground">{boldMatch[2]}</strong>);
                remaining = remaining.slice(boldMatch[0].length);
                partIndex++;
                continue;
            }

            // Check for italic text: *text* or _text_
            const italicMatch = remaining.match(/^(\*|_)([^*_]+?)\1/);
            if (italicMatch) {
                result.push(<em key={`${keyPrefix}-${partIndex}`} className="italic">{italicMatch[2]}</em>);
                remaining = remaining.slice(italicMatch[0].length);
                partIndex++;
                continue;
            }

            // Check for inline code: `code`
            const codeMatch = remaining.match(/^`([^`]+)`/);
            if (codeMatch) {
                result.push(
                    <code key={`${keyPrefix}-${partIndex}`} className="bg-muted px-1.5 py-0.5 rounded text-sm font-mono text-primary">
                        {codeMatch[1]}
                    </code>
                );
                remaining = remaining.slice(codeMatch[0].length);
                partIndex++;
                continue;
            }

            // Check for links: [text](url)
            const linkMatch = remaining.match(/^\[([^\]]+)\]\(([^)]+)\)/);
            if (linkMatch) {
                result.push(
                    <a key={`${keyPrefix}-${partIndex}`} href={linkMatch[2]} className="text-primary underline hover:opacity-80" target="_blank" rel="noopener noreferrer">
                        {linkMatch[1]}
                    </a>
                );
                remaining = remaining.slice(linkMatch[0].length);
                partIndex++;
                continue;
            }

            // Find the next special character or end of string
            const nextSpecial = remaining.search(/\*|_|`|\[/);
            if (nextSpecial === -1) {
                // No more special characters, add the rest as plain text
                result.push(<span key={`${keyPrefix}-${partIndex}`}>{remaining}</span>);
                break;
            } else if (nextSpecial === 0) {
                // Special character at start but didn't match above patterns, treat as literal
                result.push(<span key={`${keyPrefix}-${partIndex}`}>{remaining[0]}</span>);
                remaining = remaining.slice(1);
                partIndex++;
            } else {
                // Add text before the special character
                result.push(<span key={`${keyPrefix}-${partIndex}`}>{remaining.slice(0, nextSpecial)}</span>);
                remaining = remaining.slice(nextSpecial);
                partIndex++;
            }
        }

        return result;
    };

    // Render markdown content
    const renderMarkdown = (content: string) => {
        const lines = content.split('\n');
        const elements: React.ReactNode[] = [];

        lines.forEach((line, i) => {
            if (line.startsWith('# ')) {
                elements.push(<h1 key={i} className="text-2xl font-bold text-foreground mb-4">{parseInlineMarkdown(line.slice(2), `h1-${i}`)}</h1>);
            } else if (line.startsWith('## ')) {
                elements.push(<h2 key={i} className="text-xl font-semibold text-foreground mt-6 mb-3">{parseInlineMarkdown(line.slice(3), `h2-${i}`)}</h2>);
            } else if (line.startsWith('### ')) {
                elements.push(<h3 key={i} className="text-lg font-semibold text-foreground mt-4 mb-2">{parseInlineMarkdown(line.slice(4), `h3-${i}`)}</h3>);
            } else if (line.startsWith('#### ')) {
                elements.push(<h4 key={i} className="text-base font-semibold text-foreground mt-3 mb-2">{parseInlineMarkdown(line.slice(5), `h4-${i}`)}</h4>);
            } else if (line.startsWith('- ') || line.startsWith('* ')) {
                elements.push(
                    <li key={i} className="text-muted-foreground ml-4 flex items-start">
                        <span className="mr-2 text-primary">•</span>
                        <span>{parseInlineMarkdown(line.slice(2), `li-${i}`)}</span>
                    </li>
                );
            } else if (/^\d+\.\s/.test(line)) {
                const match = line.match(/^(\d+)\.\s(.*)$/);
                if (match) {
                    elements.push(
                        <li key={i} className="text-muted-foreground ml-4 flex items-start">
                            <span className="mr-2 text-primary min-w-[1.5rem]">{match[1]}.</span>
                            <span>{parseInlineMarkdown(match[2], `ol-${i}`)}</span>
                        </li>
                    );
                }
            } else if (line.startsWith('> ')) {
                elements.push(
                    <blockquote key={i} className="border-l-4 border-primary pl-4 py-1 italic text-muted-foreground my-2">
                        {parseInlineMarkdown(line.slice(2), `quote-${i}`)}
                    </blockquote>
                );
            } else if (line.startsWith('---') || line.startsWith('***')) {
                elements.push(<hr key={i} className="border-border my-4" />);
            } else if (line.trim() === '') {
                elements.push(<div key={i} className="h-2" />);
            } else {
                elements.push(<p key={i} className="text-muted-foreground leading-relaxed">{parseInlineMarkdown(line, `p-${i}`)}</p>);
            }
        });

        return elements;
    };

    const description = descriptiveResult?.description as string | undefined;

    return (
        <div className="space-y-4">
            {/* Tab Header */}
            <div className="flex border-b border-border">
                <button
                    onClick={() => setActiveTab('description')}
                    className={`px-6 py-3 text-sm font-medium transition-colors relative ${activeTab === 'description'
                        ? 'text-primary'
                        : 'text-muted-foreground hover:text-foreground'
                        }`}
                >
                    Description
                    {activeTab === 'description' && (
                        <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary" />
                    )}
                </button>
                <button
                    onClick={() => setActiveTab('json')}
                    className={`px-6 py-3 text-sm font-medium transition-colors relative ${activeTab === 'json'
                        ? 'text-primary'
                        : 'text-muted-foreground hover:text-foreground'
                        }`}
                >
                    JSON
                    {jsonLoading && (
                        <span className="ml-2 inline-block w-3 h-3 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                    )}
                    {activeTab === 'json' && (
                        <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary" />
                    )}
                </button>
            </div>

            {/* Tab Content */}
            <div className="min-h-[200px]">
                {activeTab === 'description' && (
                    <div className="bg-muted/30 rounded-xl p-6 border border-border">
                        {description ? (
                            <div className="prose prose-sm max-w-none">
                                {renderMarkdown(description)}
                            </div>
                        ) : (
                            <p className="text-muted-foreground">No description available.</p>
                        )}
                    </div>
                )}

                {activeTab === 'json' && (
                    <>
                        {jsonLoading && (
                            <div className="flex items-center justify-center py-12">
                                <div className="flex items-center gap-3 text-muted-foreground">
                                    <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                                    <span>Loading JSON data...</span>
                                </div>
                            </div>
                        )}

                        {jsonError && (
                            <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-500">
                                <p className="font-medium">Error loading JSON</p>
                                <p className="text-sm mt-1">{jsonError}</p>
                                <button
                                    onClick={loadJsonResult}
                                    className="mt-3 px-4 py-2 bg-red-500/20 rounded-lg text-sm hover:bg-red-500/30 transition-colors"
                                >
                                    Try Again
                                </button>
                            </div>
                        )}

                        {jsonResult && !jsonLoading && (
                            <JsonViewer data={jsonResult} title="Analysis Result" />
                        )}

                        {!jsonResult && !jsonLoading && !jsonError && (
                            <div className="flex items-center justify-center py-12">
                                <p className="text-muted-foreground">Click the JSON tab to load structured data.</p>
                            </div>
                        )}
                    </>
                )}
            </div>
        </div>
    );
}
