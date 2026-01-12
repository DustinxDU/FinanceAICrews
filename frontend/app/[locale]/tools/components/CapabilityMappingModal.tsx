"use client";

import React, { useState, useEffect, useRef } from "react";
import { X, ArrowRight, Check, HelpCircle, Search } from "lucide-react";
import apiClient from "@/lib/api";
import { useTranslations } from "next-intl";

import { ALL_CAPABILITIES, CAPABILITY_METADATA } from "@/lib/taxonomy";

type ViewMode = "tool-first" | "capability-first";

interface CapabilityMappingModalProps {
  isOpen: boolean;
  onClose: () => void;
  providerId: number;
  providerKey: string;
  discoveredTools?: string[];
  existingMappings?: Record<string, string>;
  onSuccess: () => void;
}

export function CapabilityMappingModal({
  isOpen,
  onClose,
  providerId,
  providerKey,
  discoveredTools = [],
  existingMappings = {},
  onSuccess,
}: CapabilityMappingModalProps) {
  const t = useTranslations("tools");
  const [viewMode, setViewMode] = useState<ViewMode>("tool-first"); // Default: Tool-first
  const [mappings, setMappings] = useState<Record<string, string>>({});
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [fetchingTools, setFetchingTools] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tools, setTools] = useState<string[]>([]);
  const initialized = useRef(false);

  // Fetch tools and existing mappings when modal opens
  useEffect(() => {
    if (isOpen && providerId) {
      loadProviderData();
    }
  }, [isOpen, providerId]);

  // NOTE: mappings state uses { tool_name: capability_id } structure
  // This allows multiple tools to map to the same capability
  const loadProviderData = async () => {
    try {
      setFetchingTools(true);
      setError(null);

      const [providerResult, discoverResult] = await Promise.allSettled([
        apiClient.getProvider(providerId),
        apiClient.discoverProviderTools(providerId, { refresh: true }),
      ]);

      let nextError: string | null = null;

      let nextTools = discoveredTools;
      if (discoverResult.status === "fulfilled") {
        const discovered = discoverResult.value?.tools;
        if (Array.isArray(discovered)) {
          nextTools = discovered;
        }
        if (typeof discoverResult.value?.error === "string" && discoverResult.value.error) {
          nextError = discoverResult.value.error;
        }
      } else {
        nextError = discoverResult.reason?.message || "Failed to discover provider tools";
      }
      setTools(nextTools);

      // Convert existingMappings from { capability_id: tool_name } to { tool_name: capability_id }
      let nextMappings: Record<string, string> = {};
      for (const [capId, toolName] of Object.entries(existingMappings)) {
        if (capId && toolName) {
          nextMappings[String(toolName)] = String(capId);
        }
      }

      if (providerResult.status === "fulfilled") {
        const mappingsList = providerResult.value?.mappings;
        if (Array.isArray(mappingsList)) {
          // Build { tool_name: capability_id } from API response
          nextMappings = {};
          mappingsList.forEach((m: any) => {
            const capabilityId = m?.capability_id;
            const rawToolName = m?.raw_tool_name;
            if (capabilityId && rawToolName) {
              // Key is tool_name, value is capability_id
              nextMappings[String(rawToolName)] = String(capabilityId);
            }
          });
        }
      } else if (!nextError) {
        nextError = providerResult.reason?.message || "Failed to load provider mappings";
      }
      setMappings(nextMappings);
      setError(nextError);
    } catch (err: any) {
      console.error("Failed to load provider data:", err);
      setError(err.message || "Failed to load provider data");
    } finally {
      setFetchingTools(false);
    }
  };

  useEffect(() => {
    if (!isOpen) {
      initialized.current = false;
      setMappings({});
      setSearchQuery("");
      setError(null);
      setTools([]);
    }
  }, [isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      // Send mappings in { tool_name: capability_id } format (new format)
      // Backend auto-detects format and supports multiple tools per capability
      await apiClient.submitCapabilityMapping(providerId, mappings);
      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err.message || "Failed to submit mapping");
    } finally {
      setLoading(false);
    }
  };

  // Capability-first mode: handle capability → tool mapping
  // mappings structure: { tool_name: capability_id }
  const handleMappingChange = (capabilityId: string, toolName: string) => {
    setMappings((prev) => {
      const updated = { ...prev };

      // First, remove any existing tool mapped to this capability
      // (in capability-first mode, we want 1:1 mapping per capability)
      Object.keys(updated).forEach((tool) => {
        if (updated[tool] === capabilityId) {
          delete updated[tool];
        }
      });

      // Add new mapping if tool selected
      if (toolName !== "") {
        updated[toolName] = capabilityId;
      }

      return updated;
    });
  };

  // Tool-first mode: handle tool → capability mapping
  // mappings structure: { tool_name: capability_id }
  const handleToolMappingChange = (toolName: string, capabilityId: string) => {
    setMappings((prev) => {
      const updated = { ...prev };

      // Remove existing mapping for this tool
      delete updated[toolName];

      // Add new mapping if capability selected
      if (capabilityId !== "") {
        updated[toolName] = capabilityId;
      }

      return updated;
    });
  };

  // Find which capability a tool is currently mapped to
  // mappings structure: { tool_name: capability_id }
  const findMappedCapability = (toolName: string): string => {
    return mappings[toolName] || "";
  };

  // Find which tool is mapped to a capability (for capability-first view)
  // Returns the first tool found (capability-first mode shows 1:1)
  const findMappedTool = (capabilityId: string): string => {
    for (const [toolName, capId] of Object.entries(mappings)) {
      if (capId === capabilityId) {
        return toolName;
      }
    }
    return "";
  };

  // Auto-guess capability for a tool based on naming heuristics
  const autoGuessMapping = (toolName: string) => {
    const toolLower = toolName.toLowerCase();

    // Simple heuristic matching
    for (const capId of ALL_CAPABILITIES) {
      const capLower = capId.toLowerCase();

      // Check for direct substring matches
      if (toolLower.includes(capLower) || capLower.includes(toolLower)) {
        handleToolMappingChange(toolName, capId);
        return;
      }

      // Check metadata
      const meta = CAPABILITY_METADATA[capId] || {};
      const displayName = (meta.display_name || "").toLowerCase();
      if (displayName && (toolLower.includes(displayName) || displayName.includes(toolLower))) {
        handleToolMappingChange(toolName, capId);
        return;
      }
    }
  };

  const filteredCapabilities = ALL_CAPABILITIES.filter((cap) => {
    if (!searchQuery) return true;
    const meta = CAPABILITY_METADATA[cap] || {};
    const displayName = meta.display_name || cap;
    const description = meta.description || "";
    const query = searchQuery.toLowerCase();
    return (
      cap.toLowerCase().includes(query) ||
      displayName.toLowerCase().includes(query) ||
      description.toLowerCase().includes(query)
    );
  });

  const filteredTools = tools.filter((tool) => {
    if (!searchQuery) return true;
    return tool.toLowerCase().includes(searchQuery.toLowerCase());
  });

  const mappedCount = Object.keys(mappings).length;

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 animate-in fade-in duration-200">
      <div className="bg-[var(--bg-panel)] rounded-xl shadow-2xl max-w-3xl w-full mx-4 max-h-[90vh] flex flex-col overflow-hidden">
        <div className="flex items-center justify-between p-6 border-b border-[var(--border-color)]">
          <div>
            <h2 className="text-xl font-semibold text-[var(--text-primary)]">
              Map Capabilities
            </h2>
            <p className="text-sm text-[var(--text-secondary)] mt-1">
              Provider:{" "}
              <span className="font-mono text-[var(--accent-blue)]">{providerKey}</span>
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {fetchingTools ? (
          <div className="flex-1 flex items-center justify-center p-12">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[var(--accent-blue)] mx-auto mb-4"></div>
              <p className="text-sm text-[var(--text-secondary)]">{t('loadingProviderTools')}</p>
            </div>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto p-6 space-y-5">
          <div className="bg-blue-900/10 border border-blue-500/30 rounded-lg p-4">
            <div className="flex items-start gap-2.5">
              <HelpCircle className="w-4 h-4 text-blue-400 mt-0.5 flex-shrink-0" />
              <div className="text-xs text-blue-300/80">
                <p className="font-medium mb-1.5 text-blue-200">How to map:</p>
                <ul className="list-disc list-inside space-y-0.5">
                  {viewMode === "tool-first" ? (
                    <>
                      <li>{t('selectCapability')}</li>
                      <li>Use "Auto" button for smart suggestions</li>
                    </>
                  ) : (
                    <>
                      <li>Select which provider tools match each standard capability</li>
                      <li>Leave blank if the provider does not support that capability</li>
                    </>
                  )}
                  <li>Mapped capabilities = {mappedCount}</li>
                </ul>
              </div>
            </div>
          </div>

          {/* View Mode Toggle */}
          <div className="flex items-center gap-3">
            <span className="text-sm text-[var(--text-secondary)] font-medium">{t('view')}</span>
            <div className="flex rounded-lg border border-[var(--border-color)] overflow-hidden">
              <button
                onClick={() => setViewMode("tool-first")}
                className={`px-4 py-2 text-sm font-medium transition-colors ${
                  viewMode === "tool-first"
                    ? "bg-[var(--accent-blue)] text-white"
                    : "bg-[var(--bg-card)] text-[var(--text-secondary)] hover:bg-[var(--bg-panel)]"
                }`}
              >
                Tools → Capabilities
              </button>
              <button
                onClick={() => setViewMode("capability-first")}
                className={`px-4 py-2 text-sm font-medium transition-colors ${
                  viewMode === "capability-first"
                    ? "bg-[var(--accent-blue)] text-white"
                    : "bg-[var(--bg-card)] text-[var(--text-secondary)] hover:bg-[var(--bg-panel)]"
                }`}
              >
                Capabilities → Tools
              </button>
            </div>
          </div>

          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-secondary)]" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={viewMode === "tool-first" ? "Search tools..." : "Search capabilities..."}
              className="w-full pl-10 pr-4 py-2.5 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg text-[var(--text-primary)] placeholder-[var(--text-secondary)] focus:border-[var(--accent-blue)] outline-none transition-colors"
            />
          </div>

          {viewMode === "tool-first" ? (
            // Tool-first view: show all tools, select capability for each
            <div className="space-y-2">
              {filteredTools.map((toolName) => {
                const mappedCap = findMappedCapability(toolName);
                const capMeta: any = mappedCap ? CAPABILITY_METADATA[mappedCap] || {} : {};
                const displayName = capMeta.display_name || mappedCap || "";

                return (
                  <div
                    key={toolName}
                    className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg p-4"
                  >
                    <div className="flex items-center gap-3">
                      <code className="flex-1 text-sm font-mono text-[var(--text-primary)]">
                        {toolName}
                      </code>

                      <ArrowRight className="w-4 h-4 text-[var(--text-secondary)] flex-shrink-0" />

                      <div className="w-56 flex-shrink-0">
                        <select
                          value={mappedCap}
                          onChange={(e) => handleToolMappingChange(toolName, e.target.value)}
                          className="w-full px-3 py-2 text-sm bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-lg text-[var(--text-primary)] focus:border-[var(--accent-blue)] outline-none transition-colors"
                        >
                          <option value="">{t('notMapped')}</option>
                          {ALL_CAPABILITIES.map((cap) => {
                            const meta = CAPABILITY_METADATA[cap] || {};
                            const label = meta.display_name || cap;
                            return (
                              <option key={cap} value={cap}>
                                {label}
                              </option>
                            );
                          })}
                        </select>
                      </div>

                      <button
                        onClick={() => autoGuessMapping(toolName)}
                        className="px-3 py-1.5 text-xs font-medium text-[var(--accent-blue)] hover:bg-blue-500/10 rounded transition-colors"
                      >
                        Auto
                      </button>

                      {mappedCap && (
                        <Check className="w-4 h-4 text-green-400 flex-shrink-0" />
                      )}
                    </div>
                  </div>
                );
              })}

              {filteredTools.length === 0 && (
                <div className="text-center py-8">
                  <p className="text-sm text-[var(--text-secondary)]">
                    {searchQuery
                      ? `No tools found matching "${searchQuery}"`
                      : "No tools discovered from this provider"}
                  </p>
                </div>
              )}
            </div>
          ) : (
            // Capability-first view: existing implementation
            <div className="space-y-2">
              {filteredCapabilities.map((capId) => {
              const meta = CAPABILITY_METADATA[capId] || {};
              const displayName = meta.display_name || capId;
              const description = meta.description || "";
              // Use findMappedTool since mappings is { tool_name: capability_id }
              const currentMapping = findMappedTool(capId);

              return (
                <div
                  key={capId}
                  className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg p-4"
                >
                  <div className="flex items-start gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-medium text-[var(--text-primary)]">
                          {displayName}
                        </span>
                        <code className="text-xs px-1.5 py-0.5 bg-[var(--bg-panel)] rounded text-[var(--text-secondary)] font-mono">
                          {capId}
                        </code>
                      </div>
                      {description && (
                        <p className="text-xs text-[var(--text-secondary)] line-clamp-1">
                          {description}
                        </p>
                      )}
                    </div>

                    <ArrowRight className="w-4 h-4 text-[var(--text-secondary)] mt-1 flex-shrink-0" />

                    <div className="w-48 flex-shrink-0">
                      <select
                        value={currentMapping}
                        onChange={(e) => handleMappingChange(capId, e.target.value)}
                        className="w-full px-3 py-2 text-sm bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-lg text-[var(--text-primary)] focus:border-[var(--accent-blue)] outline-none transition-colors"
                      >
                        <option value="">{t('noMapping')}</option>
                        {tools.map((tool) => (
                          <option key={tool} value={tool}>
                            {tool}
                          </option>
                        ))}
                      </select>
                    </div>

                    {currentMapping && (
                      <Check className="w-4 h-4 text-green-400 mt-1 flex-shrink-0" />
                    )}
                  </div>
                </div>
              );
            })}

            {filteredCapabilities.length === 0 && (
              <div className="text-center py-8">
                <p className="text-sm text-[var(--text-secondary)]">
                  No capabilities found matching "{searchQuery}"
                </p>
              </div>
            )}
          </div>
          )}

          {error && (
            <div className="bg-red-900/10 border border-red-500/30 rounded-lg p-3">
              <p className="text-sm text-red-400">{error}</p>
            </div>
          )}
        </div>
        )}

        <div className="flex gap-3 p-6 border-t border-[var(--border-color)]">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 px-4 py-2.5 border border-[var(--border-color)] rounded-lg text-sm font-medium text-[var(--text-secondary)] bg-[var(--bg-card)] hover:bg-[var(--bg-panel)] transition-colors"
          >
            {t('cancel')}
          </button>
          <button
            onClick={handleSubmit}
            disabled={loading || mappedCount === 0}
            className="flex-1 px-4 py-2.5 border border-transparent rounded-lg text-sm font-medium text-white bg-[var(--accent-blue)] hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? "Saving..." : `Save Mappings (${mappedCount})`}
          </button>
        </div>
      </div>
    </div>
  );
}
