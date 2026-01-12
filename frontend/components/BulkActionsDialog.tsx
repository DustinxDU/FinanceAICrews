import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Loader2,
  CheckCircle,
  AlertTriangle,
  Info,
  MoreVertical,
  Power,
  PowerOff,
  Trash2,
  Download,
  Upload,
  Archive,
  RefreshCw,
  Copy,
  Settings,
  Globe,
  Flag,
  X,
  Eye,
  EyeOff,
  Star,
} from "lucide-react";
import { LLMConfig, LLMProviderInfo } from "@/lib/api";

interface BulkAction {
  id: string;
  name: string;
  description: string;
  icon: React.ComponentType<any>;
  variant: "default" | "destructive" | "outline";
  requiresConfirmation: boolean;
  requiresInput?: boolean;
  inputPlaceholder?: string;
  warning?: string;
}

interface BulkActionsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  configs: LLMConfig[];
  providers: LLMProviderInfo[];
  onAction: (action: string, configIds: string[], inputValue?: string) => Promise<void>;
  isProcessing?: boolean;
}

export default function BulkActionsDialog({
  open,
  onOpenChange,
  configs,
  providers,
  onAction,
  isProcessing = false,
}: BulkActionsDialogProps) {
  const [selectedAction, setSelectedAction] = useState<string>("");
  const [confirmationInput, setConfirmationInput] = useState("");
  const [isExecuting, setIsExecuting] = useState(false);

  // Define bulk actions
  const bulkActions: BulkAction[] = [
    {
      id: "activate",
      name: "Activate Config",
      description: "Set selected configurations to active status",
      icon: Power,
      variant: "default",
      requiresConfirmation: false,
    },
    {
      id: "deactivate",
      name: "Deactivate Config",
      description: "Set selected configurations to inactive status",
      icon: PowerOff,
      variant: "outline",
      requiresConfirmation: false,
    },
    {
      id: "export",
      name: "Export Config",
      description: "Export details of selected configurations as JSON",
      icon: Download,
      variant: "outline",
      requiresConfirmation: false,
    },
    {
      id: "copy",
      name: "Copy Config",
      description: "Create copies of selected configurations",
      icon: Copy,
      variant: "outline",
      requiresConfirmation: false,
    },
    {
      id: "archive",
      name: "Archive Config",
      description: "Mark configurations as archived",
      icon: Archive,
      variant: "outline",
      requiresConfirmation: true,
      warning: "Archived configurations will not be deleted but marked as history",
    },
    {
      id: "validate",
      name: "Revalidate",
      description: "Revalidate API key validity for selected configurations",
      icon: RefreshCw,
      variant: "outline",
      requiresConfirmation: false,
    },
    {
      id: "delete",
      name: "Delete Config",
      description: "Permanently delete selected configurations",
      icon: Trash2,
      variant: "destructive",
      requiresConfirmation: true,
      requiresInput: true,
      inputPlaceholder: "Type 'delete' to confirm",
      warning: "This action is irreversible, configurations will be permanently deleted",
    },
  ];

  const selectedActionInfo = bulkActions.find(action => action.id === selectedAction);
  const configIds = configs.map(config => config.id);

  // Get risk assessment
  const getRiskAssessment = () => {
    const hasActiveConfigs = configs.some(config => config.is_active);
    const hasEnvConfigs = configs.some(config => config.is_from_env);
    const hasValidatedConfigs = configs.some(config => config.is_validated);
    const hasUniqueProviders = new Set(configs.map(config => config.provider)).size > 1;

    if (selectedAction === "delete") {
      return {
        level: "high",
        color: "red",
        message: "High Risk: Permanently delete configurations",
        icon: AlertTriangle,
      };
    }

    if (selectedAction === "archive" && hasActiveConfigs) {
      return {
        level: "medium",
        color: "yellow",
        message: "May affect usage of active configurations",
        icon: Info,
      };
    }

    if (hasActiveConfigs && ["deactivate", "delete"].includes(selectedAction)) {
      return {
        level: "medium",
        color: "yellow",
        message: "Contains active configurations, proceed with caution",
        icon: AlertTriangle,
      };
    }

    return {
      level: "low",
      color: "green",
      message: "Safe operation",
      icon: CheckCircle,
    };
  };

  const riskAssessment = getRiskAssessment();

  // Execute action
  const executeAction = async () => {
    if (!selectedAction) return;

    setIsExecuting(true);
    try {
      let inputValue = "";
      if (selectedActionInfo?.requiresInput) {
        inputValue = confirmationInput;
      }

      await onAction(selectedAction, configIds, inputValue);
      
      // Reset status
      setSelectedAction("");
      setConfirmationInput("");
      onOpenChange(false);
    } catch (error) {
      console.error("Bulk action failed:", error);
    } finally {
      setIsExecuting(false);
    }
  };

  const handleClose = () => {
    setSelectedAction("");
    setConfirmationInput("");
    onOpenChange(false);
  };

  // Stats information
  const stats = {
    total: configs.length,
    active: configs.filter(config => config.is_active).length,
    fromEnv: configs.filter(config => config.is_from_env).length,
    validated: configs.filter(config => config.is_validated).length,
    providers: new Set(configs.map(config => config.provider)).size,
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <MoreVertical className="h-5 w-5" />
            Bulk Actions
          </DialogTitle>
          <DialogDescription>
            Perform bulk actions on {configs.length} LLM configurations
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Configuration Overview */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Settings className="h-4 w-4" />
                Configuration Overview
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                <div>
                  <span className="text-muted-foreground">Total:</span>
                  <p className="font-medium">{stats.total}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">Active:</span>
                  <p className="font-medium text-green-600">{stats.active}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">From Env:</span>
                  <p className="font-medium text-blue-600">{stats.fromEnv}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">Validated:</span>
                  <p className="font-medium text-purple-600">{stats.validated}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">Providers:</span>
                  <p className="font-medium">{stats.providers}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Configuration List Preview */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Selected Configurations</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 max-h-40 overflow-y-auto">
              {configs.map((config) => {
                const providerInfo = providers.find(p => p.provider === config.provider);
                return (
                  <div 
                    key={config.id}
                    className="flex items-center justify-between p-2 border rounded"
                  >
                    <div className="flex items-center gap-2">
                      {providerInfo?.is_china_provider ? (
                        <Flag className="h-4 w-4 text-red-500" />
                      ) : (
                        <Globe className="h-4 w-4 text-blue-500" />
                      )}
                      <div>
                        <p className="font-medium text-sm">{config.display_name}</p>
                        <p className="text-xs text-muted-foreground">
                          {providerInfo?.display_name} • {config.provider}
                        </p>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-1">
                      {config.is_active && (
                        <Badge className="bg-green-100 text-green-800 text-xs">Active</Badge>
                      )}
                      {config.is_from_env && (
                        <Badge variant="outline" className="text-green-600 text-xs">Env</Badge>
                      )}
                    </div>
                  </div>
                );
              })}
            </CardContent>
          </Card>

          {/* Action Selection */}
          <div className="space-y-3">
            <Label>Select Action</Label>
            <div className="grid gap-2">
              {bulkActions.map((action) => {
                const Icon = action.icon;
                const isSelected = selectedAction === action.id;
                
                return (
                  <label
                    key={action.id}
                    className={`flex items-start gap-3 p-3 border rounded-lg cursor-pointer transition-colors ${
                      isSelected ? 'border-primary bg-primary/5' : 'hover:bg-muted/50'
                    }`}
                  >
                    <input
                      type="radio"
                      name="bulkAction"
                      value={action.id}
                      checked={isSelected}
                      onChange={(e) => setSelectedAction(e.target.value)}
                      className="mt-1"
                    />
                    <Icon className={`h-5 w-5 mt-0.5 ${
                      action.variant === "destructive" ? "text-red-500" :
                      action.variant === "outline" ? "text-muted-foreground" :
                      "text-primary"
                    }`} />
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{action.name}</span>
                        {action.requiresConfirmation && (
                          <Badge variant="outline" className="text-xs">Confirmation Required</Badge>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground">{action.description}</p>
                      {action.warning && (
                        <p className="text-xs text-yellow-600 mt-1 flex items-center gap-1">
                          <AlertTriangle className="h-3 w-3" />
                          {action.warning}
                        </p>
                      )}
                    </div>
                  </label>
                );
              })}
            </div>
          </div>

          {/* Risk Assessment */}
          {selectedAction && (
            <Alert className={`border-${riskAssessment.color}-200 bg-${riskAssessment.color}-50`}>
              <riskAssessment.icon className={`h-4 w-4 text-${riskAssessment.color}-600`} />
              <AlertDescription className={`text-${riskAssessment.color}-800`}>
                <strong>Risk Assessment:</strong> {riskAssessment.message}
              </AlertDescription>
            </Alert>
          )}

          {/* Confirmation Input */}
          {selectedActionInfo?.requiresInput && (
            <div className="space-y-2">
              <Label htmlFor="confirmation">
                Please enter confirmation text (must contain "{selectedAction === "delete" ? "delete" : "confirm"}")
              </Label>
              <Input
                id="confirmation"
                value={confirmationInput}
                onChange={(e) => setConfirmationInput(e.target.value)}
                placeholder={selectedActionInfo.inputPlaceholder}
                className={confirmationInput.toLowerCase().includes(selectedAction === "delete" ? "delete" : "confirm") ? "border-green-500" : ""}
              />
            </div>
          )}

          {/* Advanced Options */}
          {selectedAction && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">Action Options</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {selectedAction === "copy" && (
                  <div className="space-y-2">
                    <Label htmlFor="copyPrefix">Copy Name Prefix</Label>
                    <Input
                      id="copyPrefix"
                      placeholder="e.g., copy-"
                    />
                    <p className="text-xs text-muted-foreground">
                      New configurations will use this prefix
                    </p>
                  </div>
                )}

                {selectedAction === "export" && (
                  <div className="space-y-2">
                    <Label>Export Options</Label>
                    <div className="space-y-1">
                      <label className="flex items-center gap-2">
                        <input type="checkbox" defaultChecked />
                        <span className="text-sm">Include API Key (Encrypted)</span>
                      </label>
                      <label className="flex items-center gap-2">
                        <input type="checkbox" defaultChecked />
                        <span className="text-sm">Include Configuration Details</span>
                      </label>
                      <label className="flex items-center gap-2">
                        <input type="checkbox" />
                        <span className="text-sm">Include Usage Statistics</span>
                      </label>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>

        <DialogFooter className="flex justify-between">
          <div className="text-sm text-muted-foreground">
            {selectedAction && selectedActionInfo && (
              <span>Will execute: {selectedActionInfo.name}</span>
            )}
          </div>
          
          <div className="flex gap-2">
            <Button variant="outline" onClick={handleClose} disabled={isExecuting}>
              Cancel
            </Button>
            <Button 
              onClick={executeAction}
              disabled={!selectedAction || isExecuting || (selectedActionInfo?.requiresInput && !confirmationInput.toLowerCase().includes(selectedAction === "delete" ? "delete" : "confirm"))}
              variant={selectedActionInfo?.variant || "default"}
            >
              {isExecuting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Executing...
                </>
              ) : (
                <>
                  {selectedActionInfo?.icon && <selectedActionInfo.icon className="h-4 w-4 mr-2" />}
                  Execute Action
                </>
              )}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}