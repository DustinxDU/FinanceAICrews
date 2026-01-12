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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Search,
  Zap,
  Star,
  Clock,
  TrendingUp,
  Settings,
  Cpu,
  Brain,
  MessageSquare,
  FileText,
  Globe,
  Flag,
  Filter,
} from "lucide-react";
import { LLMProviderInfo, CreateLLMConfigRequest } from "@/lib/api";

interface ConfigTemplate {
  id: string;
  name: string;
  description: string;
  provider: string;
  config: Partial<CreateLLMConfigRequest>;
  tags: string[];
  category: string;
  usage_count?: number;
  rating?: number;
  is_featured?: boolean;
}

interface TemplateSelectorDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  templates: ConfigTemplate[];
  providers: LLMProviderInfo[];
  onApplyTemplate: (template: ConfigTemplate) => void;
}

export default function TemplateSelectorDialog({
  open,
  onOpenChange,
  templates,
  providers,
  onApplyTemplate,
}: TemplateSelectorDialogProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedProvider, setSelectedProvider] = useState("all");
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [selectedTemplate, setSelectedTemplate] = useState<ConfigTemplate | null>(null);

  // Category definitions
  const categories = [
    { id: "all", name: "All", icon: Settings },
    { id: "analysis", name: "Data Analysis", icon: TrendingUp },
    { id: "conversation", name: "Conversation", icon: MessageSquare },
    { id: "creative", name: "Creative Writing", icon: Brain },
    { id: "document", name: "Document Processing", icon: FileText },
    { id: "coding", name: "Code Generation", icon: Cpu },
  ];

  // Filter templates
  const filteredTemplates = templates.filter((template) => {
    // Search query filter
    const matchesSearch = 
      template.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      template.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      template.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()));
    
    // Category filter
    const matchesCategory = selectedCategory === "all" || template.category === selectedCategory;
    
    // Provider filter
    const matchesProvider = selectedProvider === "all" || template.provider === selectedProvider;

    return matchesSearch && matchesCategory && matchesProvider;
  });

  // Get provider display info
  const getProviderInfo = (providerId: string) => {
    return providers.find(p => p.provider === providerId);
  };

  // Get template rating stars
  const renderStars = (rating: number = 4) => {
    return (
      <div className="flex">
        {[...Array(5)].map((_, i) => (
          <Star
            key={i}
            className={`h-3 w-3 ${
              i < Math.floor(rating)
                ? "text-yellow-500 fill-current"
                : "text-gray-300"
            }`}
          />
        ))}
        <span className="ml-1 text-xs font-medium">{rating.toFixed(1)}</span>
      </div>
    );
  };

  const handleApplyTemplate = () => {
    if (selectedTemplate) {
      onApplyTemplate(selectedTemplate);
      onOpenChange(false);
      setSelectedTemplate(null);
      setSearchQuery("");
      setSelectedProvider("all");
      setSelectedCategory("all");
    }
  };

  const handleClose = () => {
    onOpenChange(false);
    setSelectedTemplate(null);
    setSearchQuery("");
    setSelectedProvider("all");
    setSelectedCategory("all");
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Zap className="h-5 w-5 text-yellow-500" />
            Select Configuration Template
          </DialogTitle>
          <DialogDescription>
            Choose a preset template to quickly create an LLM configuration, or customize based on an existing template
          </DialogDescription>
        </DialogHeader>

        {/* Search and Filter */}
        <div className="space-y-4">
          <div className="flex gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search template name, description, or tags..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>

          <div className="flex gap-4 overflow-x-auto">
            {/* Category Filter */}
            <div className="flex gap-2">
              {categories.map((category) => {
                const Icon = category.icon;
                return (
                  <Button
                    key={category.id}
                    variant={selectedCategory === category.id ? "default" : "outline"}
                    size="sm"
                    onClick={() => setSelectedCategory(category.id)}
                    className="whitespace-nowrap"
                  >
                    <Icon className="h-4 w-4 mr-1" />
                    {category.name}
                  </Button>
                );
              })}
            </div>

            {/* Provider Filter */}
            <div className="flex gap-2">
              <Button
                variant={selectedProvider === "all" ? "default" : "outline"}
                size="sm"
                onClick={() => setSelectedProvider("all")}
                className="whitespace-nowrap"
              >
                <Globe className="h-4 w-4 mr-1" />
                All Providers
              </Button>
              {providers.map((provider) => (
                <Button
                  key={provider.provider}
                  variant={selectedProvider === provider.provider ? "default" : "outline"}
                  size="sm"
                  onClick={() => setSelectedProvider(provider.provider)}
                  className="whitespace-nowrap"
                >
                  {provider.is_china_provider ? (
                    <Flag className="h-4 w-4 mr-1" />
                  ) : (
                    <Globe className="h-4 w-4 mr-1" />
                  )}
                  {provider.display_name}
                </Button>
              ))}
            </div>
          </div>
        </div>

        {/* Template List */}
        <div className="flex-1 overflow-y-auto">
          {filteredTemplates.length === 0 ? (
            <Card className="text-center py-12">
              <CardContent>
                <Zap className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-50" />
                <h3 className="text-lg font-medium mb-2">No matching templates found</h3>
                <p className="text-muted-foreground">
                  Try adjusting your search criteria or filter options
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4">
              {filteredTemplates.map((template) => {
                const providerInfo = getProviderInfo(template.provider);
                const isSelected = selectedTemplate?.id === template.id;
                
                return (
                  <Card
                    key={template.id}
                    className={`cursor-pointer transition-all hover:shadow-md ${
                      isSelected ? 'ring-2 ring-primary bg-primary/5' : ''
                    } ${template.is_featured ? 'border-yellow-200 bg-yellow-50/30' : ''}`}
                    onClick={() => setSelectedTemplate(template)}
                  >
                    <CardHeader className="pb-3">
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-2">
                          <div className="flex items-center gap-1">
                            {template.is_featured && (
                              <Star className="h-4 w-4 text-yellow-500 fill-current" />
                            )}
                            <CardTitle className="text-base">{template.name}</CardTitle>
                          </div>
                          <Badge variant="outline">
                            {providerInfo?.display_name || template.provider}
                          </Badge>
                        </div>
                        
                        <div className="flex items-center gap-1">
                          {renderStars(template.rating)}
                          <span className="text-xs text-muted-foreground ml-1">
                            ({template.usage_count || 0})
                          </span>
                        </div>
                      </div>
                      <CardDescription>{template.description}</CardDescription>
                    </CardHeader>
                    
                    <CardContent className="space-y-3">
                      {/* Tags */}
                      <div className="flex flex-wrap gap-1">
                        {template.tags.map((tag) => (
                          <Badge key={tag} variant="secondary" className="text-xs">
                            {tag}
                          </Badge>
                        ))}
                      </div>

                      {/* Config Preview */}
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div className="flex items-center justify-between">
                          <span className="text-muted-foreground">Temperature:</span>
                          <span className="font-medium">{template.config.temperature}</span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-muted-foreground">Max Tokens:</span>
                          <span className="font-medium">{template.config.max_tokens}</span>
                        </div>
                      </div>

                      {/* Usage Stats */}
                      <div className="flex items-center gap-4 text-xs text-muted-foreground">
                        <div className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          <span>Updated: 2 days ago</span>
                        </div>
                        {template.usage_count && (
                          <div className="flex items-center gap-1">
                            <TrendingUp className="h-3 w-3" />
                            <span>Usage: {template.usage_count}</span>
                          </div>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}
        </div>

        {/* Template Detail Preview */}
        {selectedTemplate && (
          <Card className="border-primary/20 bg-primary/5">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center gap-2">
                <Settings className="h-4 w-4" />
                Template Detail Preview
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <span className="text-muted-foreground">Provider:</span>
                  <p className="font-medium">{getProviderInfo(selectedTemplate.provider)?.display_name}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">Temperature:</span>
                  <p className="font-medium">{selectedTemplate.config.temperature}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">Max Tokens:</span>
                  <p className="font-medium">{selectedTemplate.config.max_tokens}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">Category:</span>
                  <p className="font-medium">{categories.find(c => c.id === selectedTemplate.category)?.name}</p>
                </div>
              </div>
              <div>
                <span className="text-muted-foreground">Tags:</span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {selectedTemplate.tags.map((tag) => (
                    <Badge key={tag} variant="outline" className="text-xs">
                      {tag}
                    </Badge>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        <DialogFooter className="flex justify-between">
          <div className="text-sm text-muted-foreground">
            Found {filteredTemplates.length} templates
            {searchQuery && (
              <span> • Search: "{searchQuery}"</span>
            )}
          </div>
          
          <div className="flex gap-2">
            <Button variant="outline" onClick={handleClose}>
              Cancel
            </Button>
            <Button 
              onClick={handleApplyTemplate}
              disabled={!selectedTemplate}
            >
              <Zap className="h-4 w-4 mr-2" />
              Apply Template
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}