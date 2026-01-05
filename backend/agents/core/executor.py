"""
Executor - Runs Task DAG

Responsibilities:
- Execute tasks in dependency order
- Invoke tools with parameters
- Track execution state
- Handle parallelization
- Report progress

The Executor is mechanical - it just runs the plan.
"""
from typing import Dict, Any, Callable, Optional
from pathlib import Path

from agents.schemas import TaskDAG, Task, TaskStatus, ToolCall


class ExecutionError(Exception):
    """Raised when task execution fails"""
    pass


class Executor:
    """
    Executor - Runs tasks from Task DAG

    Executes the plan created by the Planner.
    """

    def __init__(self, workspace_dir: Path, tool_registry: Dict[str, Callable]):
        """
        Initialize Executor

        Args:
            workspace_dir: Directory for mod generation
            tool_registry: Mapping of tool names to callable functions
        """
        self.workspace_dir = Path(workspace_dir)
        self.tool_registry = tool_registry
        self.execution_log = []

    def execute(
        self,
        dag: TaskDAG,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        Execute all tasks in the DAG

        Args:
            dag: Task DAG to execute
            progress_callback: Optional callback for progress updates

        Returns:
            Execution results

        Raises:
            ExecutionError: If any task fails
        """
        def log(msg: str):
            self.execution_log.append(msg)
            if progress_callback:
                progress_callback(msg)
            print(f"[Executor] {msg}")

        log(f"Starting execution of {dag.total_tasks} tasks")

        # Execute tasks in order
        while len(dag.completed_task_ids) < dag.total_tasks:
            # Get tasks ready to run
            ready_tasks = dag.get_ready_tasks()

            if not ready_tasks:
                # Check if we're stuck
                if len(dag.failed_task_ids) > 0:
                    raise ExecutionError(f"Execution failed: {len(dag.failed_task_ids)} tasks failed")
                else:
                    raise ExecutionError("Execution deadlock: no ready tasks but not all completed")

            # Execute ready tasks
            for task in ready_tasks:
                try:
                    log(f"Executing: {task.description}")
                    self._execute_task(task)
                    dag.mark_completed(task.task_id)
                    log(f"✓ Completed: {task.description}")
                except Exception as e:
                    error_msg = f"Task failed: {task.description} - {str(e)}"
                    log(f"✗ {error_msg}")
                    dag.mark_failed(task.task_id, str(e))
                    raise ExecutionError(error_msg) from e

        log(f"✓ Execution complete: {len(dag.completed_task_ids)}/{dag.total_tasks} tasks succeeded")

        return {
            "status": "success",
            "completed_tasks": len(dag.completed_task_ids),
            "total_tasks": dag.total_tasks,
            "execution_log": self.execution_log
        }

    def _execute_task(self, task: Task):
        """Execute a single task"""
        task.status = TaskStatus.RUNNING

        # Execute all tool calls for this task
        for tool_call in task.tool_calls:
            self._execute_tool_call(tool_call, task.inputs)

        task.status = TaskStatus.COMPLETED

    def _execute_tool_call(self, tool_call: ToolCall, task_inputs: Dict[str, Any]):
        """Execute a tool call"""
        tool_name = tool_call.tool_name

        if tool_name not in self.tool_registry:
            raise ExecutionError(f"Tool not found: {tool_name}")

        tool_func = self.tool_registry[tool_name]

        # Merge tool parameters with task inputs
        params = {**task_inputs, **tool_call.parameters}

        # Call the tool
        try:
            result = tool_func(**params)
            return result
        except Exception as e:
            raise ExecutionError(f"Tool {tool_name} failed: {str(e)}") from e


__all__ = ["Executor", "ExecutionError"]
