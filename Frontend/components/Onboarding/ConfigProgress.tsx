'use client'

/**
 * ConfigProgress — Visual progress indicator for onboarding fields.
 * Shows a pill for each configuration field that turns green when confirmed.
 * Includes an overall progress bar at the top.
 */

import React from 'react'
import { CheckCircle, Circle } from 'lucide-react'
import type { FieldStatus, StreamProgress } from '@/hooks/useOnboardingStream'

// Human-readable labels for each field
const FIELD_LABELS: Record<string, string> = {
  business_name: 'Nombre',
  business_type: 'Rubro',
  business_description: 'Descripción',
  target_audience: 'Público',
  services_offered: 'Servicios',
  business_hours: 'Horario',
  tone_of_voice: 'Tono',
  special_instructions: 'Reglas',
  greeting_message: 'Saludo',
  escalation_rules: 'Escalamiento',
}

const FIELD_ORDER = Object.keys(FIELD_LABELS)

interface ConfigProgressProps {
  fields: FieldStatus
  progress: StreamProgress
}

export default function ConfigProgress({ fields, progress }: ConfigProgressProps) {
  return (
    <div className="w-full space-y-3">
      {/* Overall progress bar */}
      <div className="flex items-center gap-3">
        <div className="flex-1 h-1.5 bg-slate-700/50 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-emerald-500 to-cyan-400 rounded-full transition-all duration-700 ease-out animate-progress"
            style={{ width: `${progress.percentage}%` }}
          />
        </div>
        <span className="text-xs font-mono text-slate-400 tabular-nums min-w-[3ch] text-right">
          {progress.fields_complete}/{progress.fields_total}
        </span>
      </div>

      {/* Field pills */}
      <div className="flex flex-wrap gap-1.5">
        {FIELD_ORDER.map((fieldName) => {
          const isComplete = fields[fieldName]?.complete ?? false
          return (
            <div
              key={fieldName}
              className={`
                inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium
                transition-all duration-300 border
                ${isComplete
                  ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30 animate-field-complete'
                  : 'bg-slate-800/50 text-slate-500 border-slate-700/50'
                }
              `}
            >
              {isComplete ? (
                <CheckCircle className="w-2.5 h-2.5" />
              ) : (
                <Circle className="w-2.5 h-2.5 opacity-40" />
              )}
              {FIELD_LABELS[fieldName]}
            </div>
          )
        })}
      </div>
    </div>
  )
}
