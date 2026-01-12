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
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Trash2,
  AlertTriangle,
  Info,
  Shield,
  X,
  Loader2,
  CheckCircle,
  AlertCircle,
  Globe,
  Flag,
} from "lucide-react";
import { LLMConfig, LLMProviderInfo } from "@/lib/api";

interface DeleteConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  configs: LLMConfig[];
  providers: LLMProviderInfo[];
  onConfirm: () => Promise<void>;
  isDeleting?: boolean;
}

export default function DeleteConfirmDialog({
  open,
  onOpenChange,
  configs,
  providers,
  onConfirm,
  isDeleting = false,
}: DeleteConfirmDialogProps) {
  const [confirmationText, setConfirmationText] = useState("");
  const [selectedAction, setSelectedAction] = useState<"soft" | "hard">("soft");
  const [includeActive, setIncludeActive] = useState(false);

  const isBatchDelete = configs.length > 1;
  const requiredConfirmationText = isBatchDelete ? "delete multiple configurations" : `delete "${configs[0]?.display_name}"`;

  // Check for critical configurations (e.g., currently in use)
  const hasActiveConfigs = configs.some(config => config.is_active);
  const hasEnvConfigs = configs.some(config => config.is_from_env);
  const hasValidatedConfigs = configs.some(config => config.is_validated);

  // Get risk level for configuration
  const getRiskLevel = () => {
    let riskScore = 0;
    if (hasActiveConfigs) riskScore += 3;
    if (hasEnvConfigs) riskScore += 2;
    if (hasValidatedConfigs) riskScore += 1;
    
    if (riskScore >= 4) return { level: "high", color: "red", text: "High Risk" };
    if (riskScore >= 2) return { level: "medium", color: "yellow", text: "Medium Risk" };
    return { level: "low", color: "green", text: "Low Risk" };
  };

  const riskLevel = getRiskLevel();
  const canConfirm = confirmationText.toLowerCase() === requiredConfirmationText.toLowerCase();

  const handleConfirm = async () => {
    if (!canConfirm) return;
    
    try {
      await onConfirm();
      setConfirmationText("");
      setSelectedAction("soft");
      setIncludeActive(false);
      onOpenChange(false);
    } catch (error) {
      console.error("Delete failed:", error);
    }
  };

  const handleCancel = () => {
    setConfirmationText("");
    setSelectedAction("soft");
    setIncludeActive(false);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-red-600">
            <Trash2 className="h-5 w-5" />
            Confirm Delete Configuration
          </DialogTitle>
          <DialogDescription>
            {isBatchDelete 
              ? `You are about to delete ${configs.length} LLM configurations. This action cannot be undone, please proceed with caution.`
              : "You are about to delete this LLM configuration. This action cannot be undone, please proceed with caution."
            }
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Risk Assessment */}
          <Alert className={`border-${riskLevel.color}-200 bg-${riskLevel.color}-50`}>
            <Shield className={`h-4 w-4 text-${riskLevel.color}-600`} />
            <AlertDescription className={`text-${riskLevel.color}-800`}>
              <div className="flex items-center justify-between">
                <span>Risk Level: <strong>{riskLevel.text}</strong></span>
                <Badge variant="outline" className={`border-${riskLevel.color}-300 text-${riskLevel.color}-700`}>
                  {riskLevel.text}
                </Badge>
              </div>
            </AlertDescription>
          </Alert>

          {/* Configuration List */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Info className="h-4 w-4" />
                Configurations to be Deleted
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {configs.map((config) => {
                const providerInfo = providers.find(p => p.provider === config.provider);
                return (
                  <div 
                    key={config.id}
                    className="flex items-center justify-between p-3 border rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      <div className="flex items-center gap-2">
                        {providerInfo?.is_china_provider ? (
                          <Flag className="h-4 w-4 text-red-500" />
                        ) : (
                          <Globe className="h-4 w-4 text-blue-500" />
                        )}
                        <div>
                          <p className="font-medium">{config.display_name}</p>
                          <p className="text-sm text-muted-foreground">
                            {providerInfo?.display_name} • {config.provider}
                          </p>
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-2">
                      {config.is_active && (
                        <Badge className="bg-green-100 text-green-800">Active</Badge>
                      )}
                      {config.is_from_env && (
                        <Badge variant="outline" className="text-green-600 border-green-300">
                          Environment
                        </Badge>
                      )}
                      {config.is_validated && (
                        <Badge variant="outline" className="text-blue-600 border-blue-300">
                          Validated
                        </Badge>
                      )}
                    </div>
                  </div>
                );
              })}
            </CardContent>
          </Card>

          {/* Warnings */}
          {hasActiveConfigs && (
            <Alert className="border-yellow-200 bg-yellow-50">
              <AlertTriangle className="h-4 w-4 text-yellow-600" />
              <AlertDescription className="text-yellow-800">
                <strong>Warning:</strong> Includes active configurations. Deletion may affect features currently using these configurations.
              </AlertDescription>
            </Alert>
          )}

          {hasEnvConfigs && (
            <Alert className="border-blue-200 bg-blue-50">
              <Info className="h-4 w-4 text-blue-600" />
              <AlertDescription className="text-blue-800">
                <strong>Note:</strong> Includes configurations read from environment variables. After deletion, the system will re-read the configuration from environment variables.
              </AlertDescription>
            </Alert>
          )}

          {/* Delete Type Selection */}
          <div className="space-y-3">
            <Label>Deletion Type</Label>
            <div className="grid gap-2">
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="radio"
                  name="deleteType"
                  value="soft"
                  checked={selectedAction === "soft"}
                  onChange={(e) => setSelectedAction(e.target.value as "soft" | "hard")}
                  className="text-primary"
                />
                <div>
                  <span className="font-medium">Soft Delete (Recommended)</span>
                  <p className="text-sm text-muted-foreground">
                    Mark configuration as deleted but keep in system for auditing
                  </p>
                </div>
              </label>
              
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="radio"
                  name="deleteType"
                  value="hard"
                  checked={selectedAction === "hard"}
                  onChange={(e) => setSelectedAction(e.target.value as "soft" | "hard")}
                  className="text-primary"
                />
                <div>
                  <span className="font-medium text-red-600">Hard Delete</span>
                  <p className="text-sm text-muted-foreground">
                    Completely remove configuration from database, this action cannot be undone
                  </p>
                </div>
              </label>
            </div>
          </div>

          {/* Confirmation Input */}
          <div className="space-y-2">
            <Label htmlFor="confirmation">
              Please enter "{requiredConfirmationText}" to confirm deletion:
            </Label>
            <Input
              id="confirmation"
              value={confirmationText}
              onChange={(e) => setConfirmationText(e.target.value)}
              placeholder={requiredConfirmationText}
              className={confirmationText.toLowerCase() === requiredConfirmationText.toLowerCase() ? "border-green-500" : ""}
            />
          </div>
        </div>

        <DialogFooter className="flex justify-between">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            {riskLevel.level === "high" && (
              <>
                <AlertTriangle className="h-4 w-4 text-red-500" />
                <span>High risk operation, backup recommended</span>
              </>
            )}
            {riskLevel.level === "medium" && (
              <>
                <Info className="h-4 w-4 text-yellow-500" />
                <span>Ensure these configs are no longer needed</span>
              </>
            )}
            {riskLevel.level === "low" && (
              <>
                <CheckCircle className="h-4 w-4 text-green-500" />
                <span>Safe to delete</span>
              </>
            )}
          </div>
          
          <div className="flex gap-2">
            <Button variant="outline" onClick={handleCancel} disabled={isDeleting}>
              Cancel
            </Button>
            <Button 
              variant="destructive" 
              onClick={handleConfirm} 
              disabled={!canConfirm || isDeleting}
            >
              {isDeleting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Deleting...
                </>
              ) : (
                <>
                  <Trash2 className="h-4 w-4 mr-2" />
                  Confirm Delete
                </>
              )}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}