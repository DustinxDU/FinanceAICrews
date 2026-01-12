from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class TemplateListItem(BaseModel):
    id: int
    template_key: str
    template_type: str
    version: str
    display_name: str
    description: Optional[str]
    category: str
    tags: Optional[List[str]]
    icon: Optional[str]
    is_featured: bool
    import_count: int
    published_at: datetime
    
    class Config:
        from_attributes = True

class TemplateDetail(TemplateListItem):
    payload: Dict[str, Any]
    source_file: Optional[str]
    published_by: Optional[str]

class TemplateImportRequest(BaseModel):
    custom_name: Optional[str] = None  # 可选的自定义名称

class TemplateImportResponse(BaseModel):
    success: bool
    message: str
    imported_resource_type: str
    imported_resource_id: int
    imported_resource_name: str

class TemplateUpdateNotificationItem(BaseModel):
    id: int
    template_key: str
    template_type: str
    display_name: str
    old_version: str
    new_version: str
    changelog: Optional[str]
    is_read: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class ApplyUpdateRequest(BaseModel):
    merge_strategy: str = "replace"  # replace, merge, skip

class ApplyUpdateResponse(BaseModel):
    success: bool
    message: str
    updated_resource_id: int

class CategoryCount(BaseModel):
    category: str
    count: int

class MyImportItem(BaseModel):
    import_id: int
    template_key: str
    template_type: str
    display_name: str
    imported_version: str
    latest_version: str
    has_update: bool
    is_customized: bool
    imported_resource_id: int
    imported_at: datetime
