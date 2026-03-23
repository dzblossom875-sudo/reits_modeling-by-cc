"""
项目配置管理模块
提供统一的配置加载、项目确认和路径管理
"""

import os
import sys
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class ProjectConfig:
    """单个项目的配置"""
    name: str
    asset_types: List[str]
    data_dir: str
    output_dir: str
    label: str
    description: str = ""


@dataclass
class RunConfig:
    """运行配置"""
    auto_create_dirs: bool = True
    keep_run_history: bool = True
    latest_update_mode: str = "copy"


class ProjectConfigManager:
    """
    项目配置管理器

    职责:
    1. 加载 run_config.yaml
    2. 交互式确认 active_project
    3. 提供统一的路径获取接口
    4. 支持命令行参数和环境变量覆盖

    Usage:
        # 自动确认或使用默认值
        config = ProjectConfigManager.auto_select()

        # 交互式确认
        config = ProjectConfigManager.interactive_select()

        # 强制指定项目
        config = ProjectConfigManager(project_name="huazhu")
    """

    _instance = None
    _config_path: Optional[Path] = None

    def __new__(cls, *args, **kwargs):
        """单例模式确保配置只加载一次"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        project_name: Optional[str] = None,
        config_path: Optional[str] = None,
        auto_confirm: bool = False,
        silent: bool = False
    ):
        if self._initialized:
            return

        self._root_dir = Path(__file__).parent.parent.parent
        self._config_path = Path(config_path) if config_path else self._root_dir / "run_config.yaml"
        self._silent = silent

        # 加载配置
        self._config_data = self._load_config()
        self._projects: Dict[str, ProjectConfig] = {}
        self._run_config = RunConfig()
        self._parse_config()

        # 确定 active_project（优先级: 参数 > 环境变量 > 配置文件）
        self._active_project = self._resolve_active_project(project_name)

        # 如果需要交互确认
        if not auto_confirm and not silent:
            self._active_project = self._interactive_confirm(self._active_project)

        self._initialized = True

    def _load_config(self) -> Dict[str, Any]:
        """加载 YAML 配置文件"""
        if not self._config_path.exists():
            raise FileNotFoundError(
                f"配置文件不存在: {self._config_path}\n"
                f"请确保项目根目录存在 run_config.yaml"
            )

        with open(self._config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _parse_config(self):
        """解析配置数据"""
        # 解析项目配置
        projects_data = self._config_data.get('projects', {})
        for name, data in projects_data.items():
            self._projects[name] = ProjectConfig(
                name=name,
                asset_types=data.get('asset_types', []),
                data_dir=data.get('data_dir', f'data/{name}'),
                output_dir=data.get('output_dir', f'output/{name}'),
                label=data.get('label', name),
                description=data.get('description', '')
            )

        # 解析运行配置
        run_cfg = self._config_data.get('run_config', {})
        self._run_config = RunConfig(
            auto_create_dirs=run_cfg.get('auto_create_dirs', True),
            keep_run_history=run_cfg.get('keep_run_history', True),
            latest_update_mode=run_cfg.get('latest_update_mode', 'copy')
        )

    def _resolve_active_project(self, override: Optional[str] = None) -> str:
        """
        确定 active_project（多优先级）

        优先级顺序:
        1. 构造函数参数 project_name
        2. 环境变量 REITS_PROJECT
        3. 命令行参数 --project
        4. 配置文件中的 active_project
        """
        # 1. 构造函数参数
        if override:
            return override

        # 2. 环境变量
        env_project = os.environ.get('REITS_PROJECT')
        if env_project:
            return env_project

        # 3. 命令行参数
        cmd_project = self._parse_cmdline_project()
        if cmd_project:
            return cmd_project

        # 4. 配置文件默认值
        return self._config_data.get('active_project', 'huazhu')

    def _parse_cmdline_project(self) -> Optional[str]:
        """解析命令行参数 --project"""
        for i, arg in enumerate(sys.argv):
            if arg in ('--project', '-p') and i + 1 < len(sys.argv):
                return sys.argv[i + 1]
            if arg.startswith('--project='):
                return arg.split('=', 1)[1]
        return None

    def _interactive_confirm(self, default_project: str) -> str:
        """
        交互式项目确认

        显示:
        - 可用项目列表
        - 当前选中项目（高亮）
        - 项目详情

        返回用户确认或选择的项目名称
        """
        # 非TTY环境自动返回默认值
        if not sys.stdin.isatty():
            return default_project

        print("\n" + "=" * 60)
        print("  REITs 建模项目选择")
        print("=" * 60)

        # 显示可用项目
        print("\n[可用项目列表]")
        print("-" * 60)

        project_list = list(self._projects.keys())
        for idx, (name, project) in enumerate(self._projects.items(), 1):
            marker = "=>" if name == default_project else "  "
            status = "[默认]" if name == default_project else ""

            print(f"\n{marker} {idx}. {project.label} {status}")
            print(f"      ID: {name}")
            print(f"      业态: {', '.join(project.asset_types)}")
            print(f"      描述: {project.description}")

        # 显示当前来源
        print("\n" + "-" * 60)
        source = self._detect_project_source()
        print(f"[当前选中项目] {self._projects[default_project].label} ({default_project})")
        print(f"   来源: {source}")

        # 提示用户确认或选择
        print("\n" + "-" * 60)
        print("操作选项:")
        print("  - 按回车确认使用当前项目")
        print("  - 输入数字 (1-{}) 切换项目".format(len(project_list)))
        print("  - 输入 'q' 退出程序")

        try:
            choice = input("\n请选择 [回车确认]: ").strip().lower()

            if choice == 'q':
                print("\n已退出程序")
                sys.exit(0)

            if choice == '':
                print(f"\n[OK] 已确认使用项目: {self._projects[default_project].label}")
                return default_project

            # 尝试解析数字选择
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(project_list):
                    selected = project_list[idx]
                    print(f"\n[OK] 已切换到项目: {self._projects[selected].label}")
                    return selected
                else:
                    print(f"\n[WARN] 无效选择，使用默认项目: {self._projects[default_project].label}")
                    return default_project
            except ValueError:
                print(f"\n[WARN] 无效输入，使用默认项目: {self._projects[default_project].label}")
                return default_project

        except (KeyboardInterrupt, EOFError):
            print("\n\n[WARN] 用户取消，使用默认项目")
            return default_project

    def _detect_project_source(self) -> str:
        """检测项目来源（用于显示）"""
        if os.environ.get('REITS_PROJECT'):
            return "环境变量 REITS_PROJECT"

        for i, arg in enumerate(sys.argv):
            if arg in ('--project', '-p') or arg.startswith('--project='):
                return "命令行参数"

        return "run_config.yaml 配置文件"

    # ==================== 公共接口 ====================

    @classmethod
    def get_instance(
        cls,
        project_name: Optional[str] = None,
        auto_confirm: bool = False,
        silent: bool = False
    ) -> 'ProjectConfigManager':
        """获取配置管理器实例（单例）"""
        if cls._instance is None or project_name:
            cls._instance = cls(project_name, auto_confirm=auto_confirm, silent=silent)
        return cls._instance

    @classmethod
    def auto_select(cls, project_name: Optional[str] = None, silent: bool = True) -> 'ProjectConfigManager':
        """
        自动选择项目（非交互式）

        Usage:
            config = ProjectConfigManager.auto_select()  # 使用默认配置
            config = ProjectConfigManager.auto_select("huazhu")  # 强制指定
        """
        return cls.get_instance(project_name=project_name, auto_confirm=True, silent=silent)

    @classmethod
    def interactive_select(cls) -> 'ProjectConfigManager':
        """
        交互式选择项目

        Usage:
            config = ProjectConfigManager.interactive_select()
        """
        return cls.get_instance(auto_confirm=False, silent=False)

    @property
    def active_project(self) -> str:
        """当前激活的项目名称"""
        return self._active_project

    @property
    def active_project_config(self) -> ProjectConfig:
        """当前激活的项目配置"""
        if self._active_project not in self._projects:
            raise ValueError(
                f"未知的项目: {self._active_project}\n"
                f"可用项目: {list(self._projects.keys())}"
            )
        return self._projects[self._active_project]

    @property
    def run_config(self) -> RunConfig:
        """运行配置"""
        return self._run_config

    def get_data_path(self, filename: Optional[str] = None) -> Path:
        """
        获取数据文件路径

        Args:
            filename: 可选的文件名，返回完整路径；None 则返回数据目录
        """
        base = self._root_dir / self.active_project_config.data_dir
        if filename:
            return base / filename
        return base

    def get_output_path(self, filename: Optional[str] = None, use_latest: bool = False) -> Path:
        """
        获取输出文件路径

        Args:
            filename: 可选的文件名
            use_latest: 是否使用 latest/ 子目录
        """
        base = self._root_dir / self.active_project_config.output_dir
        if use_latest:
            base = base / "latest"
        if filename:
            return base / filename
        return base

    def get_run_output_path(self, run_id: str) -> Path:
        """获取特定运行记录的输出目录"""
        return self._root_dir / self.active_project_config.output_dir / f"run_{run_id}"

    def create_output_dirs(self):
        """创建输出目录结构"""
        output_base = self.get_output_path()
        latest_dir = self.get_output_path(use_latest=True)

        output_base.mkdir(parents=True, exist_ok=True)
        latest_dir.mkdir(parents=True, exist_ok=True)

        if not self._silent:
            print(f"[DIR] 输出目录: {output_base}")
            print(f"[DIR] Latest目录: {latest_dir}")

    def list_projects(self) -> List[str]:
        """列出所有可用项目"""
        return list(self._projects.keys())

    def get_project_info(self, project_name: Optional[str] = None) -> Dict[str, Any]:
        """获取项目详细信息"""
        name = project_name or self._active_project
        if name not in self._projects:
            raise ValueError(f"未知的项目: {name}")

        project = self._projects[name]
        return {
            "name": project.name,
            "label": project.label,
            "asset_types": project.asset_types,
            "data_dir": str(self._root_dir / project.data_dir),
            "output_dir": str(self._root_dir / project.output_dir),
            "description": project.description,
        }

    def print_summary(self):
        """打印当前配置摘要"""
        print("\n" + "=" * 60)
        print("  项目配置摘要")
        print("=" * 60)

        project = self.active_project_config
        print(f"\n[当前项目] {project.label} ({project.name})")
        print(f"   业态类型: {', '.join(project.asset_types)}")
        print(f"   数据目录: {self.get_data_path()}")
        print(f"   输出目录: {self.get_output_path()}")
        print(f"   项目描述: {project.description}")

        print(f"\n[运行配置]")
        print(f"   自动创建目录: {self._run_config.auto_create_dirs}")
        print(f"   保留历史记录: {self._run_config.keep_run_history}")
        print(f"   Latest更新方式: {self._run_config.latest_update_mode}")

        print("\n" + "=" * 60)


# ==================== 便捷函数 ====================

def get_config(
    project_name: Optional[str] = None,
    auto_confirm: bool = True,
    silent: bool = True
) -> ProjectConfigManager:
    """
    获取配置管理器的便捷函数

    Usage:
        from src.core.project_config import get_config

        # 自动模式（推荐用于脚本）
        config = get_config()

        # 交互模式（推荐用于手动运行）
        config = get_config(auto_confirm=False)

        # 强制指定项目
        config = get_config("huazhu")

        # 使用路径
        data_path = config.get_data_path("extracted_params.json")
        output_path = config.get_output_path("dcf_results.json", use_latest=True)
    """
    return ProjectConfigManager.get_instance(
        project_name=project_name,
        auto_confirm=auto_confirm,
        silent=silent
    )


if __name__ == "__main__":
    # 测试交互式选择
    config = ProjectConfigManager.interactive_select()
    config.create_output_dirs()
    config.print_summary()
