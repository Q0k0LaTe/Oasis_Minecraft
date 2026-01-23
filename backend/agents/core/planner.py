"""
Planner - IR → Task DAG

Responsibilities:
- Convert ModIR into executable Task DAG
- Build dependency graph
- Identify parallelizable tasks
- Bind tasks to tools

The Planner is "dumb" - it mechanically decomposes IR into tasks.
No interpretation or reasoning.
"""
from typing import List, Dict, Set, Optional
from datetime import datetime
from pathlib import Path

from agents.schemas import ModIR, IRItem, IRBlock, IRTool, IRAsset, Task, TaskDAG, ToolCall, TaskStatus


class Planner:
    """
    Planner - Converts IR into Task DAG

    Creates an execution plan with proper dependencies.
    """

    def __init__(self):
        self.task_counter = 0

    def plan(self, ir: ModIR, workspace_root: Optional[Path] = None) -> TaskDAG:
        """
        Create execution plan from IR

        Args:
            ir: Complete Intermediate Representation
            workspace_root: Base directory where the mod should be generated

        Returns:
            TaskDAG with all tasks and dependencies
        """
        workspace_root = Path(workspace_root) if workspace_root else Path("generated")
        mod_workspace = workspace_root / ir.mod_id

        tasks = []
        self.task_counter = 0

        # Phase 1: Setup workspace
        setup_task = self._create_setup_task(ir, workspace_root, mod_workspace)
        tasks.append(setup_task)

        # Phase 2: Generate textures (can run in parallel)
        texture_tasks = self._create_texture_generation_tasks(ir)
        tasks.extend(texture_tasks)

        # Phase 3: Generate Java code (depends on setup)
        code_task = self._create_code_generation_task(ir, setup_task.task_id, mod_workspace)
        tasks.append(code_task)

        # Phase 4: Generate assets (depends on textures)
        assets_task = self._create_assets_generation_task(ir, [t.task_id for t in texture_tasks], mod_workspace)
        tasks.append(assets_task)

        # Phase 5: Generate build configuration (depends on setup)
        config_tasks = self._create_build_config_tasks(ir, setup_task.task_id, mod_workspace)
        tasks.extend(config_tasks)

        # Phase 6: Setup Gradle wrapper (depends on setup)
        gradle_wrapper_task = self._create_gradle_wrapper_task(ir, setup_task.task_id, mod_workspace)
        tasks.append(gradle_wrapper_task)

        # Phase 7: Build mod (depends on everything)
        all_task_ids = [t.task_id for t in tasks]
        build_task = self._create_build_task(ir, all_task_ids, mod_workspace)
        tasks.append(build_task)

        # Create DAG
        dag = TaskDAG(
            tasks=tasks,
            entry_tasks=[setup_task.task_id],
            final_tasks=[build_task.task_id],
            total_tasks=len(tasks),
            created_from_ir_id=ir.mod_id,
            created_at=datetime.utcnow()
        )

        print(f"✓ Planned {len(tasks)} tasks for {ir.mod_id}")
        return dag

    def _next_task_id(self) -> str:
        """Generate next task ID"""
        self.task_counter += 1
        return f"task_{self.task_counter:03d}"

    def _create_setup_task(self, ir: ModIR, workspace_root: Path, mod_workspace: Path) -> Task:
        """Create workspace setup task"""
        return Task(
            task_id=self._next_task_id(),
            description="Setup mod workspace structure",
            task_type="setup",
            tool_calls=[
                ToolCall(
                    tool_name="setup_workspace",
                    parameters={
                        "workspace_dir": str(workspace_root),
                        "mod_id": ir.mod_id,
                        "package_name": ir.base_package
                    }
                )
            ],
            inputs={},
            expected_outputs={"workspace_path": str(mod_workspace)},
            parallelizable=False,
            priority=100
        )

    def _create_texture_generation_tasks(self, ir: ModIR) -> List[Task]:
        """
        Create texture generation tasks (can run in parallel).

        Routes to different generators based on entity type:
        - Items/Tools: ItemImageGenerator (transparent backgrounds, sprites)
        - Blocks: BlockImageGenerator (opaque, seamless tileable textures)
        """
        tasks = []

        # Create tasks for items
        for item in ir.items:
            task = Task(
                task_id=self._next_task_id(),
                description=f"Generate texture for {item.display_name}",
                task_type="generate_texture",
                tool_calls=[
                    ToolCall(
                        tool_name="generate_texture",
                        parameters={
                            "item_name": item.display_name,
                            "description": item.description,
                            "variant_count": 3,
                            "entity_type": "item"
                        }
                    )
                ],
                inputs={"entity_id": item.item_id, "entity_type": "item"},
                expected_outputs={"texture_variants": []},
                parallelizable=True,
                priority=80
            )
            tasks.append(task)

        # Create tasks for blocks (uses NEW BlockImageGenerator algorithm)
        for block in ir.blocks:
            task = Task(
                task_id=self._next_task_id(),
                description=f"Generate texture for {block.display_name}",
                task_type="generate_texture",
                tool_calls=[
                    ToolCall(
                        tool_name="generate_texture",
                        parameters={
                            "item_name": block.display_name,
                            "description": block.description,
                            "variant_count": 3,
                            "entity_type": "block",
                            # Block-specific parameters for the new algorithm
                            "material": block.material,
                            "luminance": block.luminance,
                            "gameplay_role": block.description
                        }
                    )
                ],
                inputs={"entity_id": block.block_id, "entity_type": "block"},
                expected_outputs={"texture_variants": []},
                parallelizable=True,
                priority=80
            )
            tasks.append(task)

        # Create tasks for tools
        for tool in ir.tools:
            task = Task(
                task_id=self._next_task_id(),
                description=f"Generate texture for {tool.display_name}",
                task_type="generate_texture",
                tool_calls=[
                    ToolCall(
                        tool_name="generate_texture",
                        parameters={
                            "item_name": tool.display_name,
                            "description": tool.description,
                            "variant_count": 3,
                            "entity_type": "tool"
                        }
                    )
                ],
                inputs={"entity_id": tool.tool_id, "entity_type": "tool"},
                expected_outputs={"texture_variants": []},
                parallelizable=True,
                priority=80
            )
            tasks.append(task)

        return tasks

    def _create_code_generation_task(self, ir: ModIR, depends_on: str, mod_workspace: Path) -> Task:
        """Create Java code generation task (generates all code at once)"""
        # Convert IR items/blocks/tools to dict format for the tool
        items_data = [item.model_dump() for item in ir.items]
        blocks_data = [block.model_dump() for block in ir.blocks]
        tools_data = [tool.model_dump() for tool in ir.tools]

        return Task(
            task_id=self._next_task_id(),
            description=f"Generate Java code for {ir.mod_name}",
            task_type="generate_code",
            dependencies=[depends_on],
            tool_calls=[
                ToolCall(
                    tool_name="generate_java_code",
                    parameters={
                        "workspace_path": str(mod_workspace),
                        "package_name": ir.base_package,
                        "mod_id": ir.mod_id,
                        "main_class_name": ir.main_class_name,
                        "items": items_data,
                        "blocks": blocks_data,
                        "tools": tools_data
                    }
                )
            ],
            inputs={"ir": ir.model_dump()},
            expected_outputs={"main_class_path": "src/main/java/..."},
            priority=70
        )

    def _create_assets_generation_task(self, ir: ModIR, depends_on: List[str], mod_workspace: Path) -> Task:
        """Create assets generation task (generates all resource files)"""
        items_data = [item.model_dump() for item in ir.items]
        blocks_data = [block.model_dump() for block in ir.blocks]
        tools_data = [tool.model_dump() for tool in ir.tools]

        # Placeholder textures dict - will be populated by texture generation tasks
        textures = {}

        return Task(
            task_id=self._next_task_id(),
            description=f"Generate assets for {ir.mod_name}",
            task_type="generate_assets",
            dependencies=depends_on,
            tool_calls=[
                ToolCall(
                    tool_name="generate_assets",
                    parameters={
                        "workspace_path": str(mod_workspace),
                        "mod_id": ir.mod_id,
                        "items": items_data,
                        "blocks": blocks_data,
                        "tools": tools_data,
                        "textures": textures
                    }
                )
            ],
            inputs={"ir": ir.model_dump()},
            expected_outputs={"assets_path": "src/main/resources/assets"},
            priority=60
        )

    def _create_build_config_tasks(self, ir: ModIR, depends_on: str, mod_workspace: Path) -> List[Task]:
        """Create build configuration tasks"""
        tasks = []

        # Generate Gradle files
        gradle_task = Task(
            task_id=self._next_task_id(),
            description="Generate Gradle build files",
            task_type="generate_config",
            dependencies=[depends_on],
            tool_calls=[
                ToolCall(
                    tool_name="generate_gradle_files",
                    parameters={
                        "workspace_path": str(mod_workspace),
                        "mod_id": ir.mod_id,
                        "mod_name": ir.mod_name,
                        "version": ir.version,
                        "minecraft_version": ir.minecraft_version,
                        "dependencies": []
                    }
                )
            ],
            inputs={"ir": ir.model_dump()},
            expected_outputs={"build_gradle": "build.gradle"},
            priority=60
        )
        tasks.append(gradle_task)

        # Generate fabric.mod.json
        fabric_json_task = Task(
            task_id=self._next_task_id(),
            description="Generate fabric.mod.json",
            task_type="generate_config",
            dependencies=[depends_on],
            tool_calls=[
                ToolCall(
                    tool_name="generate_fabric_mod_json",
                    parameters={
                        "workspace_path": str(mod_workspace),
                        "mod_id": ir.mod_id,
                        "mod_name": ir.mod_name,
                        "version": ir.version,
                        "description": ir.description,
                        "authors": [ir.author] if ir.author else [],
                        "license": "MIT",
                        "package_name": ir.base_package,
                        "main_class_name": ir.main_class_name
                    }
                )
            ],
            inputs={"ir": ir.model_dump()},
            expected_outputs={"fabric_mod_json": "src/main/resources/fabric.mod.json"},
            priority=60
        )
        tasks.append(fabric_json_task)

        # Generate mixins.json
        mixins_task = Task(
            task_id=self._next_task_id(),
            description="Generate mixins.json",
            task_type="generate_config",
            dependencies=[depends_on],
            tool_calls=[
                ToolCall(
                    tool_name="generate_mixins_json",
                    parameters={
                        "workspace_path": str(mod_workspace),
                        "mod_id": ir.mod_id,
                        "package_name": ir.base_package
                    }
                )
            ],
            inputs={
                "ir": ir.model_dump(),
                "mod_id": ir.mod_id,
                "package_name": ir.base_package
            },
            expected_outputs={"mixins_json": f"src/main/resources/{ir.mod_id}.mixins.json"},
            priority=60
        )
        tasks.append(mixins_task)

        return tasks

    def _create_gradle_wrapper_task(self, ir: ModIR, depends_on: str, mod_workspace: Path) -> Task:
        """Create Gradle wrapper setup task"""
        return Task(
            task_id=self._next_task_id(),
            description="Setup Gradle wrapper",
            task_type="setup",
            dependencies=[depends_on],
            tool_calls=[
                ToolCall(
                    tool_name="setup_gradle_wrapper",
                    parameters={
                        "workspace_path": str(mod_workspace)
                    }
                )
            ],
            inputs={},
            expected_outputs={"gradle_wrapper": "gradle/wrapper"},
            priority=50
        )

    def _create_build_task(self, ir: ModIR, depends_on: List[str], mod_workspace: Path) -> Task:
        """Create Gradle build task"""
        return Task(
            task_id=self._next_task_id(),
            description="Build mod with Gradle",
            task_type="build",
            dependencies=depends_on,
            tool_calls=[
                ToolCall(
                    tool_name="build_mod",
                    parameters={
                        "workspace_path": str(mod_workspace),
                        "mod_id": ir.mod_id
                    }
                )
            ],
            inputs={"ir": ir.model_dump()},
            expected_outputs={"jar_file": f"build/libs/{ir.mod_id}-{ir.version}.jar"},
            priority=10
        )


__all__ = ["Planner"]
