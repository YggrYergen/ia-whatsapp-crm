from supabase import Client
from typing import TypeVar, Generic, Type, Optional, Dict, Any

T = TypeVar("T")

class BaseRepository(Generic[T]):
    """Generic repository abstractions for database operations."""
    
    def __init__(self, db: Client, table_name: str, model_class: Type[T]):
        self.db = db
        self.table_name = table_name
        self.model_class = model_class

    def get_by_id(self, record_id: str) -> Optional[T]:
        response = self.db.table(self.table_name).select("*").eq("id", record_id).execute()
        if response.data:
            return self.model_class(**response.data[0])
        return None

    def create(self, data: Dict[str, Any]) -> T:
        response = self.db.table(self.table_name).insert(data).execute()
        return self.model_class(**response.data[0])
