"""Task planner and decomposition for autonomous objectives."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class PlannedTask:
    id: str
    title: str
    description: str
    expected_result: str
    subtasks: List[Dict[str, Any]] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)  # ids of tasks that must complete first
    required_tools: List[str] = field(default_factory=list)
    completion_conditions: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    action: Dict[str, Any] = field(default_factory=dict)  # executable hint: {type, ...}


@dataclass
class Plan:
    objective: str
    description: str
    tasks: List[PlannedTask]
    risks: List[str] = field(default_factory=list)
    missing_information: List[str] = field(default_factory=list)
    clarifications: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "objective": self.objective,
            "description": self.description,
            "tasks": [asdict(t) for t in self.tasks],
            "risks": self.risks,
            "missing_information": self.missing_information,
            "clarifications": self.clarifications,
        }


class TaskPlanner:
    """Transforms natural-language objectives into structured task plans.

    Uses deterministic heuristics so autonomous workflows are testable without
    an external LLM; can be extended to call the model service for richer plans.
    """

    def plan(self, objective: str, context: Optional[Dict[str, Any]] = None) -> Plan:
        obj = (objective or "").strip()
        lower = obj.lower()
        tasks: List[PlannedTask] = []
        risks: List[str] = []

        # 1) Requirement extraction / objective identification (heuristic)
        if not obj:
            return Plan(objective=obj, description="No objective provided", tasks=[], missing_information=["Objective is empty"], clarifications=["What should I do?"])

        # Pattern: create folder and several files
        if "folder" in lower and "file" in lower and ("create" in lower or "make" in lower):
            tasks = self._plan_create_folder_files(obj)
        # Pattern: install package
        elif "install" in lower and ("package" in lower or "pip" in lower or "npm" in lower or "dependency" in lower):
            tasks = self._plan_install_package(obj)
        # Pattern: build/create app/application
        elif ("build" in lower or "create" in lower or "develop" in lower) and ("app" in lower or "application" in lower or "project" in lower):
            tasks = self._plan_build_app(obj)
        # Pattern: diagnose/fix/debug/error
        elif any(k in lower for k in ["diagnose", "debug", "error", "fix", "issue", "failure", "failing"]):
            tasks = self._plan_diagnose_error(obj)
        # Pattern: download and organize
        elif "download" in lower and "organize" in lower:
            tasks = self._plan_download_organize(obj)
        # Pattern: organize documents/files
        elif "organize" in lower and any(k in lower for k in ["document", "file", "folder"]):
            tasks = self._plan_organize_documents(obj)
        else:
            tasks = self._plan_generic(obj)

        # 4) Dependency analysis / 5) ordering already encoded in dependencies lists
        # 6) Missing info detection
        missing = self._detect_missing(obj, lower)
        clarifications = [f"Please clarify: {m}" for m in missing] if missing else []
        # 7) Risks
        if any(t.action.get("type") == "tool" for t in tasks):
            risks.append("Tool execution may fail or require permissions.")
        if any("delete" in (t.title + t.description).lower() for t in tasks):
            risks.append("Destructive file operations require care.")

        return Plan(
            objective=obj,
            description=f"Plan to accomplish: {obj}",
            tasks=tasks,
            risks=risks or ["Low risk if steps are followed."],
            missing_information=missing,
            clarifications=clarifications,
        )

    def _tid(self) -> str:
        return str(uuid.uuid4())[:8]

    def _plan_create_folder_files(self, obj: str) -> List[PlannedTask]:
        # extract folder name simple
        m = re.search(r"folder\s+(?:named\s+|called\s+)?['\"]?([\w\-./]+)['\"]?", obj, re.I)
        folder = m.group(1) if m else "new_folder"
        m2 = re.search(r"(\d+)\s+files", obj, re.I)
        count = int(m2.group(1)) if m2 else 3
        t1 = PlannedTask(
            id=self._tid(), title=f"Create folder '{folder}'",
            description=f"Create directory {folder}.",
            expected_result=f"Folder {folder} exists.",
            dependencies=[], required_tools=["filesystem"],
            completion_conditions=[f"Directory {folder} exists"],
            action={"type": "tool", "server": "filesystem", "tool": "fs.create_directory", "arguments": {"path": folder, "recursive": True}},
        )
        tasks = [t1]
        prev = t1.id
        for i in range(1, count + 1):
            name = f"{folder}/file{i}.txt"
            t = PlannedTask(
                id=self._tid(), title=f"Create file '{name}'",
                description=f"Create file {name} inside {folder}.",
                expected_result=f"File {name} exists.",
                dependencies=[prev], required_tools=["filesystem"],
                completion_conditions=[f"File {name} exists"],
                action={"type": "tool", "server": "filesystem", "tool": "fs.create_file", "arguments": {"path": name, "content": f"Content for file {i}\n", "overwrite": True}},
            )
            tasks.append(t)
            prev = t.id
        t_verify = PlannedTask(
            id=self._tid(), title="Verify created structure",
            description=f"List {folder} to verify files were created.",
            expected_result=f"{folder} contains {count} files.",
            dependencies=[prev], required_tools=["filesystem"],
            completion_conditions=["Listing shows expected files"],
            action={"type": "tool", "server": "filesystem", "tool": "fs.list_directory", "arguments": {"path": folder}},
        )
        tasks.append(t_verify)
        return tasks

    def _plan_install_package(self, obj: str) -> List[PlannedTask]:
        m = re.search(r"install\s+(?:package\s+)?['\"]?([a-zA-Z0-9_\-\.]+)['\"]?", obj, re.I)
        pkg = m.group(1) if m else "package"
        installer = "pip" if "pip" in obj.lower() or "python" in obj.lower() else ("npm" if "npm" in obj.lower() else "pip")
        cmd = f"{installer} show {pkg} || echo not-installed"
        install_cmd = f"{installer} install {pkg}"
        t1 = PlannedTask(id=self._tid(), title=f"Check if {pkg} is installed", description=f"Check current installation state of {pkg}.", expected_result="Know whether package is present.", dependencies=[], required_tools=["terminal"], completion_conditions=["Check command completes"], risks=["Environment may differ."], action={"type": "tool", "server": "terminal", "tool": "terminal.execute", "arguments": {"command": cmd}})
        t2 = PlannedTask(id=self._tid(), title=f"Install {pkg}", description=f"Install package {pkg} using {installer}.", expected_result=f"{pkg} installed (if permitted).", dependencies=[t1.id], required_tools=["terminal"], completion_conditions=["Install command exits successfully"], risks=["May require permissions/network; only run when permitted."], action={"type": "tool", "server": "terminal", "tool": "terminal.execute", "arguments": {"command": install_cmd}})
        t3 = PlannedTask(id=self._tid(), title=f"Verify {pkg} installation", description=f"Verify {pkg} is available.", expected_result=f"{pkg} importable/available.", dependencies=[t2.id], required_tools=["terminal"], completion_conditions=["Verification succeeds"], action={"type": "tool", "server": "terminal", "tool": "terminal.execute", "arguments": {"command": f"{installer} show {pkg}"}})
        return [t1, t2, t3]

    def _plan_build_app(self, obj: str) -> List[PlannedTask]:
        m = re.search(r"(?:build|create|develop)\s+(?:a\s+)?(?:small\s+)?([a-zA-Z0-9_\- ]+?)\s+(?:app|application)", obj, re.I)
        kind = (m.group(1).strip() if m else "python")
        app_dir = "sample_app"
        t1 = PlannedTask(id=self._tid(), title="Create application directory", description=f"Create directory {app_dir} for the application.", expected_result=f"{app_dir} exists.", dependencies=[], required_tools=["filesystem"], completion_conditions=["Directory exists"], action={"type": "tool", "server": "filesystem", "tool": "fs.create_directory", "arguments": {"path": app_dir, "recursive": True}})
        content = "def main():\n    print('Hello from NEXUS AI sample app')\n\nif __name__ == '__main__':\n    main()\n"
        t2 = PlannedTask(id=self._tid(), title="Create application entry file", description="Create main application file.", expected_result="main.py created.", dependencies=[t1.id], required_tools=["filesystem"], completion_conditions=["File exists"], action={"type": "tool", "server": "filesystem", "tool": "fs.create_file", "arguments": {"path": f"{app_dir}/main.py", "content": content, "overwrite": True}})
        t3 = PlannedTask(id=self._tid(), title="Verify application structure", description="List application files.", expected_result="Application files present.", dependencies=[t2.id], required_tools=["filesystem"], completion_conditions=["Listing shows main.py"], action={"type": "tool", "server": "filesystem", "tool": "fs.list_directory", "arguments": {"path": app_dir}})
        t4 = PlannedTask(id=self._tid(), title="Run application smoke check", description="Execute the application to verify it runs.", expected_result="App runs and prints greeting.", dependencies=[t3.id], required_tools=["terminal"], completion_conditions=["Process exits 0"], action={"type": "tool", "server": "terminal", "tool": "terminal.execute", "arguments": {"command": f"cd {app_dir} && python3 main.py"}})
        return [t1, t2, t3, t4]

    def _plan_diagnose_error(self, obj: str) -> List[PlannedTask]:
        t1 = PlannedTask(id=self._tid(), title="Gather error context", description="Inspect recent logs/status relevant to the reported error.", expected_result="Context collected.", dependencies=[], required_tools=["terminal"], completion_conditions=["Status/log command completes"], action={"type": "tool", "server": "terminal", "tool": "terminal.execute", "arguments": {"command": "pwd && ls -la | head -20"}})
        t2 = PlannedTask(id=self._tid(), title="Identify likely cause", description="Analyze gathered context to identify probable cause.", expected_result="Probable cause identified.", dependencies=[t1.id], required_tools=[], completion_conditions=["Analysis recorded"], action={"type": "analysis", "note": "Analyze command output and objective to determine likely cause."})
        t3 = PlannedTask(id=self._tid(), title="Propose and record fix", description="Document recommended fix or mitigation.", expected_result="Fix recommendation recorded.", dependencies=[t2.id], required_tools=[], completion_conditions=["Recommendation recorded"], action={"type": "analysis", "note": "Provide fix steps based on diagnosis."})
        return [t1, t2, t3]

    def _plan_download_organize(self, obj: str) -> List[PlannedTask]:
        return self._plan_organize_documents(obj)

    def _plan_organize_documents(self, obj: str) -> List[PlannedTask]:
        target = "organized_docs"
        t1 = PlannedTask(id=self._tid(), title="Inspect target area", description="List files to understand what needs organizing.", expected_result="Current files listed.", dependencies=[], required_tools=["filesystem"], completion_conditions=["Listing available"], action={"type": "tool", "server": "filesystem", "tool": "fs.list_directory", "arguments": {"path": "."}})
        t2 = PlannedTask(id=self._tid(), title="Create organization folder", description=f"Create folder {target} for organized items.", expected_result=f"{target} exists.", dependencies=[t1.id], required_tools=["filesystem"], completion_conditions=["Directory exists"], action={"type": "tool", "server": "filesystem", "tool": "fs.create_directory", "arguments": {"path": target, "recursive": True}})
        t3 = PlannedTask(id=self._tid(), title="Verify organization folder", description=f"Confirm {target} is ready.", expected_result=f"{target} present.", dependencies=[t2.id], required_tools=["filesystem"], completion_conditions=["Folder exists"], action={"type": "tool", "server": "filesystem", "tool": "fs.stat", "arguments": {"path": target}})
        return [t1, t2, t3]

    def _plan_generic(self, obj: str) -> List[PlannedTask]:
        t1 = PlannedTask(id=self._tid(), title="Understand objective", description=f"Analyze objective: {obj}", expected_result="Objective understood and scoped.", dependencies=[], required_tools=[], completion_conditions=["Objective analyzed"], action={"type": "analysis", "note": obj})
        t2 = PlannedTask(id=self._tid(), title="Gather relevant context", description="Collect information needed to proceed.", expected_result="Context gathered.", dependencies=[t1.id], required_tools=[], completion_conditions=["Context recorded"], action={"type": "analysis", "note": "Gather context"})
        t3 = PlannedTask(id=self._tid(), title="Execute primary steps", description="Perform the main actions required by the objective.", expected_result="Primary steps completed.", dependencies=[t2.id], required_tools=[], completion_conditions=["Actions attempted"], action={"type": "analysis", "note": "Execute objective"})
        t4 = PlannedTask(id=self._tid(), title="Verify outcome", description="Verify the objective was addressed.", expected_result="Outcome verified and reported.", dependencies=[t3.id], required_tools=[], completion_conditions=["Verification recorded"], action={"type": "analysis", "note": "Verify"})
        return [t1, t2, t3, t4]

    def _detect_missing(self, obj: str, lower: str) -> List[str]:
        missing: List[str] = []
        if len(obj.split()) < 2:
            missing.append("Objective is too vague")
        if "install" in lower and "package" in lower and not re.search(r"install\s+(?:package\s+)?['\"]?[a-zA-Z0-9_\-\.]+", lower):
            missing.append("Which package should be installed?")
        return missing
