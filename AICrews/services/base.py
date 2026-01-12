"""
Base Service - 服务基类

定义统一的服务接口规范。
"""

from __future__ import annotations

from typing import Generic, TypeVar, Optional, List
from pydantic import BaseModel
from sqlalchemy.orm import Session

from AICrews.database.models.base import Base as ORMBase


T = TypeVar('T', bound=ORMBase)
SchemaT = TypeVar('SchemaT', bound=BaseModel)


class BaseService(Generic[T]):
    """基础服务类
    
    提供通用的 CRUD 操作接口。
    所有服务类都应该继承此基类。
    """
    
    def __init__(self, db: Session, model: type[T]):
        """初始化服务
        
        Args:
            db: 数据库会话
            model: ORM 模型类
        """
        self.db = db
        self.model = model
    
    def get_by_id(self, id: int) -> Optional[T]:
        """根据 ID 获取实体
        
        Args:
            id: 实体 ID
            
        Returns:
            实体对象，如果不存在则返回 None
        """
        return self.db.query(self.model).filter(self.model.id == id).first()
    
    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        order_by: str = "id"
    ) -> List[T]:
        """获取实体列表
        
        Args:
            skip: 跳过记录数
            limit: 返回记录数
            order_by: 排序字段
            
        Returns:
            实体列表
        """
        query = self.db.query(self.model)
        if hasattr(self.model, order_by):
            order_field = getattr(self.model, order_by)
            query = query.order_by(order_field.desc())
        return query.offset(skip).limit(limit).all()
    
    def create(self, **kwargs) -> T:
        """创建实体
        
        Args:
            **kwargs: 实体字段
            
        Returns:
            新创建的实体对象
        """
        obj = self.model(**kwargs)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj
    
    def update(self, id: int, **kwargs) -> Optional[T]:
        """更新实体
        
        Args:
            id: 实体 ID
            **kwargs: 要更新的字段
            
        Returns:
            更新后的实体对象，如果不存在则返回 None
        """
        obj = self.get_by_id(id)
        if not obj:
            return None
        
        for key, value in kwargs.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
        
        self.db.commit()
        self.db.refresh(obj)
        return obj
    
    def delete(self, id: int) -> bool:
        """删除实体
        
        Args:
            id: 实体 ID
            
        Returns:
            删除成功返回 True，否则返回 False
        """
        obj = self.get_by_id(id)
        if not obj:
            return False
        
        self.db.delete(obj)
        self.db.commit()
        return True
    
    def count(self) -> int:
        """获取实体总数
        
        Returns:
            实体总数
        """
        return self.db.query(self.model).count()


__all__ = ["BaseService"]
