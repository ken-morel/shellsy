;NSIS Modern User Interface
;Welcome/Finish Page Example Script
;Written by Joost Verburg

;--------------------------------
;Include Modern UI

  !include "MUI2.nsh"

;--------------------------------
;General

  ;Name and file
  Name "Shellsy"
  OutFile "build/windows/shellsy_windows8_amd64.exe"
  Unicode True
  Caption "Shellsy Setup"

  ;Default installation folder
  InstallDir "$LOCALAPPDATA\shellsy"

  ;Get installation folder from registry if available
  InstallDirRegKey HKCU "Software\shellsy" ""

  ;Request application privileges for Windows Vista
  RequestExecutionLevel admin

;--------------------------------
;Variables

  ;Var StartMenuFolder

;--------------------------------

;Interface Settings

  !define MUI_ICON "shellsy.ico"
  !define MUI_UICON "shellsy.ico"

  !define MUI_HEADERIMAGE
  !define MUI_HEADERIMAGE_BITMAP "header.ico"
  !define MUI_HEADERIMAGE_UNBITMAP "header.ico"

  !define MUI_BGCOLOR "112233"
  !define MUI_TEXTCOLOR "FFFFFF"
  !define MUI_FINISHPAGE_LINK_COLOR "9922FF"
  !define MUI_LICENSEPAGE_BGCOLOR "112233"
  !define MUI_DIRECTORYPAGE_BGCOLOR "112233"
  !define MUI_STARTMENUPAGE_BGCOLOR "112233"
  !define MUI_INSTFILESPAGE_COLORS "FFFFFF 112233"
  !define MUI_INSTFILESPAGE_PROGRESSBAR "colored"


  !define MUI_HEADER_TRANSPARENT_TEXT
  !define MUI_WELCOMEPAGE_TEXT "Hy pythonista, Welcome to shellsy setup, hope goes on well! if not, please issue"
  !define MUI_WELCOMEPAGE_TITLE "Shellsy setup"

  !define MUI_FINISHPAGE_TITLE "Shellsy setup complete!"
  !define MUI_FINISHPAGE_TEXT "Thanks for installing shellsy, good coding and let the rest of your day go on better!"

  !define MUI_FINISHPAGE_RUN "$INSTDIR\shellsy.exe"
  !define MUI_FINISHPAGE_RUN_TEXT "Run shellsy >"

  !define MUI_FINISHPAGE_SHOWREADME "https://github.com/ken-morel/shellsy/"

  !define MUI_FINISHPAGE_LINK "Shellsy documentation"
  !define MUI_FINISHPAGE_LINK_LOCATION "https://shellsy.vercel.app"

  !define MUI_ABORTWARNING
  !define MUI_ABORTWARNING_TEXT "Sure you want to stop installing shellsy?"

  !define MUI_STARTMENUPAGE_REGISTRY_ROOT "HKCU"
  !define MUI_STARTMENUPAGE_REGISTRY_KEY "Software\shellsy"
  !define MUI_STARTMENUPAGE_REGISTRY_VALUENAME "shellsy"


;--------------------------------
;Pages

  !insertmacro MUI_PAGE_WELCOME
  !insertmacro MUI_PAGE_LICENSE "LICENSE"
  !insertmacro MUI_PAGE_COMPONENTS
  !insertmacro MUI_PAGE_DIRECTORY

  ;!insertmacro MUI_PAGE_STARTMENU Application "$StartMenuFolder"

  !insertmacro MUI_PAGE_INSTFILES
  !insertmacro MUI_PAGE_FINISH

  !insertmacro MUI_UNPAGE_WELCOME
  !insertmacro MUI_UNPAGE_CONFIRM
  !insertmacro MUI_UNPAGE_INSTFILES
  !insertmacro MUI_UNPAGE_FINISH

;--------------------------------
;Languages

  !insertmacro MUI_LANGUAGE "English"

;--------------------------------
;Installer Sections

Section "Main Section" SecMain

  ;ADD YOUR OWN FILES HERE...

  


  SetShellVarContext all
  ; Check if the path exists in the current PATH
  ; nsExec::Exec 'echo %PATH% | findstr /C:"%INSTDIR%"'
  ; Pop $0

  ; ${If} $0 == 0
      ; Path not found, add it to PATH
      nsExec::Exec 'setx PATH "%PATH%;%INSTDIR%"'
  ; ${Else}
  ;     ; Path already exists, display a message or take appropriate action
  ;     MessageBox MB_ICONINFORMATION "The path $INSTDIR is already in the PATH."
  ; ${EndIf}

  ;Store installation folder
  WriteRegStr HKCU "Software\shellsy" "" $INSTDIR

  ;Create uninstaller
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  ;!insertmacro MUI_STARTMENU_WRITE_BEGIN Application

    ;Create shortcuts
  CreateShortcut "$SMPROGRAMS\shellsy.lnk" "$INSTDIR\shellsy.exe" "" "$INSTDIR\shellsy.ico"
  CreateDirectory "$SMPROGRAMS\shellsy"
  SetOutPath "$SMPROGRAMS\shellsy"
  CreateShortcut "$SMPROGRAMS\shellsy\Uninstall.lnk" "$INSTDIR\Uninstall.exe" "" "$INSTDIR\shellsy.ico"


  CreateShortcut "$DESKTOP\shellsy.lnk" "$INSTDIR\shellsy.exe" "" "$INSTDIR\shellsy.ico"

  ;!insertmacro MUI_STARTMENU_WRITE_END

SectionEnd

;--------------------------------
;Descriptions

  ;Language strings
  LangString DESC_SecMain ${LANG_ENGLISH} "Shellsy Core"

  ;Assign language strings to sections
  !insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
    !insertmacro MUI_DESCRIPTION_TEXT ${SecMain} $(DESC_SecMain)
  !insertmacro MUI_FUNCTION_DESCRIPTION_END

;--------------------------------
;Uninstaller Section

Section "Uninstall"

  ;ADD YOUR OWN FILES HERE...

  Delete "$INSTDIR\Uninstall.exe"

  RMDir "$INSTDIR"

  ;!insertmacro MUI_STARTMENU_GETFOLDER Application $StartMenuFolder

  Delete "$SMPROGRAMS\shellsy\Uninstall.lnk"
  RMDir "$SMPROGRAMS\shellsy"

  DeleteRegKey /ifempty HKCU "Software\shellsy"

SectionEnd
