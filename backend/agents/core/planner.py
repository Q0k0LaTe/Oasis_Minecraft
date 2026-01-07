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
from typing import List, Dict, Set
from datetime import datetime

from agents.schemas import ModIR, IRItem, IRBlock, IRTool, IRAsset, Task, TaskDAG, ToolCall, TaskStatus


class Planner:
    """
    Planner - Converts IR into Task DAG

    Creates an execution plan with proper dependencies.
    """

    def __init__(self):
        self.task_counter = 0

    def plan(self, ir: ModIR) -> TaskDAG:
        """
        Create execution plan from IR

        Args:
            ir: Complete Intermediate Representation

        Returns:
            TaskDAG with all tasks and dependencies
        """
        tasks = []
        self.task_counter = 0

        # Phase 1: Setup tasks
        setup_task = self._create_setup_task(ir)
        tasks.append(setup_task)

        # Phase 2: Asset generation tasks
        texture_tasks = self._create_texture_generation_tasks(ir)
        tasks.extend(texture_tasks)

        # Phase 3: Code generation tasks (depend on setup)
        code_tasks = self._create_code_generation_tasks(ir, setup_task.task_id)
        tasks.extend(code_tasks)

        # Phase 4: Asset writing tasks (depend on textures)
        asset_tasks = self._create_asset_writing_tasks(ir, [t.task_id for t in texture_tasks])
        tasks.extend(asset_tasks)

        # Phase 5: Build config tasks (depend on setup)
        build_config_task = self._create_build_config_task(ir, setup_task.task_id)
        tasks.append(build_config_task)

        # Phase 6: Validation task (depends on all code + assets)
        all_gen_tasks = code_tasks + asset_tasks
        validation_task = self._create_validation_task(ir, [t.task_id for t in all_gen_tasks] + [build_config_task.task_id])
        tasks.append(validation_task)

        # Phase 7: Build task (depends on validation)
        build_task = self._create_build_task(ir, validation_task.task_id)
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

    def _create_setup_task(self, ir: ModIR) -> Task:
        """Create workspace setup task"""
        return Task(
            task_id=self._next_task_id(),
            description="Setup mod workspace structure",
            task_type="setup",
            tool_calls=[
                ToolCall(
                    tool_name="workspace_setup",
                    parameters={
                        "mod_id": ir.mod_id,
                        "base_package": ir.base_package
                    }
                )
            ],
            inputs={"ir": ir.dict()},
            expected_outputs={"workspace_dir": f"generated/{ir.mod_id}"},
            parallelizable=False,
            priority=100
        )

    def _create_texture_generation_tasks(self, ir: ModIR) -> List[Task]:
        """Create texture generation tasks (can run in parallel)"""
        tasks = []

        # Collect all texture assets
        texture_assets = []
        for item in ir.items:
            texture_assets.append(("item", item.item_id, item.texture_asset))
        for block in ir.blocks:
            texture_assets.append(("block", block.block_id, block.texture_asset))
        for tool in ir.tools:
            texture_assets.append(("tool", tool.tool_id, tool.texture_asset))

        for asset_type, entity_id, asset in texture_assets:
            task = Task(
                task_id=self._next_task_id(),
                description=f"Generate texture for {entity_id}",
                task_type="generate_texture",
                tool_calls=[
                    ToolCall(
                        tool_name="image_generator",
                        parameters={
                            "prompt": asset.texture_generation_prompt,
                            "reference_ids": asset.texture_reference_ids,
                            "output_path": asset.file_path
                        }
                    )
                ],
                inputs={"asset": asset.dict()},
                expected_outputs={"texture_file": asset.file_path},
                parallelizable=True,  # Textures can generate in parallel
                priority=80
            )
            tasks.append(task)

        return tasks

    def _create_code_generation_tasks(self, ir: ModIR, depends_on: str) -> List[Task]:
        """Create Java code generation tasks"""
        tasks = []

        # Main mod class
        task = Task(
            task_id=self._next_task_id(),
            description=f"Generate main mod class: {ir.main_class_name}",
            task_type="generate_code",
            dependencies=[depends_on],
            tool_calls=[
                ToolCall(
                    tool_name="code_generator",
                    parameters={
                        "template": "main_mod_class",
                        "ir": ir.dict()
                    }
                )
            ],
            inputs={"ir": ir.dict()},
            expected_outputs={"java_file": f"src/main/java/{ir.base_package.replace('.', '/')}/{ir.main_class_name}.java"},
            priority=70
        )
        tasks.append(task)

        # Item classes
        for item in ir.items:
            task = Task(
                task_id=self._next_task_id(),
                description=f"Generate item class: {item.java_class_name}",
                task_type="generate_code",
                dependencies=[depends_on],
                tool_calls=[
                    ToolCall(
                        tool_name="code_generator",
                        parameters={
                            "template": "item_class",
                            "item": item.dict()
                        }
                    )
                ],
                inputs={"item": item.dict()},
                expected_outputs={"java_file": f"src/main/java/{item.java_package.replace('.', '/')}/{item.java_class_name}.java"},
                parallelizable=True,
                priority=60
            )
            tasks.append(task)

        # Block classes
        for block in ir.blocks:
            task = Task(
                task_id=self._next_task_id(),
                description=f"Generate block class: {block.java_class_name}",
                task_type="generate_code",
                dependencies=[depends_on],
                tool_calls=[
                    ToolCall(
                        tool_name="code_generator",
                        parameters={
                            "template": "block_class",
                            "block": block.dict()
                        }
                    )
                ],
                inputs={"block": block.dict()},
                expected_outputs={"java_file": f"src/main/java/{block.java_package.replace('.', '/')}/{block.java_class_name}.java"},
                parallelizable=True,
                priority=60
            )
            tasks.append(task)

        # Tool classes
        for tool in ir.tools:
            task = Task(
                task_id=self._next_task_id(),
                description=f"Generate tool class: {tool.java_class_name}",
                task_type="generate_code",
                dependencies=[depends_on],
                tool_calls=[
                    ToolCall(
                        tool_name="code_generator",
                        parameters={
                            "template": "tool_class",
                            "tool": tool.dict()
                        }
                    )
                ],
                inputs={"tool": tool.dict()},
                expected_outputs={"java_file": f"src/main/java/{tool.java_package.replace('.', '/')}/{tool.java_class_name}.java"},
                parallelizable=True,
                priority=60
            )
            tasks.append(task)

        return tasks

    def _create_asset_writing_tasks(self, ir: ModIR, depends_on: List[str]) -> List[Task]:
        """Create asset file writing tasks"""
        tasks = []

        # Group assets by type
        json_assets = [a for a in ir.assets if a.asset_type in ["model", "blockstate", "recipe", "loot_table"]]

        # Create tasks for JSON assets
        for asset in json_assets:
            task = Task(
                task_id=self._next_task_id(),
                description=f"Write {asset.asset_type}: {asset.file_path}",
                task_type="write_asset",
                dependencies=depends_on if asset.asset_type == "texture" else [],
                tool_calls=[
                    ToolCall(
                        tool_name="asset_writer",
                        parameters={
                            "file_path": asset.file_path,
                            "content": asset.json_content
                        }
                    )
                ],
                inputs={"asset": asset.dict()},
                expected_outputs={"asset_file": asset.file_path},
                parallelizable=True,
                priority=50
            )
            tasks.append(task)

        # Lang files (merge all lang entries)
        lang_task = Task(
            task_id=self._next_task_id(),
            description="Write language files",
            task_type="write_asset",
            tool_calls=[
                ToolCall(
                    tool_name="lang_merger",
                    parameters={
                        "ir": ir.dict()
                    }
                )
            ],
            inputs={"ir": ir.dict()},
            expected_outputs={"lang_file": f"assets/{ir.mod_id}/lang/en_us.json"},
            priority=50
        )
        tasks.append(lang_task)

        return tasks

    def _create_build_config_task(self, ir: ModIR, depends_on: str) -> Task:
        """Create build configuration task"""
        return Task(
            task_id=self._next_task_id(),
            description="Generate build configuration files",
            task_type="generate_config",
            dependencies=[depends_on],
            tool_calls=[
                ToolCall(
                    tool_name="config_generator",
                    parameters={
                        "ir": ir.dict()
                    }
                )
            ],
            inputs={"ir": ir.dict()},
            expected_outputs={
                "gradle_build": "build.gradle",
                "gradle_properties": "gradle.properties",
                "fabric_mod_json": "src/main/resources/fabric.mod.json"
            },
            priority=60
        )

    def _create_validation_task(self, ir: ModIR, depends_on: List[str]) -> Task:
        """Create pre-build validation task"""
        return Task(
            task_id=self._next_task_id(),
            description="Validate generated mod structure",
            task_type="validate",
            dependencies=depends_on,
            tool_calls=[
                ToolCall(
                    tool_name="validator",
                    parameters={
                        "ir": ir.dict()
                    }
                )
            ],
            inputs={"ir": ir.dict()},
            expected_outputs={"validation_report": "validation_report.json"},
            priority=40
        )

    def _create_build_task(self, ir: ModIR, depends_on: str) -> Task:
        """Create Gradle build task"""
        return Task(
            task_id=self._next_task_id(),
            description="Compile mod with Gradle",
            task_type="build",
            dependencies=[depends_on],
            tool_calls=[
                ToolCall(
                    tool_name="gradle_builder",
                    parameters={
                        "mod_id": ir.mod_id
                    }
                )
            ],
            inputs={"ir": ir.dict()},
            expected_outputs={"jar_file": f"build/libs/{ir.mod_id}-{ir.version}.jar"},
            priority=10
        )


__all__ = ["Planner"]
