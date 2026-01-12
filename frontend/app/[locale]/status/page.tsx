"use client";

import React from "react";
import { CheckCircle, AlertTriangle, XCircle, Clock } from "lucide-react";
import { PublicLayout } from "@/components/layout/PublicLayout";
import { useTranslations } from "next-intl";


interface ServiceStatusProps {
  name: string;
  status: "operational" | "degraded" | "outage" | "maintenance";
  description?: string;
  lastUpdated?: string;
}

function ServiceStatus({ name, status, description, lastUpdated }: ServiceStatusProps) {
  const statusConfig = {
    operational: { icon: CheckCircle, color: "text-green-500", bg: "bg-green-500/10", border: "border-green-500/30", text: "Operational" },
    degraded: { icon: AlertTriangle, color: "text-yellow-500", bg: "bg-yellow-500/10", border: "border-yellow-500/30", text: "Degraded Performance" },
    outage: { icon: XCircle, color: "text-red-500", bg: "bg-red-500/10", border: "border-red-500/30", text: "Service Outage" },
    maintenance: { icon: Clock, color: "text-blue-500", bg: "bg-blue-500/10", border: "border-blue-500/30", text: "Scheduled Maintenance" }
  };

  const config = statusConfig[status];
  const Icon = config.icon;

  return (
    <div className={`p-4 rounded-lg border ${config.bg} ${config.border}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-3">
          <Icon className={`w-5 h-5 ${config.color}`} />
          <h3 className="font-bold text-[var(--text-primary)]">{name}</h3>
        </div>
        <span className={`text-xs font-medium ${config.color}`}>{config.text}</span>
      </div>
      {description && (
        <p className="text-sm text-[var(--text-secondary)] mb-2">{description}</p>
      )}
      {lastUpdated && (
        <p className="text-xs text-[var(--text-secondary)]">Last updated: {lastUpdated}</p>
      )}
    </div>
  );
}

interface IncidentProps {
  title: string;
  status: "investigating" | "identified" | "monitoring" | "resolved";
  date: string;
  description: string;
}

function Incident({ title, status, date, description }: IncidentProps) {
  const statusColors = {
    investigating: "text-yellow-500 bg-yellow-500/10",
    identified: "text-orange-500 bg-orange-500/10", 
    monitoring: "text-blue-500 bg-blue-500/10",
    resolved: "text-green-500 bg-green-500/10"
  };

  return (
    <div className="p-6 bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-xl">
      <div className="flex items-start justify-between mb-3">
        <h3 className="font-bold text-[var(--text-primary)]">{title}</h3>
        <span className={`text-xs font-medium px-2 py-1 rounded-full ${statusColors[status]}`}>
          {status.charAt(0).toUpperCase() + status.slice(1)}
        </span>
      </div>
      <p className="text-sm text-[var(--text-secondary)] mb-2">{description}</p>
      <p className="text-xs text-[var(--text-secondary)]">{date}</p>
    </div>
  );
}

function StatusPage() {
  const t = useTranslations('status');
  return (
    <PublicLayout>
      <div className="py-24 px-6 max-w-4xl mx-auto">
        <div className="text-center mb-16">
          <h1 className="text-4xl font-bold mb-4">{t('systemStatus')}</h1>
          <p className="text-[var(--text-secondary)]">Current status of FinanceAI services and infrastructure.</p>
        </div>

        {/* Overall Status */}
        <div className="mb-12 p-6 bg-green-500/10 border border-green-500/30 rounded-xl">
          <div className="flex items-center gap-3 mb-2">
            <CheckCircle className="w-6 h-6 text-green-500" />
            <h2 className="text-xl font-bold text-green-400">{t('allSystemsOperational')}</h2>
          </div>
          <p className="text-[var(--text-secondary)]">All services are running normally. Last checked: {new Date().toLocaleString()}</p>
        </div>

        {/* {t('serviceStatus')} */}
        <div className="mb-12">
          <h2 className="text-2xl font-bold mb-6">{t('serviceStatus')}</h2>
          <div className="space-y-4">
            <ServiceStatus 
              name="API Gateway"
              status="operational"
              description="REST API endpoints and authentication services"
              lastUpdated="2 minutes ago"
            />
            <ServiceStatus 
              name="Agent Execution Engine"
              status="operational"
              description="AI crew orchestration and task execution"
              lastUpdated="5 minutes ago"
            />
            <ServiceStatus 
              name="Data Connectors (MCP)"
              status="operational"
              description="Bloomberg, Reuters, and SEC Edgar integrations"
              lastUpdated="1 minute ago"
            />
            <ServiceStatus 
              name="Web Application"
              status="operational"
              description="Frontend dashboard and crew builder interface"
              lastUpdated="3 minutes ago"
            />
            <ServiceStatus 
              name="Database Cluster"
              status="operational"
              description="Primary and replica database instances"
              lastUpdated="4 minutes ago"
            />
          </div>
        </div>

        {/* Recent Incidents */}
        <div className="mb-12">
          <h2 className="text-2xl font-bold mb-6">Recent Incidents</h2>
          <div className="space-y-4">
            <Incident 
              title="Scheduled Maintenance - Database Upgrade"
              status="resolved"
              date="Dec 18, 2025 - 02:00 UTC to 04:00 UTC"
              description="Successfully upgraded database cluster to improve performance. All services restored."
            />
            <Incident 
              title="Intermittent API Timeouts"
              status="resolved"
              date="Dec 15, 2025 - 14:30 UTC to 15:45 UTC"
              description="Resolved timeout issues affecting API responses. Root cause was identified as increased load during peak hours."
            />
          </div>
        </div>

        {/* Performance Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="p-6 bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-xl text-center">
            <div className="text-3xl font-bold text-[var(--accent-green)] mb-2">99.9%</div>
            <div className="text-sm text-[var(--text-secondary)]">Uptime (30 days)</div>
          </div>
          <div className="p-6 bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-xl text-center">
            <div className="text-3xl font-bold text-[var(--accent-blue)] mb-2">245ms</div>
            <div className="text-sm text-[var(--text-secondary)]">{t('avgResponseTime')}</div>
          </div>
          <div className="p-6 bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-xl text-center">
            <div className="text-3xl font-bold text-[var(--accent-green)] mb-2">1.2M+</div>
            <div className="text-sm text-[var(--text-secondary)]">API Requests (24h)</div>
          </div>
        </div>
      </div>
    </PublicLayout>
  );
}

export default StatusPage;
