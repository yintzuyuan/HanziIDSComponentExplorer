#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IDS 資料庫建置 CLI

用法：
    python scripts/build_ids.py              # 建置到 dist/
    python scripts/build_ids.py --copy       # 建置並複製到外掛目錄
    python scripts/build_ids.py --download   # 下載資料來源並建置
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

# 將 scripts 目錄加入路徑
sys.path.insert(0, str(Path(__file__).parent))

from ids_generator import IDSGenerator


def download_data_sources() -> None:
    """下載資料來源（用於本地開發）"""
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    # CHISE IDS
    chise_dir = data_dir / "chise-ids"
    if not chise_dir.exists():
        print("下載 CHISE IDS...")
        subprocess.run(
            [
                "git",
                "clone",
                "--depth=1",
                "https://github.com/chise/ids.git",
                str(chise_dir),
            ],
            check=True,
        )
    else:
        print("更新 CHISE IDS...")
        subprocess.run(["git", "-C", str(chise_dir), "pull"], check=True)

    # CNS11643
    cns_dir = data_dir / "cns11643"
    if not cns_dir.exists():
        print("下載 CNS11643...")
        subprocess.run(
            [
                "git",
                "clone",
                "--depth=1",
                "https://github.com/yintzuyuan/CNS11643-OpenData.git",
                str(cns_dir),
            ],
            check=True,
        )
    else:
        print("更新 CNS11643...")
        subprocess.run(["git", "-C", str(cns_dir), "pull"], check=True)


def copy_to_plugin(pdata_path: Path) -> None:
    """複製 pdata 到外掛目錄"""
    plugin_data_dir = Path(
        "HanziIDSComponentExplorer.glyphsPlugin/Contents/Resources/data"
    )

    if not plugin_data_dir.exists():
        print(f"警告：外掛目錄不存在：{plugin_data_dir}")
        return

    dest = plugin_data_dir / "ids.pdata"
    shutil.copy2(pdata_path, dest)
    print(f"已複製到：{dest}")


def main() -> None:
    parser = argparse.ArgumentParser(description="IDS 資料庫建置工具")
    parser.add_argument(
        "--download",
        action="store_true",
        help="下載資料來源（用於本地開發）",
    )
    parser.add_argument(
        "--copy",
        action="store_true",
        help="建置後複製到外掛目錄",
    )

    args = parser.parse_args()

    # 下載資料來源
    if args.download:
        download_data_sources()

    # 檢查資料來源是否存在
    chise_dir = Path("data/chise-ids")
    if not chise_dir.exists():
        print("錯誤：找不到 CHISE IDS 資料")
        print("請執行：python scripts/build_ids.py --download")
        sys.exit(1)

    # 建置
    generator = IDSGenerator()
    pdata_path = generator.build()

    # 複製到外掛目錄
    if args.copy:
        copy_to_plugin(pdata_path)

    print("完成！")


if __name__ == "__main__":
    main()
