"use client";

import React, { useState, useEffect, useRef } from 'react';
import { Search, Loader2 } from 'lucide-react';
import apiClient from '@/lib/api';

interface AssetPickerProps {
  value?: string;
  onSelect: (ticker: string, assetInfo?: any) => void;
  placeholder?: string;
  className?: string;
}

export function AssetPicker({ value, onSelect, placeholder = "Search ticker...", className = "" }: AssetPickerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [activeTab, setActiveTab] = useState('All');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [displayValue, setDisplayValue] = useState(value || '');
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Close when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Update display value when prop changes
  useEffect(() => {
    if (value && value !== displayValue.split(' - ')[0]) {
      setDisplayValue(value);
    }
  }, [value, displayValue]);

  // Debounced search
  useEffect(() => {
    if (!isOpen) return;

    const timeoutId = setTimeout(async () => {
      if (query.trim().length >= 1) {
        await performSearch(query);
      } else {
        setSearchResults([]);
      }
    }, 300);

    return () => clearTimeout(timeoutId);
  }, [query, activeTab, isOpen]);

  const performSearch = async (searchQuery: string) => {
    try {
      setIsSearching(true);
      const assetTypes = activeTab === 'All' ? undefined : [activeTab];
      const results = await apiClient.searchAssets({
        query: searchQuery,
        asset_types: assetTypes,
        limit: 10
      });
      setSearchResults(results);
    } catch (error) {
      console.error('Search error:', error);
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  const handleSelect = (result: any) => {
    const newValue = result.ticker;
    const newDisplay = `${result.ticker} - ${result.name}`;
    setDisplayValue(newDisplay);
    onSelect(newValue, result);
    setIsOpen(false);
    setQuery('');
  };

  const tabs = ['All', 'US', 'CRYPTO', 'MACRO'];

  const suggestions = [
    { ticker: 'NVDA', name: 'NVIDIA Corp', asset_type: 'US' },
    { ticker: 'AAPL', name: 'Apple Inc', asset_type: 'US' },
    { ticker: 'BTC-USD', name: 'Bitcoin', asset_type: 'CRYPTO' },
    { ticker: 'SPX', name: 'S&P 500', asset_type: 'MACRO' }
  ];

  return (
    <div className={`relative ${className}`} ref={containerRef}>
      <div
        className="relative cursor-text"
        onClick={() => {
          setIsOpen(true);
          setTimeout(() => inputRef.current?.focus(), 0);
        }}
      >
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-secondary)]" />
        <input
          type="text"
          readOnly
          value={displayValue}
          className="w-full bg-[var(--bg-app)] border border-[var(--border-color)] rounded-lg pl-9 pr-3 py-2 text-sm font-mono focus:border-[var(--accent-green)] outline-none cursor-pointer hover:border-[var(--text-secondary)] transition-colors text-[var(--text-primary)]"
          placeholder={placeholder}
        />
      </div>

      {isOpen && (
        <div className="absolute top-full left-0 right-0 mt-2 bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-xl shadow-xl z-50 overflow-hidden animate-in zoom-in-95 duration-100">
          {/* Search Header */}
          <div className="p-3 border-b border-[var(--border-color)] bg-[var(--bg-card)]">
            <div className="flex items-center gap-2 mb-2">
              <Search className="w-4 h-4 text-[var(--text-secondary)]" />
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={e => setQuery(e.target.value)}
                placeholder="Type to search..."
                className="bg-transparent border-none outline-none text-sm w-full text-[var(--text-primary)] placeholder-[var(--text-secondary)]"
              />
            </div>
            <div className="flex gap-3 overflow-x-auto no-scrollbar">
              {tabs.map(tab => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`text-[10px] font-bold uppercase whitespace-nowrap transition-colors ${activeTab === tab ? 'text-[var(--accent-blue)]' : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'}`}
                >
                  {tab}
                </button>
              ))}
            </div>
          </div>

          {/* Results */}
          <div className="max-h-[300px] overflow-y-auto">
            {isSearching ? (
              <div className="flex items-center justify-center p-6 text-[var(--text-secondary)]">
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
                <span className="text-xs">Searching...</span>
              </div>
            ) : searchResults.length > 0 ? (
              <div className="p-1">
                {searchResults.map((res: any, i: number) => (
                  <button
                    key={i}
                    onClick={() => handleSelect(res)}
                    className="w-full flex items-center justify-between p-2 hover:bg-[var(--bg-card)] rounded-lg cursor-pointer group text-left transition-colors"
                  >
                    <div className="flex items-center gap-3 overflow-hidden">
                      <div className="w-8 h-8 rounded shrink-0 flex items-center justify-center text-xs font-bold bg-zinc-800 text-zinc-300">
                        {res.ticker.substring(0, 2)}
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-sm truncate">{res.ticker}</span>
                          <span className="text-[10px] bg-[var(--bg-app)] border border-[var(--border-color)] px-1 rounded text-[var(--text-secondary)] shrink-0">{res.asset_type}</span>
                        </div>
                        <div className="text-xs text-[var(--text-secondary)] truncate">{res.name}</div>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            ) : query ? (
              <div className="p-6 text-center text-xs text-[var(--text-secondary)]">
                No results found
              </div>
            ) : (
              <div className="p-4">
                 <div className="text-[10px] font-bold text-[var(--text-secondary)] uppercase mb-2">Suggestions</div>
                 <div className="space-y-1">
                   {suggestions.map(item => (
                     <button
                       key={item.ticker}
                       onClick={() => handleSelect(item)}
                       className="w-full flex items-center gap-3 p-2 hover:bg-[var(--bg-card)] rounded-lg text-left"
                     >
                       <span className="text-xs font-bold w-16">{item.ticker}</span>
                       <span className="text-xs text-[var(--text-secondary)] truncate">{item.name}</span>
                     </button>
                   ))}
                 </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
