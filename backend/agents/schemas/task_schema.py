"""
Task Schema - Execution Plan

This defines the task DAG format that the Planner produces
and the Executor runs.

Tasks are atomic, deterministic operations.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


class TaskStatus(str, Enum):
    """Task execution status"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class ToolCall(BaseModel):
    """A call to a specific tool with parameters"""
    tool_name: str = Field(..., description="Tool identifier (e.g., 'code_generator', 'image_generator')")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Tool-specific parameters")
    expected_output: Optional[str] = Field(None, description="What this tool call should produce")


class Task(BaseModel):
    """A single atomic task in the execution plan"""
    task_id: str = Field(..., description="Unique task identifier")
    description: str = Field(..., description="Human-readable task description")
    task_type: str = Field(..., description="generate_code, generate_asset, build, validate, etc.")

    # Dependencies
    dependencies: List[str] = Field(default_factory=list, description="Task IDs that must complete first")

    # Execution
    tool_calls: List[ToolCall] = Field(default_factory=list, description="Tools to invoke for this task")
    inputs: Dict[str, Any] = Field(default_factory=dict, description="Input data from IR or previous tasks")
    expected_outputs: Dict[str, str] = Field(default_factory=dict, description="Output file paths or artifacts")

    # Status tracking
    status: TaskStatus = Field(TaskStatus.PENDING)
    started_at: Optional[datetime] = Field(None)
    completed_at: Optional[datetime] = Field(None)
    error_message: Optional[str] = Field(None)

    # Metadata
    parallelizable: bool = Field(False, description="Can run in parallel with other tasks")
    retryable: bool = Field(False, description="Can retry on failure")
    priority: int = Field(0, description="Higher priority runs first")


class TaskDAG(BaseModel):
    """
    Complete execution plan as a Directed Acyclic Graph

    The Planner produces this from the IR.
    The Executor runs it.
    """
    tasks: List[Task] = Field(..., description="All tasks to execute")
    entry_tasks: List[str] = Field(..., description="Task IDs with no dependencies (start here)")
    final_tasks: List[str] = Field(..., description="Task IDs that produce final outputs")

    # Metadata
    total_tasks: int = Field(...)
    estimated_duration_seconds: Optional[float] = Field(None)
    created_from_ir_id: str = Field(..., description="IR version this was planned from")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Execution state
    current_task_id: Optional[str] = Field(None, description="Currently executing task")
    completed_task_ids: List[str] = Field(default_factory=list)
    failed_task_ids: List[str] = Field(default_factory=list)

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        return None

    def get_ready_tasks(self) -> List[Task]:
        """Get tasks that are ready to run (dependencies met)"""
        ready = []
        for task in self.tasks:
            if task.status != TaskStatus.PENDING:
                continue
            # Check if all dependencies are completed
            deps_met = all(
                dep_id in self.completed_task_ids
                for dep_id in task.dependencies
            )
            if deps_met:
                ready.append(task)
        return ready

    def mark_completed(self, task_id: str):
        """Mark task as completed"""
        task = self.get_task(task_id)
        if task:
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            if task_id not in self.completed_task_ids:
                self.completed_task_ids.append(task_id)

    def mark_failed(self, task_id: str, error_message: str):
        """Mark task as failed"""
        task = self.get_task(task_id)
        if task:
            task.status = TaskStatus.FAILED
            task.error_message = error_message
            task.completed_at = datetime.utcnow()
            if task_id not in self.failed_task_ids:
                self.failed_task_ids.append(task_id)


# Export
__all__ = [
    "Task",
    "TaskDAG",
    "TaskStatus",
    "ToolCall",
]
