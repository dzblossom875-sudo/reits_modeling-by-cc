"""
Dashboard 启动器
用法:
    python scripts/launch.py                      # 启动当前 active_project 的 noi_dashboard
    python scripts/launch.py noi                  # 同上
    python scripts/launch.py dcf                  # 启动 dcf_results_dashboard
    python scripts/launch.py --project huazhu noi # 指定项目启动
    python scripts/launch.py list                 # 列出所有端口分配
"""

import sys
import os
import subprocess
import yaml
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

_ROOT = Path(__file__).parent.parent

DASHBOARD_SCRIPTS = {
    "noi": "scripts/noi_dashboard.py",
    "dcf": "scripts/dcf_results_dashboard.py",
}


def load_config():
    with open(_ROOT / "run_config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_port(cfg, project_name, dashboard_type):
    ports = cfg["projects"][project_name].get("ports", {})
    key = f"{dashboard_type}_dashboard"
    return ports.get(key)


def list_all(cfg):
    print("\n端口分配一览：")
    print(f"{'项目':<20} {'Dashboard':<15} {'端口'}")
    print("-" * 45)
    for proj, data in cfg["projects"].items():
        label = data.get("label", proj)
        for dtype in ["noi", "dcf"]:
            port = data.get("ports", {}).get(f"{dtype}_dashboard", "未配置")
            print(f"{label:<20} {dtype+'_dashboard':<15} {port}")
    print()


def main():
    args = sys.argv[1:]

    # 解析 --project
    project_name = None
    if "--project" in args:
        idx = args.index("--project")
        project_name = args[idx + 1]
        args = args[:idx] + args[idx + 2:]

    dashboard_type = args[0] if args else "noi"

    cfg = load_config()

    if dashboard_type == "list":
        list_all(cfg)
        return

    if dashboard_type not in DASHBOARD_SCRIPTS:
        print(f"未知 dashboard 类型: {dashboard_type}，可选: {list(DASHBOARD_SCRIPTS.keys())}")
        sys.exit(1)

    if not project_name:
        project_name = cfg.get("active_project", "")

    if project_name not in cfg["projects"]:
        print(f"未知项目: {project_name}，可选: {list(cfg['projects'].keys())}")
        sys.exit(1)

    port = get_port(cfg, project_name, dashboard_type)
    if not port:
        print(f"项目 {project_name} 未配置 {dashboard_type}_dashboard 端口")
        sys.exit(1)

    script = _ROOT / DASHBOARD_SCRIPTS[dashboard_type]
    label = cfg["projects"][project_name].get("label", project_name)

    print(f"\n启动 [{label}] {dashboard_type}_dashboard → http://localhost:{port}")
    print(f"脚本: {script.name}  端口: {port}\n")

    env = os.environ.copy()
    env["REITS_PROJECT"] = project_name

    subprocess.run([
        sys.executable, "-m", "streamlit", "run", str(script),
        "--server.port", str(port),
        "--server.headless", "false",
    ], env=env)


if __name__ == "__main__":
    main()
