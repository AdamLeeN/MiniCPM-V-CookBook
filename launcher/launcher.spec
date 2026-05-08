# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from pathlib import Path

# 项目根目录
base_dir = Path(SPECPATH).parent
launcher_dir = Path(SPECPATH)

block_cipher = None

# 分析入口文件
a = Analysis(
    [str(launcher_dir / 'main.py')],
    pathex=[
        str(base_dir),
        str(launcher_dir),
    ],
    binaries=[],
    datas=[
        # 嵌入脚本
        (str(launcher_dir / 'scripts' / 'setup_wsl.sh'), 'scripts'),
        (str(launcher_dir / 'scripts' / 'start_services.sh'), 'scripts'),
        (str(launcher_dir / 'scripts' / 'stop_services.sh'), 'scripts'),
        # 嵌入资源
        (str(base_dir / 'demo' / 'web_demo' / 'WebRTC_Demo'), 'embedded/WebRTC_Demo'),
    ],
    hiddenimports=[
        'PyQt6.sip',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'yaml',
        'psutil',
        'requests',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='MiniCPM-o-Launcher',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 无控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon=str(launcher_dir / 'assets' / 'icon.ico'),
)
