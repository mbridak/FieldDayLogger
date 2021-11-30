# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['fielddaylogger.py'],
             pathex=['.'],
             binaries=[('icon/*.png','icon'),
             ('font/*.ttf','font')],
             datas=[('main.ui','.'),
             ('MASTER.SCP','.'),
             ('arrl_sect.dat','.'),
             ('dialog.ui','.'),
             ('settings.ui','.'),
             ('startup.ui','.')
             ],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='fielddaylogger',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False )
