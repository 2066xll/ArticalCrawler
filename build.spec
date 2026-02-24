# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None

# 项目根目录
ROOT = os.path.abspath('.')

a = Analysis(
    ['app.py'],
    pathex=[ROOT],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('frontend', 'frontend'),
        ('static', 'static'),
        ('article_crawler.py', '.'),
        ('data', 'data'),
    ],
    hiddenimports=[
        'flask',
        'jinja2',
        'markupsafe',
        'werkzeug',
        'werkzeug.serving',
        'werkzeug.debug',
        'click',
        'itsdangerous',
        'blinker',
        'requests',
        'bs4',
        'lxml',
        'lxml.etree',
        'lxml.html',
        'dotenv',
        'urllib3',
        'charset_normalizer',
        'certifi',
        'idna',
        'soupsieve',
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
    name='文章抓取',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
