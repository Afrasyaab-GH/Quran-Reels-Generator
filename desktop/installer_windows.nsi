; ============================================================
;  Quran Reels Generator - Windows Installer (NSIS)
;  Build prerequisites:
;    1. Run: pyinstaller desktop/QuranReels.spec --noconfirm
;       (produces dist/QuranReels/)
;    2. Install NSIS: https://nsis.sourceforge.io/Download
;    3. Compile: makensis desktop/installer_windows.nsi
; ============================================================

!define APP_NAME       "Quran Reels Generator"
!define APP_PUBLISHER  "Quran Reels"
!define APP_VERSION    "0.2.4"
!define APP_EXE        "QuranReels.exe"
!define APP_DIST_DIR   "..\dist\QuranReels"
!define APP_REG_KEY    "Software\Microsoft\Windows\CurrentVersion\Uninstall\QuranReels"

Var VIDEOS_DIR

Function .onInit
    StrCpy $VIDEOS_DIR "$VIDEOS\QuranReels"
FunctionEnd

Name        "${APP_NAME}"
OutFile     "..\dist\QuranReels-Setup-${APP_VERSION}.exe"
InstallDir  "$LOCALAPPDATA\Programs\QuranReels"
InstallDirRegKey HKCU "Software\QuranReels" "InstallDir"
RequestExecutionLevel admin       ; Run as Administrator to allow writing to Program Files
SetCompressor /SOLID lzma
ShowInstDetails show
ShowUninstDetails show

!include "MUI2.nsh"

!define MUI_ICON "icon.ico"
!define MUI_UNICON "icon.ico"
!define MUI_ABORTWARNING

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY

; Directory page for Videos Output
!define MUI_DIRECTORYPAGE_VARIABLE $VIDEOS_DIR
!define MUI_DIRECTORYPAGE_TEXT_TOP "Select the directory where downloaded Quran Reels videos will be saved."
!define MUI_DIRECTORYPAGE_TEXT_DESTINATION "Videos Output Directory"
!insertmacro MUI_PAGE_DIRECTORY

!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT "Launch ${APP_NAME}"
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "Arabic"

Section "Main" SEC_MAIN
    SetOutPath "$INSTDIR"
    File /r "${APP_DIST_DIR}\*.*"

    ; Shortcuts
    CreateDirectory "$SMPROGRAMS\${APP_NAME}"
    CreateShortcut  "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}"
    CreateShortcut  "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk"   "$INSTDIR\Uninstall.exe"
    CreateShortcut  "$DESKTOP\${APP_NAME}.lnk"                "$INSTDIR\${APP_EXE}"

    ; Registry: install dir + Add/Remove Programs entry
    WriteRegStr HKCU "Software\QuranReels" "InstallDir" "$INSTDIR"
    WriteRegStr HKCU "Software\QuranReels" "VideosDir" "$VIDEOS_DIR"
    WriteRegStr HKCU "${APP_REG_KEY}" "DisplayName"     "${APP_NAME}"
    WriteRegStr HKCU "${APP_REG_KEY}" "DisplayVersion"  "${APP_VERSION}"
    WriteRegStr HKCU "${APP_REG_KEY}" "Publisher"       "${APP_PUBLISHER}"
    WriteRegStr HKCU "${APP_REG_KEY}" "DisplayIcon"     "$INSTDIR\${APP_EXE}"
    WriteRegStr HKCU "${APP_REG_KEY}" "UninstallString" "$INSTDIR\Uninstall.exe"
    WriteRegDWORD HKCU "${APP_REG_KEY}" "NoModify" 1
    WriteRegDWORD HKCU "${APP_REG_KEY}" "NoRepair" 1

    WriteUninstaller "$INSTDIR\Uninstall.exe"
SectionEnd

Section "Uninstall"
    Delete "$DESKTOP\${APP_NAME}.lnk"
    RMDir /r "$SMPROGRAMS\${APP_NAME}"
    RMDir /r "$INSTDIR"
    DeleteRegKey HKCU "${APP_REG_KEY}"
    DeleteRegKey HKCU "Software\QuranReels"

    ; Note: user data in %APPDATA%\QuranReels is intentionally preserved
    MessageBox MB_YESNO "Also delete your saved videos and settings in %APPDATA%\QuranReels?" IDNO +3
        RMDir /r "$APPDATA\QuranReels"
SectionEnd
