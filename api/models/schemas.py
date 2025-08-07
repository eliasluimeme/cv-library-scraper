"""
Additional schema models and utilities.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class TaskResult(BaseModel):
    """Generic task result model."""
    task_id: str = Field(..., description="Task identifier")
    status: str = Field(..., description="Task status")
    result: Optional[Dict[str, Any]] = Field(None, description="Task result data")
    error: Optional[str] = Field(None, description="Error message if failed")
    created_at: datetime = Field(..., description="Task creation time")
    started_at: Optional[datetime] = Field(None, description="Task start time")
    completed_at: Optional[datetime] = Field(None, description="Task completion time")
    duration: Optional[float] = Field(None, description="Task duration in seconds")


class APIMetrics(BaseModel):
    """API metrics model."""
    total_requests: int = Field(0, description="Total requests processed")
    total_errors: int = Field(0, description="Total errors encountered")
    average_response_time: float = Field(0.0, description="Average response time in ms")
    requests_per_minute: float = Field(0.0, description="Current requests per minute")
    
    # Endpoint-specific metrics
    auth_requests: int = Field(0, description="Authentication requests")
    search_requests: int = Field(0, description="Search requests")
    download_requests: int = Field(0, description="Download requests")
    
    # Success rates
    auth_success_rate: float = Field(0.0, description="Authentication success rate")
    search_success_rate: float = Field(0.0, description="Search success rate") 
    download_success_rate: float = Field(0.0, description="Download success rate")


class SystemResources(BaseModel):
    """System resource usage model."""
    cpu_percent: float = Field(..., description="CPU usage percentage")
    memory_total: int = Field(..., description="Total memory in bytes")
    memory_used: int = Field(..., description="Used memory in bytes")
    memory_percent: float = Field(..., description="Memory usage percentage")
    disk_total: int = Field(..., description="Total disk space in bytes")
    disk_used: int = Field(..., description="Used disk space in bytes")
    disk_percent: float = Field(..., description="Disk usage percentage")
    
    # Browser-specific resources
    browser_instances: int = Field(0, description="Number of browser instances")
    browser_memory_mb: float = Field(0.0, description="Browser memory usage in MB")


class ValidationError(BaseModel):
    """Validation error model."""
    field: str = Field(..., description="Field with validation error")
    message: str = Field(..., description="Validation error message")
    value: Any = Field(None, description="Invalid value")


class BulkOperationResult(BaseModel):
    """Bulk operation result model."""
    total: int = Field(..., description="Total operations attempted")
    successful: int = Field(..., description="Successful operations")
    failed: int = Field(..., description="Failed operations")
    errors: Optional[Dict[str, str]] = Field(None, description="Error details by item ID")
    duration: float = Field(..., description="Operation duration in seconds") 