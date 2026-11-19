from typing import Any, Dict, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    user_id: str
    name: str
    email: str
    department: str
    role: str


class RequestCreate(BaseModel):
    category: str = Field(..., description="Request category, e.g. Hardware, Software, Access, Supplies")
    priority: str = Field(default="Medium", description="Low, Medium, High, Urgent")
    description: str = Field(..., description="Details and justification for the request")
    web_context: Optional[Dict[str, Any]] = Field(default=None, description="Metadata from the originating web page")


class ServiceRequest(BaseModel):
    id: str
    user_id: str
    user_name: str
    user_email: str
    department: str
    category: str
    priority: str
    description: str
    status: str = "Pending Approval"
    created_at: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    submitted_via: str = "web_form"  # "web_form" or "agent_assistant"
