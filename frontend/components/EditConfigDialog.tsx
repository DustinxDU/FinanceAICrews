import { useState, useEffect, useCallback, useMemo, type ChangeEvent } from "react";
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
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Slider } from "@/components/ui/slider";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Loader2,
  Check,
  AlertCircle,
  Eye,
  EyeOff,
  Zap,
  Info,
  Globe,
  Flag,
  Settings,
  Key,
  Link,
  Brain,
  Thermometer,
  Type,
  Save,
  XCircle,
  CheckCircle2,
} from "lucide-react";
import { LLMProviderInfo, LLMConfig, CreateLLMConfigRequest } from "@/lib/api";
import { 
  validateField, 
  validateForm, 
  validateApiKeyFormat, 
  validateConfigNameUnique,
  FormValidator,
  ValidationState,
  createValidationState 
} from "@/lib/validation";

interface ConfigTemplate {
  id: string;
  name: string;
  description: string;
  provider: string;
  config: Partial<CreateLLMConfigRequest>;
  tags: string[];
  category?: string;
  usage_count?: number;
  rating?: number;
  is_featured?: boolean;
}

interface EditConfigDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  config: LLMConfig | null;
  providers: LLMProviderInfo[];
  formData: CreateLLMConfigRequest;
  setFormData: (data: CreateLLMConfigRequest) => void;
  validationStatus: {
    loading: boolean;
    valid?: boolean;
    message?: string;
  };
  setValidationStatus: (status: any) => void;
  onSubmit: () => Promise<void>;
  templates: ConfigTemplate[];
  onApplyTemplate: (template: ConfigTemplate) => void;
}

export default function EditConfigDialog({
  open,
  onOpenChange,
  config,
  providers,
  formData,
  setFormData,
  validationStatus,
  setValidationStatus,
  onSubmit,
  templates,
  onApplyTemplate,
}: EditConfigDialogProps) {
  const [localFormData, setLocalFormData] = useState<CreateLLMConfigRequest>(formData);
  const [showApiKey, setShowApiKey] = useState(false);
  const [showBaseUrl, setShowBaseUrl] = useState(false);
  const [activeTab, setActiveTab] = useState("basic");
  const [validator] = useState(() => new FormValidator());
  const [validationState, setValidationState] = useState<ValidationState>(createValidationState());
  const [isValidatingName, setIsValidatingName] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);

  // Sync external formData changes
  useEffect(() => {
    setLocalFormData(formData);
  }, [formData]);

  // Update form data when config changes
  useEffect(() => {
    if (config && open) {
      const configFormData: CreateLLMConfigRequest = {
        provider: config.provider,
        display_name: config.display_name,
        api_key: "", // Do not display original API key when editing
        base_url: config.base_url || "",
        custom_model_name: config.custom_model_name || "",
        endpoint_id: config.endpoint_id || "",
        default_model: config.default_model || "",
        temperature: config.temperature,
        max_tokens: config.max_tokens || 4000,
      };
      setLocalFormData(configFormData);
      setFormData(configFormData);
    }
  }, [config, open, setFormData]);

  // Reset validation state when dialog closes
  useEffect(() => {
    if (!open) {
      validator.clearErrors();
      setValidationState(createValidationState());
      setIsValidatingName(false);
    }
  }, [open, validator]);

  // Get current selected provider info
  const selectedProvider = useMemo(() => 
    providers.find(p => p.provider === localFormData.provider), 
    [providers, localFormData.provider]
  );

  // Real-time field validation
  const validateFieldRealTime = useCallback(async (fieldName: string, value: any) => {
    const error = validateField(fieldName, value, localFormData, selectedProvider);
    
    if (error) {
      validator.setErrors({ ...validationState.errors, [fieldName]: error });
    } else {
      const newErrors = { ...validationState.errors };
      delete newErrors[fieldName];
      validator.setErrors(newErrors);
    }
    
    setValidationState(validator.getState());

    // Config name uniqueness check (exclude current config)
    if (fieldName === 'display_name' && value && value.trim() && config?.display_name !== value.trim()) {
      setIsValidatingName(true);
      try {
        const uniqueError = await validateConfigNameUnique(value.trim(), config?.id);
        if (uniqueError) {
          const newErrors = { ...validationState.errors, display_name: uniqueError };
          validator.setErrors(newErrors);
          setValidationState(validator.getState());
        }
      } finally {
        setIsValidatingName(false);
      }
    }

    // API key format validation
    if (fieldName === 'api_key' && value && localFormData.provider) {
      const apiKeyError = validateApiKeyFormat(value, localFormData.provider);
      if (apiKeyError) {
        const newErrors = { ...validationState.errors, api_key: apiKeyError };
        validator.setErrors(newErrors);
        setValidationState(validator.getState());
      }
    }
  }, [localFormData, selectedProvider, validationState.errors, validator, config?.id, config?.display_name]);

  // Complete form validation
  const validateFormComplete = useCallback(() => {
    const result = validateForm(localFormData, selectedProvider);
    validator.setErrors(result.errors);
    setValidationState(validator.getState());
    return result.isValid;
  }, [localFormData, selectedProvider, validator]);

  // Apply template
  const applyTemplateToForm = (template: ConfigTemplate) => {
    setLocalFormData({
      ...localFormData,
      provider: template.provider,
      temperature: template.config.temperature || 0.7,
      max_tokens: template.config.max_tokens || 4000,
    });
    onApplyTemplate(template);
  };

  // Validate API Key
  const validateApiKey = async () => {
    if (!localFormData.api_key || !localFormData.provider) {
      setValidationStatus({ loading: false, message: "Please enter API Key and Provider first" });
      return;
    }

    setValidationStatus({ loading: true });
    
    try {
      // Should call actual validation API here
      // Simulating validation process temporarily
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // Simulating validation result
      const isValid = localFormData.api_key.length > 20;
      setValidationStatus({
        loading: false,
        valid: isValid,
        message: isValid ? "API Key validation successful" : "API Key validation failed",
      });
    } catch (error) {
      setValidationStatus({
        loading: false,
        valid: false,
        message: "API Key validation failed, please check if the key is correct",
      });
    }
  };

  // Handle field change
  const handleFieldChange = useCallback((fieldName: string, value: any) => {
    setLocalFormData(prev => ({ ...prev, [fieldName]: value }));
    // Trigger real-time validation
    validateFieldRealTime(fieldName, value);
  }, [validateFieldRealTime]);

  // Submit form
  const handleSubmit = async () => {
    if (!validateFormComplete()) {
      setActiveTab("basic");
      return;
    }

    setIsUpdating(true);
    try {
      await onSubmit();
      onOpenChange(false);
      setIsUpdating(false);
    } catch (error) {
      console.error("Update failed:", error);
      setIsUpdating(false);
    }
  };

  // Reset form
  const resetForm = useCallback(() => {
    if (config) {
      const configFormData: CreateLLMConfigRequest = {
        provider: config.provider,
        display_name: config.display_name,
        api_key: "",
        base_url: config.base_url || "",
        custom_model_name: config.custom_model_name || "",
        endpoint_id: config.endpoint_id || "",
        default_model: config.default_model || "",
        temperature: config.temperature,
        max_tokens: config.max_tokens || 4000,
      };
      setLocalFormData(configFormData);
      setFormData(configFormData);
    }
    validator.clearErrors();
    setValidationState(createValidationState());
    setValidationStatus({ loading: false });
  }, [config, validator, setFormData, setValidationStatus]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Edit LLM Configuration
          </DialogTitle>
          <DialogDescription>
            Modify your LLM configuration parameters to optimize user experience
          </DialogDescription>
        </DialogHeader>

        {/* Configuration Overview */}
        {config && (
          <Card className="bg-muted/50">
            <CardContent className="p-4">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="text-muted-foreground">Config ID:</span>
                  <p className="font-mono text-xs mt-1">{config.id}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">Provider:</span>
                  <p className="font-medium mt-1">{selectedProvider?.display_name}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">Status:</span>
                  <div className="mt-1">
                    {config.is_active ? (
                      <Badge className="bg-green-100 text-green-800">Active</Badge>
                    ) : (
                      <Badge variant="outline">Inactive</Badge>
                    )}
                  </div>
                </div>
                <div>
                  <span className="text-muted-foreground">Last Updated:</span>
                  <p className="text-xs mt-1">
                    {config.updated_at ? new Date(config.updated_at).toLocaleDateString() : "Unknown"}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="basic">Basic Configuration</TabsTrigger>
            <TabsTrigger value="advanced">Advanced Parameters</TabsTrigger>
            <TabsTrigger value="template">Quick Templates</TabsTrigger>
          </TabsList>

          <TabsContent value="basic" className="space-y-4 mt-4">
            <div className="grid gap-4 md:grid-cols-2">
              {/* Provider selection */}
              <div className="space-y-2">
                <Label htmlFor="provider">Provider *</Label>
                <Select
                  value={localFormData.provider}
                  onChange={(e: ChangeEvent<HTMLSelectElement>) => handleFieldChange('provider', e.target.value)}
                  options={providers.map(provider => ({
                    value: provider.provider,
                    label: provider.is_china_provider
                      ? `China ${provider.display_name}`
                      : provider.display_name,
                  }))}
                />
                {validationState.errors.provider && (
                  <p className="text-sm text-red-600 flex items-center gap-1">
                    <XCircle className="h-3 w-3" />
                    {validationState.errors.provider}
                  </p>
                )}
                {localFormData.provider && !validationState.errors.provider && (
                  <p className="text-sm text-green-600 flex items-center gap-1">
                    <CheckCircle2 className="h-3 w-3" />
                    Provider selected
                  </p>
                )}
              </div>

              {/* Config name */}
              <div className="space-y-2">
                <Label htmlFor="display_name">
                  Config Name * 
                  {isValidatingName && (
                    <span className="text-sm text-blue-500 ml-2">
                      <Loader2 className="h-3 w-3 inline animate-spin mr-1" />
                      Checking...
                    </span>
                  )}
                </Label>
                <div className="relative">
                  <Input
                    id="display_name"
                    value={localFormData.display_name}
                    onChange={(e) => handleFieldChange('display_name', e.target.value)}
                    placeholder="e.g., My GPT-4 Config"
                    className={
                      validationState.errors.display_name 
                        ? "border-red-300 focus:border-red-500" 
                        : localFormData.display_name && !validationState.errors.display_name
                        ? "border-green-300 focus:border-green-500"
                        : ""
                    }
                  />
                  {localFormData.display_name && !validationState.errors.display_name && !isValidatingName && (
                    <CheckCircle2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-green-500" />
                  )}
                  {validationState.errors.display_name && (
                    <XCircle className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-red-500" />
                  )}
                </div>
                {validationState.errors.display_name ? (
                  <p className="text-sm text-red-600 flex items-center gap-1">
                    <XCircle className="h-3 w-3" />
                    {validationState.errors.display_name}
                  </p>
                ) : localFormData.display_name && !isValidatingName ? (
                  <p className="text-sm text-green-600 flex items-center gap-1">
                    <CheckCircle2 className="h-3 w-3" />
                    Config name is valid
                  </p>
                ) : null}
              </div>
            </div>

            {/* API Key */}
            <div className="space-y-2">
              <Label htmlFor="api_key">
                API Key {config ? "(Leave empty to keep unchanged)" : "*"}
              </Label>
              <div className="relative">
                <Input
                  id="api_key"
                  type={showApiKey ? "text" : "password"}
                  value={localFormData.api_key}
                  onChange={(e) => handleFieldChange('api_key', e.target.value)}
                  placeholder={config ? "Leave empty to keep original API key" : "Enter your API key"}
                  className={
                    validationState.errors.api_key 
                      ? "border-red-300 focus:border-red-500 pr-10" 
                      : localFormData.api_key && !validationState.errors.api_key
                      ? "border-green-300 focus:border-green-500 pr-10"
                      : "pr-10"
                  }
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="absolute right-2 top-1/2 -translate-y-1/2 h-6 w-6"
                  onClick={() => setShowApiKey(!showApiKey)}
                >
                  {showApiKey ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </Button>
                {localFormData.api_key && !validationState.errors.api_key && (
                  <CheckCircle2 className="absolute right-10 top-1/2 -translate-y-1/2 h-4 w-4 text-green-500" />
                )}
                {validationState.errors.api_key && (
                  <XCircle className="absolute right-10 top-1/2 -translate-y-1/2 h-4 w-4 text-red-500" />
                )}
              </div>
              {validationState.errors.api_key ? (
                <p className="text-sm text-red-600 flex items-center gap-1">
                  <XCircle className="h-3 w-3" />
                  {validationState.errors.api_key}
                </p>
              ) : localFormData.api_key && !validationState.errors.api_key ? (
                <p className="text-sm text-green-600 flex items-center gap-1">
                  <CheckCircle2 className="h-3 w-3" />
                  API key format is correct
                </p>
              ) : (
                <p className="text-sm text-muted-foreground">
                  {config ? "Leave empty to keep original API key. New keys will be validated upon update." : 
                   localFormData.provider === 'openai' ? "OpenAI keys start with sk- and are 51 characters long." :
                   localFormData.provider === 'anthropic' ? "Anthropic keys start with sk-ant-." :
                   localFormData.provider === 'volcengine' ? "Volcengine API Key." :
                   "Enter your API key."}
                </p>
              )}
            </div>

            {/* Base URL (Dynamic Display) */}
            {selectedProvider?.requires_base_url && (
              <div className="space-y-2">
                <Label htmlFor="base_url">
                  Base URL * <span className="text-sm text-muted-foreground">(Required)</span>
                </Label>
                <div className="relative">
                  <Input
                    id="base_url"
                    value={localFormData.base_url}
                    onChange={(e) => handleFieldChange('base_url', e.target.value)}
                    placeholder={selectedProvider.default_base_url || "https://api.example.com"}
                    className={
                      validationState.errors.base_url 
                        ? "border-red-300 focus:border-red-500" 
                        : localFormData.base_url && !validationState.errors.base_url
                        ? "border-green-300 focus:border-green-500"
                        : ""
                    }
                  />
                  <Link className="absolute right-2 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  {localFormData.base_url && !validationState.errors.base_url && (
                    <CheckCircle2 className="absolute right-10 top-1/2 -translate-y-1/2 h-4 w-4 text-green-500" />
                  )}
                  {validationState.errors.base_url && (
                    <XCircle className="absolute right-10 top-1/2 -translate-y-1/2 h-4 w-4 text-red-500" />
                  )}
                </div>
                {validationState.errors.base_url ? (
                  <p className="text-sm text-red-600 flex items-center gap-1">
                    <XCircle className="h-3 w-3" />
                    {validationState.errors.base_url}
                  </p>
                ) : localFormData.base_url && !validationState.errors.base_url ? (
                  <p className="text-sm text-green-600 flex items-center gap-1">
                    <CheckCircle2 className="h-3 w-3" />
                    Base URL format is correct
                  </p>
                ) : null}
              </div>
            )}

            {/* Endpoint ID (Volcengine only) */}
            {selectedProvider?.requires_endpoint_id && (
              <div className="space-y-2">
                <Label htmlFor="endpoint_id">
                  Endpoint ID * <span className="text-sm text-muted-foreground">(Required for Volcengine)</span>
                </Label>
                <div className="relative">
                  <Input
                    id="endpoint_id"
                    value={localFormData.endpoint_id}
                    onChange={(e) => handleFieldChange('endpoint_id', e.target.value)}
                    placeholder="Enter your Endpoint ID"
                    className={
                      validationState.errors.endpoint_id 
                        ? "border-red-300 focus:border-red-500" 
                        : localFormData.endpoint_id && !validationState.errors.endpoint_id
                        ? "border-green-300 focus:border-green-500"
                        : ""
                    }
                  />
                  {localFormData.endpoint_id && !validationState.errors.endpoint_id && (
                    <CheckCircle2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-green-500" />
                  )}
                  {validationState.errors.endpoint_id && (
                    <XCircle className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-red-500" />
                  )}
                </div>
                {validationState.errors.endpoint_id ? (
                  <p className="text-sm text-red-600 flex items-center gap-1">
                    <XCircle className="h-3 w-3" />
                    {validationState.errors.endpoint_id}
                  </p>
                ) : localFormData.endpoint_id && !validationState.errors.endpoint_id ? (
                  <p className="text-sm text-green-600 flex items-center gap-1">
                    <CheckCircle2 className="h-3 w-3" />
                    Endpoint ID format is correct
                  </p>
                ) : null}
              </div>
            )}

            {/* Default Model */}
            <div className="space-y-2">
              <Label htmlFor="default_model">Default Model</Label>
              <Input
                id="default_model"
                value={localFormData.default_model}
                onChange={(e) => handleFieldChange('default_model', e.target.value)}
                placeholder="e.g., gpt-4, claude-3-sonnet"
              />
              {selectedProvider?.available_models && selectedProvider.available_models.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  <span className="text-sm text-muted-foreground mr-2">Popular Models:</span>
                  {selectedProvider.available_models.slice(0, 5).map((model) => (
                    <Badge
                      key={model.value}
                      variant="outline"
                      className="text-xs cursor-pointer hover:bg-primary/10"
                      onClick={() => handleFieldChange('default_model', model.value)}
                    >
                      {model.name}
                    </Badge>
                  ))}
                </div>
              )}
            </div>

            {/* Custom Model Name */}
            {selectedProvider?.requires_custom_model_name && (
              <div className="space-y-2">
                <Label htmlFor="custom_model_name">Custom Model Name *</Label>
                <div className="relative">
                  <Input
                    id="custom_model_name"
                    value={localFormData.custom_model_name}
                    onChange={(e) => handleFieldChange('custom_model_name', e.target.value)}
                    placeholder="Enter the model name you want to use"
                    className={
                      validationState.errors.custom_model_name 
                        ? "border-red-300 focus:border-red-500" 
                        : localFormData.custom_model_name && !validationState.errors.custom_model_name
                        ? "border-green-300 focus:border-green-500"
                        : ""
                    }
                  />
                  {localFormData.custom_model_name && !validationState.errors.custom_model_name && (
                    <CheckCircle2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-green-500" />
                  )}
                  {validationState.errors.custom_model_name && (
                    <XCircle className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-red-500" />
                  )}
                </div>
                {validationState.errors.custom_model_name ? (
                  <p className="text-sm text-red-600 flex items-center gap-1">
                    <XCircle className="h-3 w-3" />
                    {validationState.errors.custom_model_name}
                  </p>
                ) : localFormData.custom_model_name && !validationState.errors.custom_model_name ? (
                  <p className="text-sm text-green-600 flex items-center gap-1">
                    <CheckCircle2 className="h-3 w-3" />
                    Model name format is correct
                  </p>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    This provider requires a specific model name
                  </p>
                )}
              </div>
            )}

            {/* API Key Validation Status */}
            {validationStatus.message && (
              <Alert className={validationStatus.valid ? "border-green-200 bg-green-50" : "border-red-200 bg-red-50"}>
                <AlertCircle className={`h-4 w-4 ${validationStatus.valid ? "text-green-600" : "text-red-600"}`} />
                <AlertDescription className={validationStatus.valid ? "text-green-800" : "text-red-800"}>
                  {validationStatus.message}
                </AlertDescription>
              </Alert>
            )}

            {/* Validation Button */}
            <div className="flex justify-end">
              <Button
                variant="outline"
                size="sm"
                onClick={validateApiKey}
                disabled={validationStatus.loading || !localFormData.api_key || !localFormData.provider}
              >
                {validationStatus.loading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Validating...
                  </>
                ) : (
                  <>
                    <Check className="h-4 w-4 mr-2" />
                    Validate API Key
                  </>
                )}
              </Button>
            </div>
          </TabsContent>

          <TabsContent value="advanced" className="space-y-4 mt-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Thermometer className="h-5 w-5" />
                  Temperature
                </CardTitle>
                <CardDescription>
                  Controls randomness of output. Lower values make output more focused and deterministic, higher values make it more creative.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Current Value: {localFormData.temperature ?? 0.7}</span>
                  <Badge variant="outline">
                    {(localFormData.temperature ?? 0.7) < 0.3 ? "Conservative" : 
                     (localFormData.temperature ?? 0.7) > 1 ? "Creative" : "Balanced"}
                  </Badge>
                </div>
                <Slider
                  value={[localFormData.temperature ?? 0.7]}
                  onValueChange={([value]) => handleFieldChange('temperature', value)}
                  max={2}
                  min={0}
                  step={0.1}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>Deterministic (0)</span>
                  <span>Balanced (1)</span>
                  <span>Creative (2)</span>
                </div>
                {validationState.errors.temperature ? (
                  <p className="text-sm text-red-600 flex items-center gap-1">
                    <XCircle className="h-3 w-3" />
                    {validationState.errors.temperature}
                  </p>
                ) : localFormData.temperature !== undefined ? (
                  <p className="text-sm text-green-600 flex items-center gap-1">
                    <CheckCircle2 className="h-3 w-3" />
                    Temperature is valid ({localFormData.temperature})
                  </p>
                ) : null}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Type className="h-5 w-5" />
                  Max Tokens
                </CardTitle>
                <CardDescription>
                  Limits maximum length of generated text. Higher values allow longer responses but increase cost.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Current Value: {localFormData.max_tokens ?? 4000}</span>
                  <Badge variant="outline">
                    {(localFormData.max_tokens ?? 4000) <= 1000 ? "Short" :
                     (localFormData.max_tokens ?? 4000) <= 4000 ? "Medium" : "Detailed"}
                  </Badge>
                </div>
                <Input
                  type="number"
                  value={localFormData.max_tokens || 4000}
                  onChange={(e) => {
                    const value = parseInt(e.target.value) || 4000;
                    handleFieldChange('max_tokens', value);
                  }}
                  min={1}
                  max={32000}
                  placeholder="4000"
                  className={
                    validationState.errors.max_tokens 
                      ? "border-red-300 focus:border-red-500" 
                      : localFormData.max_tokens && !validationState.errors.max_tokens
                      ? "border-green-300 focus:border-green-500"
                      : ""
                  }
                />
                {validationState.errors.max_tokens ? (
                  <p className="text-sm text-red-600 flex items-center gap-1">
                    <XCircle className="h-3 w-3" />
                    {validationState.errors.max_tokens}
                  </p>
                ) : localFormData.max_tokens ? (
                  <p className="text-sm text-green-600 flex items-center gap-1">
                    <CheckCircle2 className="h-3 w-3" />
                    Max tokens is valid ({localFormData.max_tokens})
                  </p>
                ) : null}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="template" className="space-y-4 mt-4">
            <div className="grid gap-4">
              {templates.map((template) => (
                <Card
                  key={template.id}
                  className="cursor-pointer hover:shadow-md transition-shadow"
                  onClick={() => applyTemplateToForm(template)}
                >
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-base flex items-center gap-2">
                        <Zap className="h-4 w-4 text-yellow-500" />
                        {template.name}
                      </CardTitle>
                      <Badge variant="outline">
                        {providers.find(p => p.provider === template.provider)?.display_name}
                      </Badge>
                    </div>
                    <CardDescription>{template.description}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-1 mb-3">
                      {template.tags.map((tag) => (
                        <Badge key={tag} variant="secondary" className="text-xs">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-muted-foreground">Temperature:</span>
                        <span className="ml-1 font-medium">{template.config.temperature}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Max Tokens:</span>
                        <span className="ml-1 font-medium">{template.config.max_tokens}</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>
        </Tabs>

        <DialogFooter className="flex justify-between">
          <div className="flex gap-2">
            <Button variant="outline" onClick={resetForm}>
              Reset
            </Button>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button onClick={handleSubmit} disabled={isUpdating}>
              {isUpdating ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Updating...
                </>
              ) : (
                <>
                  <Save className="h-4 w-4 mr-2" />
                  Save Changes
                </>
              )}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}