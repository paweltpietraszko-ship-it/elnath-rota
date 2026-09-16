Attribute VB_Name = "ElnathRotaAddin"
' ROTA-EXCEL-VBA-ENGINE-ADAPTER brief.md sections 5/6/7/9/11: thin VBA
' adapter over the external Excel API (api/routers/excel_external.py).
' This module owns NO scheduling logic -- it only reads the standard
' template's named ranges/tables, calls the API, and writes back the
' server's own answer. It never invents a status, a work code, or a
' blocker message; every one of those comes verbatim from the response.
Option Explicit

' --- one-time configuration (excel/INSTALL.md) ---------------------------
' Stored per-Windows-user via SaveSetting/GetSetting (registry), never
' inside the distributed .xlsx template -- the same file can be handed to
' someone else without leaking a colleague's access key.
Private Const CONFIG_APP As String = "ElnathRota"
Private Const CONFIG_SECTION As String = "Config"

Public Sub RotaConfigure()
    Dim currentUrl As String, currentKey As String
    currentUrl = GetSetting(CONFIG_APP, CONFIG_SECTION, "ServiceUrl", "")
    currentKey = GetSetting(CONFIG_APP, CONFIG_SECTION, "AccessKey", "")

    Dim newUrl As String, newKey As String
    newUrl = InputBox("Adres usługi Rota (np. https://twoja-rota.up.railway.app):", "Konfiguracja Elnath Rota", currentUrl)
    If newUrl = "" Then Exit Sub
    newKey = InputBox("Klucz dostępu (otrzymany od administratora):", "Konfiguracja Elnath Rota", IIf(currentKey = "", "", "********"))
    If newKey = "" Then Exit Sub

    SaveSetting CONFIG_APP, CONFIG_SECTION, "ServiceUrl", newUrl
    If newKey <> "********" Then
        SaveSetting CONFIG_APP, CONFIG_SECTION, "AccessKey", newKey
    End If
    MsgBox "Zapisano konfigurację Elnath Rota.", vbInformation
End Sub

Private Function ServiceUrl() As String
    ServiceUrl = GetSetting(CONFIG_APP, CONFIG_SECTION, "ServiceUrl", "")
End Function

Private Function AccessKey() As String
    AccessKey = GetSetting(CONFIG_APP, CONFIG_SECTION, "AccessKey", "")
End Function

' --- HTTP -------------------------------------------------------------

Private Function HttpCall(ByVal method As String, ByVal path As String, ByVal body As String) As String
    ' Returns the raw JSON response body on 2xx; raises a VBA error
    ' (caught by callers as a plain "network/auth" blocker per brief.md
    ' section 9) on anything else, including a transport failure.
    If ServiceUrl() = "" Or AccessKey() = "" Then
        Err.Raise vbObjectError + 1, "ElnathRotaAddin", "Dodatek nie jest jeszcze skonfigurowany. Uruchom RotaConfigure."
    End If

    Dim http As Object
    Set http = CreateObject("WinHttp.WinHttpRequest.5.1")
    http.Open method, ServiceUrl() & path, False
    http.SetRequestHeader "Content-Type", "application/json"
    http.SetRequestHeader "Authorization", "Bearer " & AccessKey()
    On Error GoTo TransportFailed
    If body = "" Then
        http.Send
    Else
        http.Send body
    End If
    On Error GoTo 0

    If http.Status >= 200 And http.Status < 300 Then
        HttpCall = http.ResponseText
        Exit Function
    End If

    ' brief.md section 9: a controlled-blocker response still has a JSON
    ' body with a "detail"/"blocker" field -- surface it verbatim rather
    ' than a bare status code.
    Dim detail As String
    detail = JsonExtractString(http.ResponseText, "detail")
    If detail = "" Then detail = JsonExtractString(http.ResponseText, "message")
    If detail = "" Then detail = "Serwer zwrócił błąd (" & http.Status & ")."
    Err.Raise vbObjectError + 2, "ElnathRotaAddin", detail
    Exit Function

TransportFailed:
    Err.Raise vbObjectError + 3, "ElnathRotaAddin", "Brak połączenia z usługą Rota. Sprawdź internet i spróbuj ponownie."
End Function

' --- reading the standard template (brief.md section 3) ----------------

Private Function SiteId() As String
    SiteId = Trim(ActiveWorkbook.Names("ROTA_SITE_ID").RefersToRange.Value)
End Function

Private Function MonthValue() As String
    Dim raw As Variant
    raw = ActiveWorkbook.Names("ROTA_MONTH").RefersToRange.Value
    MonthValue = Format(raw, "yyyy-mm-01")
End Function

Private Function ListObjectByName(ByVal tableName As String) As ListObject
    Dim ws As Worksheet
    For Each ws In ActiveWorkbook.Worksheets
        On Error Resume Next
        Set ListObjectByName = ws.ListObjects(tableName)
        On Error GoTo 0
        If Not ListObjectByName Is Nothing Then Exit Function
    Next ws
End Function

Private Function BuildTargetHoursJson() As String
    Dim lo As ListObject
    Set lo = ListObjectByName("ROTA_EMPLOYEES")
    Dim parts As String, r As Long
    Dim colEmp As Long, colTarget As Long
    colEmp = lo.ListColumns("employee_id").Index
    colTarget = lo.ListColumns("target_hours").Index
    If Not lo.DataBodyRange Is Nothing Then
        For r = 1 To lo.DataBodyRange.Rows.Count
            Dim empId As String, hours As Variant
            empId = Trim(lo.DataBodyRange.Cells(r, colEmp).Value)
            hours = lo.DataBodyRange.Cells(r, colTarget).Value
            If empId <> "" And IsNumeric(hours) Then
                If parts <> "" Then parts = parts & ","
                parts = parts & "{""employee_id"":" & JsonString(empId) & ",""target_hours"":" & CLng(hours) & "}"
            End If
        Next r
    End If
    BuildTargetHoursJson = "[" & parts & "]"
End Function

Private Function BuildAvailabilityJson() As String
    Dim lo As ListObject
    Set lo = ListObjectByName("ROTA_AVAILABILITY")
    Dim parts As String, r As Long
    If Not lo Is Nothing And Not lo.DataBodyRange Is Nothing Then
        Dim cId As Long, cEmp As Long, cKind As Long, cStart As Long, cEnd As Long
        Dim cStartT As Long, cEndT As Long, cDel As Long, cActive As Long
        cId = lo.ListColumns("availability_id").Index
        cEmp = lo.ListColumns("employee_id").Index
        cKind = lo.ListColumns("kind").Index
        cStart = lo.ListColumns("start_date").Index
        cEnd = lo.ListColumns("end_date").Index
        cStartT = lo.ListColumns("start_time").Index
        cEndT = lo.ListColumns("end_time").Index
        cDel = lo.ListColumns("delegation_hours").Index
        cActive = lo.ListColumns("active").Index
        For r = 1 To lo.DataBodyRange.Rows.Count
            Dim row As Range
            Set row = lo.DataBodyRange.Rows(r)
            Dim availId As String
            availId = Trim(row.Cells(1, cId).Value)
            If availId <> "" Then
                If parts <> "" Then parts = parts & ","
                parts = parts & "{" & _
                    """availability_id"":" & JsonString(availId) & "," & _
                    """employee_id"":" & JsonString(Trim(row.Cells(1, cEmp).Value)) & "," & _
                    """kind"":" & JsonString(Trim(row.Cells(1, cKind).Value)) & "," & _
                    """start_date"":" & JsonString(Format(row.Cells(1, cStart).Value, "yyyy-mm-dd")) & "," & _
                    """end_date"":" & JsonString(Format(row.Cells(1, cEnd).Value, "yyyy-mm-dd")) & "," & _
                    """start_time"":" & JsonOptionalTime(row.Cells(1, cStartT).Value) & "," & _
                    """end_time"":" & JsonOptionalTime(row.Cells(1, cEndT).Value) & "," & _
                    """delegation_hours"":" & JsonOptionalInt(row.Cells(1, cDel).Value) & "," & _
                    """active"":" & IIf(row.Cells(1, cActive).Value, "true", "false") & _
                    "}"
            End If
        Next r
    End If
    BuildAvailabilityJson = "[" & parts & "]"
End Function

Private Function BuildMonthlyInputJson() As String
    BuildMonthlyInputJson = "{""site_id"":" & JsonString(SiteId()) & "," & _
        """month"":" & JsonString(MonthValue()) & "," & _
        """target_hours"":" & BuildTargetHoursJson() & "," & _
        """availability"":" & BuildAvailabilityJson() & "}"
End Function

' --- the three coordinator actions (brief.md section 5) -----------------

Public Sub RotaPlan()
    RunPlanningCall "/external/excel/plan", "Przelicz"
End Sub

Public Sub RotaShowOtherVariant()
    RunPlanningCall "/external/excel/replan", "Pokaż inny wariant"
End Sub

Private Sub RunPlanningCall(ByVal path As String, ByVal actionLabel As String)
    On Error GoTo Failed
    Dim responseJson As String
    responseJson = HttpCall("POST", path, BuildMonthlyInputJson())
    WriteCandidates responseJson
    Dim status As String
    status = JsonExtractString(responseJson, "status")
    If status = "FEASIBLE" Then
        MsgBox "Gotowe -- zobacz propozycje w tabeli Kandydaci i wybierz jedną, a potem uruchom ""Użyj tego grafiku"".", vbInformation, actionLabel
    Else
        Dim message As String
        message = JsonExtractString(responseJson, "message")
        If message = "" Then message = "Brak propozycji grafiku."
        MsgBox message, vbExclamation, actionLabel
    End If
    Exit Sub
Failed:
    MsgBox Err.Description, vbCritical, actionLabel
End Sub

Public Sub RotaUseSelectedCandidate()
    On Error GoTo Failed
    Dim candidateId As String
    candidateId = Trim(ActiveWorkbook.Names("ROTA_SELECTED_CANDIDATE_ID").RefersToRange.Value)
    If candidateId = "" Then
        MsgBox "Najpierw wybierz kandydata w tabeli Kandydaci (wpisz jego identyfikator w komórce wyboru).", vbExclamation
        Exit Sub
    End If
    Dim payload As String
    payload = "{""site_id"":" & JsonString(SiteId()) & ",""month"":" & JsonString(MonthValue()) & _
        ",""candidate_id"":" & JsonString(candidateId) & "}"
    HttpCall "POST", "/external/excel/select-candidate", payload
    RotaRefreshSchedule
    MsgBox "Grafik zaakceptowany i wpisany do arkusza wyniku.", vbInformation, "Użyj tego grafiku"
    Exit Sub
Failed:
    MsgBox Err.Description, vbCritical, "Użyj tego grafiku"
End Sub

Public Sub RotaRefreshSchedule()
    On Error GoTo Failed
    Dim responseJson As String
    responseJson = HttpCall("GET", "/external/excel/schedule/" & SiteId() & "/" & MonthValue(), "")
    WriteScheduleOutput responseJson
    Exit Sub
Failed:
    ' brief.md section 9/11: a failed refresh must never blank out an
    ' already-written ROTA_SCHEDULE_OUTPUT -- WriteScheduleOutput is only
    ' ever called after a successful response, so simply not calling it
    ' here already satisfies "output area unchanged on error".
    MsgBox Err.Description, vbCritical, "Odśwież grafik"
End Sub

' --- writing results back into the template (brief.md section 3.4/3.5) --
' Both write helpers build their new rows in memory and only replace the
' table's DataBodyRange after every row parsed successfully -- brief.md
' section 3.5/11: never a partially-overwritten table.

Private Sub WriteCandidates(ByVal responseJson As String)
    Dim lo As ListObject
    Set lo = ListObjectByName("ROTA_CANDIDATES")
    Dim candidatesJson As String
    candidatesJson = JsonExtractArray(responseJson, "candidates")
    Dim newRows As Collection
    Set newRows = New Collection
    Dim candidateItems As Collection
    Set candidateItems = JsonSplitArrayItems(candidatesJson)
    Dim ci As Variant
    For Each ci In candidateItems
        Dim candidateId As String, candidateNo As String
        candidateId = JsonExtractString(CStr(ci), "candidate_id")
        candidateNo = JsonExtractString(CStr(ci), "candidate_no")
        Dim rowsJson As String
        rowsJson = JsonExtractArray(CStr(ci), "rows")
        Dim rowItems As Collection
        Set rowItems = JsonSplitArrayItems(rowsJson)
        Dim ri As Variant
        For Each ri In rowItems
            newRows.Add Array(candidateId, candidateNo, JsonExtractString(CStr(ri), "employee_id"), _
                JsonExtractString(CStr(ri), "pseudonym"), JsonExtractStringArray(CStr(ri), "days"), _
                JsonExtractString(CStr(ri), "total_hours"))
        Next ri
    Next ci
    ReplaceTableRows lo, newRows, True
End Sub

Private Sub WriteScheduleOutput(ByVal responseJson As String)
    Dim lo As ListObject
    Set lo = ListObjectByName("ROTA_SCHEDULE_OUTPUT")
    Dim rowsJson As String
    rowsJson = JsonExtractArray(responseJson, "rows")
    Dim newRows As Collection
    Set newRows = New Collection
    Dim rowItems As Collection
    Set rowItems = JsonSplitArrayItems(rowsJson)
    Dim ri As Variant
    For Each ri In rowItems
        newRows.Add Array(JsonExtractString(CStr(ri), "employee_id"), JsonExtractString(CStr(ri), "pseudonym"), _
            JsonExtractStringArray(CStr(ri), "days"), JsonExtractString(CStr(ri), "total_hours"))
    Next ri
    ReplaceTableRows lo, newRows, False
End Sub

Private Sub ReplaceTableRows(ByVal lo As ListObject, ByVal newRows As Collection, ByVal hasCandidateColumns As Boolean)
    If Not lo.DataBodyRange Is Nothing Then lo.DataBodyRange.Delete
    Dim r As Long
    For r = 1 To newRows.Count
        Dim item As Variant
        item = newRows(r)
        lo.ListRows.Add
        Dim dayValues As Variant
        Dim baseCol As Long
        If hasCandidateColumns Then
            lo.DataBodyRange.Cells(r, lo.ListColumns("candidate_id").Index).Value = item(0)
            lo.DataBodyRange.Cells(r, lo.ListColumns("candidate_no").Index).Value = item(1)
            lo.DataBodyRange.Cells(r, lo.ListColumns("employee_id").Index).Value = item(2)
            lo.DataBodyRange.Cells(r, lo.ListColumns("pseudonym").Index).Value = item(3)
            dayValues = item(4)
            lo.DataBodyRange.Cells(r, lo.ListColumns("total_hours").Index).Value = CLng(item(5))
        Else
            lo.DataBodyRange.Cells(r, lo.ListColumns("employee_id").Index).Value = item(0)
            lo.DataBodyRange.Cells(r, lo.ListColumns("pseudonym").Index).Value = item(1)
            dayValues = item(2)
            lo.DataBodyRange.Cells(r, lo.ListColumns("total_hours").Index).Value = CLng(item(3))
        End If
        Dim d As Long
        For d = 0 To UBound(dayValues)
            Dim colName As String
            colName = "day_" & Format(d + 1, "00")
            On Error Resume Next
            lo.DataBodyRange.Cells(r, lo.ListColumns(colName).Index).Value = dayValues(d)
            On Error GoTo 0
        Next d
    Next r
End Sub

' --- minimal JSON helpers -------------------------------------------
' Purpose-built for this fixed, documented contract (TEMPLATE_CONTRACT.md)
' -- not a general-purpose JSON library. VBA has no native JSON support.

Private Function JsonString(ByVal s As String) As String
    Dim escaped As String
    escaped = Replace(s, "\", "\\")
    escaped = Replace(escaped, """", "\""")
    JsonString = """" & escaped & """"
End Function

Private Function JsonOptionalTime(ByVal v As Variant) As String
    If IsEmpty(v) Or v = "" Then
        JsonOptionalTime = "null"
    Else
        JsonOptionalTime = JsonString(Format(v, "hh:mm"))
    End If
End Function

Private Function JsonOptionalInt(ByVal v As Variant) As String
    If IsEmpty(v) Or v = "" Or Not IsNumeric(v) Then
        JsonOptionalInt = "null"
    Else
        JsonOptionalInt = CStr(CLng(v))
    End If
End Function

Private Function JsonExtractString(ByVal json As String, ByVal key As String) As String
    ' Returns the raw value text for "key": <value> whether the value is a
    ' quoted string, a number, or null -- good enough for this module's
    ' own fixed, flat response fields.
    Dim needle As String
    needle = """" & key & """:"
    Dim p As Long
    p = InStr(json, needle)
    If p = 0 Then Exit Function
    Dim start As Long
    start = p + Len(needle)
    Do While Mid(json, start, 1) = " "
        start = start + 1
    Loop
    If Mid(json, start, 1) = """" Then
        Dim endPos As Long
        endPos = start + 1
        Do While endPos <= Len(json)
            If Mid(json, endPos, 1) = "\" Then
                endPos = endPos + 2
            ElseIf Mid(json, endPos, 1) = """" Then
                Exit Do
            Else
                endPos = endPos + 1
            End If
        Loop
        JsonExtractString = Mid(json, start + 1, endPos - start - 1)
        JsonExtractString = Replace(JsonExtractString, "\""", """")
        JsonExtractString = Replace(JsonExtractString, "\\", "\")
    ElseIf Mid(json, start, 4) = "null" Then
        JsonExtractString = ""
    Else
        Dim scan As Long
        scan = start
        Do While scan <= Len(json) And InStr(",}]", Mid(json, scan, 1)) = 0
            scan = scan + 1
        Loop
        JsonExtractString = Trim(Mid(json, start, scan - start))
    End If
End Function

Private Function JsonExtractArray(ByVal json As String, ByVal key As String) As String
    ' Returns the raw "[...]" text for a top-level array field, matching
    ' bracket depth so nested arrays/objects inside it are not truncated.
    Dim needle As String
    needle = """" & key & """:"
    Dim p As Long
    p = InStr(json, needle)
    If p = 0 Then
        JsonExtractArray = "[]"
        Exit Function
    End If
    Dim start As Long
    start = InStr(p, json, "[")
    Dim depth As Long, i As Long
    depth = 0
    For i = start To Len(json)
        Dim ch As String
        ch = Mid(json, i, 1)
        If ch = "[" Then depth = depth + 1
        If ch = "]" Then
            depth = depth - 1
            If depth = 0 Then
                JsonExtractArray = Mid(json, start, i - start + 1)
                Exit Function
            End If
        End If
    Next i
    JsonExtractArray = "[]"
End Function

Private Function JsonSplitArrayItems(ByVal arrayJson As String) As Collection
    ' Splits a "[{...},{...}]" array into its top-level object strings,
    ' respecting nested brace depth (each row carries its own "days" array).
    Dim result As New Collection
    Dim inner As String
    inner = Mid(arrayJson, 2, Len(arrayJson) - 2)
    Dim depth As Long, itemStart As Long, i As Long
    depth = 0
    itemStart = 0
    For i = 1 To Len(inner)
        Dim ch As String
        ch = Mid(inner, i, 1)
        If ch = "{" Or ch = "[" Then
            If depth = 0 Then itemStart = i
            depth = depth + 1
        ElseIf ch = "}" Or ch = "]" Then
            depth = depth - 1
            If depth = 0 And itemStart > 0 Then
                result.Add Mid(inner, itemStart, i - itemStart + 1)
                itemStart = 0
            End If
        End If
    Next i
    Set JsonSplitArrayItems = result
End Function

Private Function JsonExtractStringArray(ByVal json As String, ByVal key As String) As Variant
    ' "days":["D","","DEL"] -> a 0-based VBA array of strings.
    Dim raw As String
    raw = JsonExtractArray(json, key)
    Dim inner As String
    inner = Mid(raw, 2, Len(raw) - 2)
    If Trim(inner) = "" Then
        JsonExtractStringArray = Array()
        Exit Function
    End If
    Dim parts() As String
    parts = Split(inner, ",")
    Dim result() As String
    ReDim result(UBound(parts))
    Dim i As Long
    For i = 0 To UBound(parts)
        Dim v As String
        v = Trim(parts(i))
        If Left(v, 1) = """" Then v = Mid(v, 2, Len(v) - 2)
        result(i) = v
    Next i
    JsonExtractStringArray = result
End Function
