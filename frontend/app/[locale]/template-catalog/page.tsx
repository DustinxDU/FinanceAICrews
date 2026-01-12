"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "@/i18n/routing";
import { useTranslations } from "next-intl";
import {
  Search,
  Filter,
  Download,
  Star,
  Users,
  Bot,
  ListTodo,
  Workflow,
  ChevronRight,
  Bell,
  Check,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ToastProvider, useToast } from "@/lib/toast";
import { useAuth } from "@/contexts/AuthContext";

interface Template {
  id: number;
  template_key: string;
  template_type: string;
  version: string;
  display_name: string;
  description: string | null;
  category: string;
  tags: string[] | null;
  icon: string | null;
  is_featured: boolean;
  import_count: number;
  published_at: string;
  payload?: Record<string, unknown>;
}

interface Category {
  category: string;
  count: number;
}

interface UpdateNotification {
  id: number;
  template_key: string;
  template_type: string;
  display_name: string;
  old_version: string;
  new_version: string;
  changelog: string | null;
  is_read: boolean;
  created_at: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

const typeIcons: Record<string, React.ReactNode> = {
  agent: <Bot className="h-5 w-5" />,
  task: <ListTodo className="h-5 w-5" />,
  crew: <Workflow className="h-5 w-5" />,
};

const categoryColors: Record<string, string> = {
  analysis: "bg-blue-100 text-blue-800",
  research: "bg-green-100 text-green-800",
  execution: "bg-orange-100 text-orange-800",
  regional: "bg-purple-100 text-purple-800",
  style: "bg-pink-100 text-pink-800",
  general: "bg-gray-100 text-gray-800",
  crew: "bg-indigo-100 text-indigo-800",
};

function TemplateCatalogPage() {
  const router = useRouter();
  const { toast } = useToast();
  const { token } = useAuth();
  const t = useTranslations('templateCatalog');

  const [templates, setTemplates] = useState<Template[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [notifications, setNotifications] = useState<UpdateNotification[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedType, setSelectedType] = useState<string>("all");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [importDialogOpen, setImportDialogOpen] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null);
  const [importing, setImporting] = useState(false);
  const [customName, setCustomName] = useState("");

  const fetchTemplates = async () => {
    try {
      const params = new URLSearchParams();
      if (selectedType !== "all") params.append("template_type", selectedType);
      if (selectedCategory !== "all") params.append("category", selectedCategory);
      if (searchQuery) params.append("search", searchQuery);

      const response = await fetch(`${API_BASE}/api/v1/templates?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        setTemplates(data);
      }
    } catch (error) {
      console.error("Failed to fetch templates:", error);
    }
  };

  const fetchCategories = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/v1/templates/categories`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        setCategories(data);
      }
    } catch (error) {
      console.error("Failed to fetch categories:", error);
    }
  };

  const fetchNotifications = async () => {
    try {
      const response = await fetch(
        `${API_BASE}/api/v1/templates/updates/notifications`,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      if (response.ok) {
        const data = await response.json();
        setNotifications(data);
      }
    } catch (error) {
      console.error("Failed to fetch notifications:", error);
    }
  };

  useEffect(() => {
    if (token) {
      Promise.all([fetchTemplates(), fetchCategories(), fetchNotifications()]).finally(
        () => setLoading(false)
      );
    }
  }, [token]);

  useEffect(() => {
    if (token) {
      fetchTemplates();
    }
  }, [selectedType, selectedCategory, searchQuery, token]);

  const handleImportClick = (template: Template) => {
    setSelectedTemplate(template);
    setCustomName(template.template_key);
    setImportDialogOpen(true);
  };

  const handleImport = async () => {
    if (!selectedTemplate) return;

    setImporting(true);
    try {
      const response = await fetch(
        `${API_BASE}/api/v1/templates/${selectedTemplate.id}/import`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ custom_name: customName }),
        }
      );

      if (response.ok) {
        const result = await response.json();
        toast({
          type: "success",
          title: t('importSuccess'),
          description: t('importedAs', { name: selectedTemplate.display_name, importedName: result.imported_resource_name }),
        });
        setImportDialogOpen(false);

        // 根据类型跳转到对应的编辑页面
        if (selectedTemplate.template_type === "crew") {
          router.push(`/crew-builder?id=${result.imported_resource_id}`);
        }
      } else {
        const error = await response.json();
        toast({
          type: "error",
          title: t('importFailed'),
          description: error.detail || t('importFailedDetail'),
        });
      }
    } catch (error) {
      toast({
        type: "error",
        title: t('importFailed'),
        description: t('networkError'),
      });
    } finally {
      setImporting(false);
    }
  };

  const renderTemplateCard = (template: Template) => (
    <Card
      key={template.id}
      className="hover:shadow-lg transition-shadow cursor-pointer group"
    >
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-muted">
              {typeIcons[template.template_type]}
            </div>
            <div>
              <CardTitle className="text-lg">{template.display_name}</CardTitle>
              <CardDescription className="text-xs">
                v{template.version} · {template.template_key}
              </CardDescription>
            </div>
          </div>
          {template.is_featured && (
            <Star className="h-4 w-4 text-yellow-500 fill-yellow-500" />
          )}
        </div>
      </CardHeader>

      <CardContent className="pb-3">
        <p className="text-sm text-muted-foreground line-clamp-2">
          {template.description || t('noDescription')}
        </p>

        <div className="flex flex-wrap gap-1 mt-3">
          <Badge
            variant="secondary"
            className={categoryColors[template.category] || categoryColors.general}
          >
            {template.category}
          </Badge>
          {template.tags?.slice(0, 2).map((tag) => (
            <Badge key={tag} variant="outline" className="text-xs">
              {tag}
            </Badge>
          ))}
        </div>
      </CardContent>

      <CardFooter className="pt-0 flex justify-between items-center">
        <div className="flex items-center text-xs text-muted-foreground">
          <Users className="h-3 w-3 mr-1" />
          {template.import_count} {t('importCount', { count: template.import_count })}
        </div>
        <Button
          size="sm"
          variant="outline"
          onClick={(e) => {
            e.stopPropagation();
            handleImportClick(template);
          }}
          className="opacity-0 group-hover:opacity-100 transition-opacity"
        >
          <Download className="h-4 w-4 mr-1" />
          {t('import')}
        </Button>
      </CardFooter>
    </Card>
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-4 sm:p-6 lg:p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold">{t('officialTemplateCatalog')}</h1>
          <p className="text-muted-foreground mt-1">
            {t('browseImportTemplates')}
          </p>
        </div>

        {notifications.length > 0 && (
          <Button variant="outline" className="relative">
            <Bell className="h-4 w-4 mr-2" />
            {t('updateNotifications')}
            <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center">
              {notifications.length}
            </span>
          </Button>
        )}
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder={t('searchTemplates')}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>

        <Select
          value={selectedType}
          onChange={(e) => setSelectedType(e.target.value)}
          className="w-[140px]"
          options={[
            { value: "all", label: t('allTypes') },
            { value: "agent", label: "Agent" },
            { value: "task", label: "Task" },
            { value: "crew", label: "Crew" },
          ]}
        />

        <Select
          value={selectedCategory}
          onChange={(e) => setSelectedCategory(e.target.value)}
          className="w-[140px]"
          options={[
            { value: "all", label: t('allCategories') },
            ...categories.map((cat) => ({
              value: cat.category,
              label: `${cat.category} (${cat.count})`,
            })),
          ]}
        />
      </div>

      {/* Tabs */}
      <Tabs defaultValue="all" className="mb-6">
        <TabsList>
          <TabsTrigger value="all">{t('all')}</TabsTrigger>
          <TabsTrigger value="featured">{t('featured')}</TabsTrigger>
          <TabsTrigger value="agents">Agents</TabsTrigger>
          <TabsTrigger value="tasks">Tasks</TabsTrigger>
          <TabsTrigger value="crews">Crews</TabsTrigger>
        </TabsList>

        <TabsContent value="all" className="mt-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {templates.map(renderTemplateCard)}
          </div>
        </TabsContent>

        <TabsContent value="featured" className="mt-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {templates.filter((t) => t.is_featured).map(renderTemplateCard)}
          </div>
        </TabsContent>

        <TabsContent value="agents" className="mt-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {templates
              .filter((t) => t.template_type === "agent")
              .map(renderTemplateCard)}
          </div>
        </TabsContent>

        <TabsContent value="tasks" className="mt-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {templates
              .filter((t) => t.template_type === "task")
              .map(renderTemplateCard)}
          </div>
        </TabsContent>

        <TabsContent value="crews" className="mt-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {templates
              .filter((t) => t.template_type === "crew")
              .map(renderTemplateCard)}
          </div>
        </TabsContent>
      </Tabs>

      {templates.length === 0 && (
        <div className="text-center py-12 text-muted-foreground">
          <Workflow className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p>{t('noTemplates')}</p>
          <p className="text-sm mt-1">{t('noTemplatesHint')}</p>
        </div>
      )}

      {/* Import Dialog */}
      <Dialog open={importDialogOpen} onOpenChange={setImportDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('importTemplate')}</DialogTitle>
            <DialogDescription>
              {t('importToWorkspace', { name: selectedTemplate?.display_name || '' })}
            </DialogDescription>
          </DialogHeader>

          <div className="py-4">
            <label className="text-sm font-medium mb-2 block">{t('customName')}</label>
            <Input
              value={customName}
              onChange={(e) => setCustomName(e.target.value)}
              placeholder={t('customNamePlaceholder')}
            />
            <p className="text-xs text-muted-foreground mt-2">
              {t('importNote')}
            </p>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setImportDialogOpen(false)}
              disabled={importing}
            >
              {t('cancel')}
            </Button>
            <Button onClick={handleImport} disabled={importing || !customName}>
              {importing ? t('importing') : t('confirmImport')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// Ensure page is wrapped with ToastProvider for useToast
export default function TemplateCatalogPageWithProviders() {
  return (
    <ToastProvider>
      <TemplateCatalogPage />
    </ToastProvider>
  );
}
