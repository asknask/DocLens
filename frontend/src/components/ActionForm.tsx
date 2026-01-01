'use client';

import { useState } from 'react';
import { ActionType, getActionLabel, getActionDescription } from '@/lib/api';

interface ActionFormProps {
    onSubmit: (action: ActionType, options: Record<string, unknown>, refine: string) => void;
    isProcessing: boolean;
    disabled: boolean;
}

const ACTIONS: ActionType[] = ['summarize', 'extract_structured', 'classify', 'qa', 'transform'];

export default function ActionForm({ onSubmit, isProcessing, disabled }: ActionFormProps) {
    const [selectedAction, setSelectedAction] = useState<ActionType>('summarize');
    const [question, setQuestion] = useState('');
    const [refine, setRefine] = useState('');
    const [targetFormat, setTargetFormat] = useState('markdown');

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();

        const options: Record<string, unknown> = {};

        if (selectedAction === 'qa' && question) {
            options.question = question;
        }

        if (selectedAction === 'transform' && targetFormat) {
            options.target_format = targetFormat;
        }

        onSubmit(selectedAction, options, refine);
    };

    const canSubmit = !disabled && !isProcessing && (
        selectedAction !== 'qa' || question.trim().length > 0
    );

    return (
        <form onSubmit={handleSubmit} className="space-y-6">
            {/* Action Selection */}
            <div>
                <label className="block text-sm font-medium text-foreground mb-3">
                    Select Analysis Action
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
                    {ACTIONS.map((action) => (
                        <button
                            key={action}
                            type="button"
                            onClick={() => setSelectedAction(action)}
                            disabled={disabled}
                            className={`
                p-4 rounded-xl border-2 text-left transition-all duration-200
                ${selectedAction === action
                                    ? 'border-primary bg-primary/10'
                                    : 'border-border hover:border-border/80 bg-muted/50 hover:bg-muted'
                                }
                ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
              `}
                        >
                            <span className="block font-medium text-foreground text-sm">
                                {getActionLabel(action)}
                            </span>
                            <span className="block text-xs text-muted-foreground mt-1 line-clamp-2">
                                {getActionDescription(action)}
                            </span>
                        </button>
                    ))}
                </div>
            </div>

            {/* Conditional Fields */}
            {selectedAction === 'qa' && (
                <div>
                    <label htmlFor="question" className="block text-sm font-medium text-foreground mb-2">
                        Your Question <span className="text-red-500">*</span>
                    </label>
                    <input
                        id="question"
                        type="text"
                        value={question}
                        onChange={(e) => setQuestion(e.target.value)}
                        placeholder="What would you like to know about this document?"
                        disabled={disabled}
                        className="
              w-full px-4 py-3 rounded-xl bg-background border border-border
              text-foreground placeholder-muted-foreground focus:outline-none focus:border-primary
              transition-colors disabled:opacity-50
            "
                    />
                </div>
            )}

            {selectedAction === 'transform' && (
                <div>
                    <label htmlFor="format" className="block text-sm font-medium text-foreground mb-2">
                        Target Format
                    </label>
                    <select
                        id="format"
                        value={targetFormat}
                        onChange={(e) => setTargetFormat(e.target.value)}
                        disabled={disabled}
                        className="
              w-full px-4 py-3 rounded-xl bg-background border border-border
              text-foreground focus:outline-none focus:border-primary
              transition-colors disabled:opacity-50
            "
                    >
                        <option value="markdown">Markdown</option>
                        <option value="plain">Plain Text</option>
                        <option value="json">JSON</option>
                        <option value="html">HTML</option>
                        <option value="summary">Structured Summary</option>
                        <option value="outline">Outline</option>
                    </select>
                </div>
            )}

            {/* Refine Instructions */}
            <div>
                <label htmlFor="refine" className="block text-sm font-medium text-foreground mb-2">
                    Refinement Instructions <span className="text-muted-foreground">(optional)</span>
                </label>
                <textarea
                    id="refine"
                    value={refine}
                    onChange={(e) => setRefine(e.target.value)}
                    placeholder="E.g., 'Keep it brief', 'Focus on financial data', 'Respond in Spanish'..."
                    disabled={disabled}
                    rows={2}
                    maxLength={500}
                    className="
            w-full px-4 py-3 rounded-xl bg-background border border-border
            text-foreground placeholder-muted-foreground focus:outline-none focus:border-primary
            transition-colors disabled:opacity-50 resize-none
          "
                />
                <p className="text-xs text-muted-foreground mt-1">{refine.length}/500 characters</p>
            </div>

            {/* Submit Button */}
            <button
                type="submit"
                disabled={!canSubmit}
                className={`
          w-full py-4 px-6 rounded-xl font-semibold text-white text-lg
          transition-all duration-300 flex items-center justify-center gap-3
          ${canSubmit
                        ? 'bg-gradient-to-r from-violet-600 to-fuchsia-600 hover:from-violet-500 hover:to-fuchsia-500 shadow-lg hover:shadow-violet-500/25'
                        : 'bg-slate-700 cursor-not-allowed'
                    }
        `}
            >
                {isProcessing ? (
                    <>
                        <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                        </svg>
                        <span>Processing...</span>
                    </>
                ) : (
                    <>
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                        <span>Run Analysis</span>
                    </>
                )}
            </button>
        </form>
    );
}
