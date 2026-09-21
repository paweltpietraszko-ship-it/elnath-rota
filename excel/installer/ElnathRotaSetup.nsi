; ROTA-EXCEL-INSTALLER-AUTOMATION (2026-09-21, OWNER: "dzisiejsze czasy,
; czlowiek klika pobierz i magia sie dzieje... instalator sam sprawdza
; wszystko i ewentualnie jesli musi to pyta gdzie zapisac").
;
; Replaces the manual excel/INSTALL.md steps (copy .xlam by hand, Excel
; Options -> Add-ins -> Browse dialog, running the RotaConfigure macro by
; hand via Alt+F8) with a single double-click installer. Built with NSIS
; (Nullsoft Scriptable Install System, zlib/libpng license -- free for
; commercial use without restriction, unlike Inno Setup 6.5+ which now
; requires a paid commercial license). Adopted as-is, no custom installer
; engine written here.
;
; Two mechanisms this script relies on, both real Excel/VBA behavior, not
; anything invented for this project:
;   1. %APPDATA%\Microsoft\Excel\XLSTART is a default TRUSTED location
;      that Excel auto-loads every file from at startup -- dropping the
;      .xlam there is a complete substitute for the manual "File ->
;      Options -> Add-ins -> Browse..." dialog, with no macro-security
;      warning (XLSTART is trusted by default) and no Office-version-
;      numbered registry key to get wrong (HKCU\...\Office\16.0\Excel\
;      Options\OPENx varies per Office version; XLSTART does not).
;   2. The add-in's own RotaConfigure macro (excel/src/elnath_rota_addin.bas)
;      persists via VBA's SaveSetting/GetSetting, which is documented to
;      read/write HKEY_CURRENT_USER\Software\VB and VBA Program
;      Settings\<AppName>\<Section>\<Key> -- writing those same registry
;      values here is equivalent to the user having already run
;      RotaConfigure by hand.
;
; Build (on any machine with NSIS installed -- winget install NSIS.NSIS,
; or https://nsis.sourceforge.io/Download, both free):
;   makensis excel\installer\ElnathRotaSetup.nsi
; produces excel\installer\ElnathRotaSetup.exe, the single file to hand
; to a coordinator.

!include "MUI2.nsh"
!include "nsDialogs.nsh"
!include "LogicLib.nsh"

; ROTA-EXCEL-INSTALLER-AUTOMATION: single shared Rota instance today --
; change this one line and rebuild if the service ever moves. The wizard
; still shows it, editable, so a coordinator pointed at a different
; environment (or a future multi-instance setup) is never stuck.
!define SERVICE_URL_DEFAULT "https://elnath-rota-production.up.railway.app/api"

Name "Elnath Rota — dodatek do Excela"
OutFile "ElnathRotaSetup.exe"
InstallDir "$DOCUMENTS\Elnath Rota"
RequestExecutionLevel user
ShowInstDetails show
ShowUninstDetails show

!define MUI_ABORTWARNING

!insertmacro MUI_PAGE_WELCOME
Page custom AccessKeyPageCreate AccessKeyPageLeave
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "Polish"

Var AccessKeyEdit
Var AccessKeyValue
Var ServiceUrlEdit
Var ServiceUrlValue

Function AccessKeyPageCreate
    !insertmacro MUI_HEADER_TEXT "Klucz dostępu" "Dane potrzebne, żeby dodatek połączył się z Twoją Rotą"

    nsDialogs::Create 1018
    Pop $0
    ${If} $0 == error
        Abort
    ${EndIf}

    ${NSD_CreateLabel} 0 0 100% 24u "Wklej klucz dostępu do Elnath Rota, wydany przez administratora (e-mail z kluczem):"
    Pop $0

    ${NSD_CreateText} 0 26u 100% 13u ""
    Pop $AccessKeyEdit

    ${NSD_CreateLabel} 0 48u 100% 24u "Adres usługi Rota (zwykle nie trzeba zmieniać):"
    Pop $0

    ${NSD_CreateText} 0 74u 100% 13u "${SERVICE_URL_DEFAULT}"
    Pop $ServiceUrlEdit

    nsDialogs::Show
FunctionEnd

Function AccessKeyPageLeave
    ${NSD_GetText} $AccessKeyEdit $AccessKeyValue
    ${NSD_GetText} $ServiceUrlEdit $ServiceUrlValue
    ${If} $AccessKeyValue == ""
        MessageBox MB_ICONEXCLAMATION "Klucz dostępu jest wymagany. Poproś administratora Roty o klucz i wklej go tutaj."
        Abort
    ${EndIf}
    ${If} $ServiceUrlValue == ""
        StrCpy $ServiceUrlValue "${SERVICE_URL_DEFAULT}"
    ${EndIf}
FunctionEnd

Section "Dodatek Elnath Rota" SEC_ADDIN
    SetOutPath "$APPDATA\Microsoft\Excel\XLSTART"
    File "..\ELNATH_ROTA_ADDIN.xlam"

    SetOutPath "$INSTDIR"
    File "..\ELNATH_ROTA_TEMPLATE.xlsx"

    ; Equivalent to running RotaConfigure by hand (VBA SaveSetting target).
    WriteRegStr HKCU "Software\VB and VBA Program Settings\ElnathRota\Config" "ServiceUrl" "$ServiceUrlValue"
    WriteRegStr HKCU "Software\VB and VBA Program Settings\ElnathRota\Config" "AccessKey" "$AccessKeyValue"

    WriteRegStr HKCU "Software\ElnathRota\Installer" "InstallDir" "$INSTDIR"
    WriteUninstaller "$INSTDIR\Odinstaluj.exe"
SectionEnd

Function .onInstSuccess
    MessageBox MB_OK|MB_ICONINFORMATION "Gotowe. Otwórz plik grafiku ($INSTDIR\ELNATH_ROTA_TEMPLATE.xlsx) w Excelu — dodatek załaduje się automatycznie."
FunctionEnd

Section "Uninstall"
    Delete "$APPDATA\Microsoft\Excel\XLSTART\ELNATH_ROTA_ADDIN.xlam"
    Delete "$INSTDIR\ELNATH_ROTA_TEMPLATE.xlsx"
    Delete "$INSTDIR\Odinstaluj.exe"
    RMDir "$INSTDIR"
    DeleteRegKey HKCU "Software\VB and VBA Program Settings\ElnathRota"
    DeleteRegKey HKCU "Software\ElnathRota"
SectionEnd
