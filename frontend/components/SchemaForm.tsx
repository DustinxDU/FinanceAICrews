/**
 * Schema-Driven Form Component
 * 
 * Dynamically renders form fields based on input_schema (JSON Schema) returned from backend
 * Supports text, number, select types, default values, and required validation
 */

import React, { useState, useEffect } from 'react';
import { Search, ChevronDown } from 'lucide-react';
import { AssetPicker } from './AssetPicker';
import { TimeframePicker, TimeframeValue } from './TimeframePicker';

export interface SchemaProperty {
  type: string;
  title?: string;
  description?: string;
  enum?: string[];
  default?: any;
}

export interface InputSchema {
  type: 'object';
  properties: Record<string, SchemaProperty>;
  required?: string[];
}

interface SchemaFormProps {
  schema: InputSchema | null;
  values: Record<string, any>;
  onChange: (values: Record<string, any>) => void;
  disabled?: boolean;
}

interface FormFieldProps {
  name: string;
  property: SchemaProperty;
  value: any;
  onChange: (value: any) => void;
  required: boolean;
  disabled?: boolean;
}

// Helper to detect field type based on name and property
function detectSpecialFieldType(name: string, property: SchemaProperty): 'ticker' | 'timeframe' | null {
  const lowerName = name.toLowerCase();
  const lowerTitle = (property.title || '').toLowerCase();
  const lowerDesc = (property.description || '').toLowerCase();

  // Detect ticker/symbol/asset fields
  if (
    lowerName.includes('ticker') ||
    lowerName.includes('symbol') ||
    lowerName === 'asset' ||
    lowerTitle.includes('ticker') ||
    lowerTitle.includes('symbol') ||
    lowerDesc.includes('stock ticker') ||
    lowerDesc.includes('ticker symbol')
  ) {
    return 'ticker';
  }

  // Detect timeframe/period fields
  if (
    lowerName.includes('timeframe') ||
    lowerName.includes('period') ||
    lowerName === 'range' ||
    lowerTitle.includes('timeframe') ||
    lowerTitle.includes('period') ||
    lowerDesc.includes('time period') ||
    lowerDesc.includes('date range')
  ) {
    return 'timeframe';
  }

  return null;
}

function FormField({ name, property, value, onChange, required, disabled }: FormFieldProps) {
  const label = property.title || name;
  const placeholder = property.description || `Enter ${label.toLowerCase()}`;

  // Detect special field types
  const specialType = property.type === 'string' && !property.enum ? detectSpecialFieldType(name, property) : null;

  // Asset Picker for ticker/symbol fields
  if (specialType === 'ticker') {
    return (
      <div className="mb-4">
        <label className="block text-sm font-medium mb-1">
          {label}
          {required && <span className="text-red-400 ml-1">*</span>}
        </label>
        <AssetPicker
          value={value || ''}
          onSelect={(ticker) => onChange(ticker)}
          placeholder={placeholder}
        />
        {property.description && (
          <p className="text-xs text-[var(--text-secondary)] mt-1">{property.description}</p>
        )}
      </div>
    );
  }

  // Timeframe Picker for timeframe/period fields
  if (specialType === 'timeframe') {
    const timeframeValue: TimeframeValue = typeof value === 'object' && value?.type
      ? value
      : { type: 'preset', value: value || '1mo' };

    return (
      <div className="mb-4">
        <label className="block text-sm font-medium mb-1">
          {label}
          {required && <span className="text-red-400 ml-1">*</span>}
        </label>
        <TimeframePicker
          value={timeframeValue}
          onChange={(tf) => {
            // Pass the value string for simple backend compatibility
            onChange(tf.value);
          }}
        />
        {property.description && (
          <p className="text-xs text-[var(--text-secondary)] mt-1">{property.description}</p>
        )}
      </div>
    );
  }

  // Regular Text Input
  if (property.type === 'string' && !property.enum) {
    return (
      <div className="mb-4">
        <label className="block text-sm font-medium mb-1">
          {label}
          {required && <span className="text-red-400 ml-1">*</span>}
        </label>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-secondary)]" />
          <input
            type="text"
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            disabled={disabled}
            className="w-full bg-[var(--bg-app)] border border-[var(--border-color)] rounded-lg pl-8 pr-3 py-2 text-sm font-mono focus:border-[var(--accent-green)] outline-none disabled:opacity-50"
            placeholder={placeholder}
          />
        </div>
        {property.description && (
          <p className="text-xs text-[var(--text-secondary)] mt-1">{property.description}</p>
        )}
      </div>
    );
  }

  // Number Input
  if (property.type === 'number') {
    return (
      <div className="mb-4">
        <label className="block text-sm font-medium mb-1">
          {label}
          {required && <span className="text-red-400 ml-1">*</span>}
        </label>
        <input
          type="number"
          value={value || ''}
          onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
          disabled={disabled}
          className="w-full bg-[var(--bg-app)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-sm focus:border-[var(--accent-green)] outline-none disabled:opacity-50"
          placeholder={placeholder}
        />
        {property.description && (
          <p className="text-xs text-[var(--text-secondary)] mt-1">{property.description}</p>
        )}
      </div>
    );
  }

  // Select Dropdown
  if (property.type === 'string' && property.enum) {
    const [isOpen, setIsOpen] = useState(false);
    const selectedOption = property.enum.find(opt => opt === value) || property.enum[0];

    return (
      <div className="mb-4">
        <label className="block text-sm font-medium mb-1">
          {label}
          {required && <span className="text-red-400 ml-1">*</span>}
        </label>
        <div className="relative">
          <button
            type="button"
            onClick={() => !disabled && setIsOpen(!isOpen)}
            disabled={disabled}
            className="w-full bg-[var(--bg-app)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-sm text-left focus:border-[var(--accent-green)] outline-none disabled:opacity-50 flex items-center justify-between"
          >
            <span>{selectedOption || placeholder}</span>
            <ChevronDown className="w-4 h-4 text-[var(--text-secondary)]" />
          </button>
          
          {isOpen && !disabled && (
            <div className="absolute top-full left-0 right-0 mt-1 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg shadow-xl z-50 max-h-48 overflow-y-auto">
              {property.enum.map((option) => (
                <button
                  key={option}
                  type="button"
                  onClick={() => {
                    onChange(option);
                    setIsOpen(false);
                  }}
                  className={`w-full text-left px-3 py-2 text-sm hover:bg-[var(--bg-panel)] transition-colors ${
                    option === value ? 'bg-[var(--bg-panel)] text-[var(--accent-green)]' : ''
                  }`}
                >
                  {option}
                </button>
              ))}
            </div>
          )}
        </div>
        {property.description && (
          <p className="text-xs text-[var(--text-secondary)] mt-1">{property.description}</p>
        )}
      </div>
    );
  }

  // Fallback for unsupported types
  return (
    <div className="mb-4">
      <label className="block text-sm font-medium mb-1">
        {label}
        {required && <span className="text-red-400 ml-1">*</span>}
      </label>
      <input
        type="text"
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className="w-full bg-[var(--bg-app)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-sm focus:border-[var(--accent-green)] outline-none disabled:opacity-50"
        placeholder={`${property.type} field`}
      />
      <p className="text-xs text-yellow-400 mt-1">Unsupported field type: {property.type}</p>
    </div>
  );
}

export function SchemaForm({ schema, values, onChange, disabled }: SchemaFormProps) {
  // Initialize form values with defaults from schema
  useEffect(() => {
    if (!schema) return;

    const defaultValues: Record<string, any> = {};
    let hasDefaults = false;

    Object.entries(schema.properties).forEach(([name, property]) => {
      if (property.default !== undefined) {
        defaultValues[name] = property.default;
        hasDefaults = true;
      }
    });

    if (hasDefaults) {
      onChange({ ...defaultValues, ...values });
    }
  }, [schema]);

  if (!schema || !schema.properties) {
    return (
      <div className="text-center text-[var(--text-secondary)] py-4">
        <p className="text-sm">No input schema available</p>
        <p className="text-xs mt-1">This crew doesn't require additional parameters</p>
      </div>
    );
  }

  const requiredFields = schema.required || [];

  return (
    <div className="space-y-2">
      {Object.entries(schema.properties).map(([name, property]) => (
        <FormField
          key={name}
          name={name}
          property={property}
          value={values[name]}
          onChange={(value) => onChange({ ...values, [name]: value })}
          required={requiredFields.includes(name)}
          disabled={disabled}
        />
      ))}
    </div>
  );
}

export default SchemaForm;
