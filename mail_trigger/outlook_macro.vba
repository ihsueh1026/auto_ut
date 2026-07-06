' ============================================================================
'  Outlook button macro - MANUAL trigger (no auto-fire on new mail).
'
'  You pick a "Build Successfully" mail (select it in the list, or open it),
'  click the button, confirm, and it launches autotest for that build.
'
'  Install:
'    1. Outlook > Alt+F11 (VBA editor).
'    2. IMPORTANT: right-click the project > Insert > Module. Paste this block
'       into that standard MODULE - NOT into "ThisOutlookSession". Macros in
'       ThisOutlookSession do NOT show up in the button (QAT) macro list.
'    3. Insert > UserForm. Keep its DEFAULT name UserForm1 (no rename needed).
'       Leave it EMPTY (no controls) - press F7 to open its code window and
'       paste the whole outlook_frmTests.vba block there. The checkboxes are
'       created by code, so you never drag any controls. (This needs NO "trust
'       access to the VBA project object model".)
'    4. Edit PY and RUN_ON_MAIL paths below. File > Save.
'    5. Restart Outlook (enable macros if Trust Center prompts).
'    6. Add it as a button:
'         File > Options > Quick Access Toolbar >
'         "Choose commands from" dropdown = Macros >
'         pick "Project1.TriggerAutotestOnSelectedMail" > Add >> OK.
'       A button appears on the QAT; click it while a build mail is selected.
'
'  It pops a checkbox dialog (UserForm1: boot / serdes / ...) to pick test items, then
'  hands subject + body + EntryID + --tests to run_on_mail.py with --manual
'  (which skips the whitelist + de-dup, since you clicked deliberately).
' ============================================================================
Option Explicit

Private Const PY As String = "C:\Users\ali_lin\AppData\Local\Microsoft\WindowsApps\python.exe"
Private Const RUN_ON_MAIL As String = "D:\claude\sw6100\auto_ut\mail_trigger\run_on_mail.py"

Public Sub TriggerAutotestOnSelectedMail()
    Dim m As Outlook.MailItem
    Set m = ActiveMail()
    If m Is Nothing Then
        MsgBox "Select (or open) a mail first.", vbExclamation, "Auto-UT"
        Exit Sub
    End If

    ' one dialog: pick which test items to run (checkbox form -> autotest
    ' --tests). Its Run/Cancel IS the confirmation; none ticked = "all".
    ' UserForm1 builds its checkboxes dynamically and shows the mail subject.
    '
    ' EARLY-BOUND (New UserForm1). Outlook VBA's UserForms.Add is unreliable - it
    ' returns Nothing even when the form exists - so use New on the form's name.
    ' The form must exist as a UserForm named UserForm1 (the default from
    ' Insert > UserForm). If you get a compile error "User-defined type not
    ' defined" on UserForm1 below, that form is missing or has a different name.
    Dim f As UserForm1, tests As String, skipFlash As Boolean
    Set f = New UserForm1
    f.MailSubject = m.Subject
    f.Show                                       ' modal
    If f.Cancelled Then
        Unload f
        Exit Sub
    End If
    tests = f.Result
    skipFlash = f.SkipFlash                       ' "Test only" ticked
    Unload f
    If Len(tests) = 0 Then tests = "all"

    ' body -> temp file (avoids command-line length / quoting limits)
    Dim tmp As String
    tmp = Environ$("TEMP") & "\build_mail_body.txt"
    WriteFile tmp, m.Body

    Dim sender As String
    sender = ""
    On Error Resume Next
    sender = m.SenderEmailAddress
    On Error GoTo 0

    Dim cmd As String
    cmd = """" & PY & """ """ & RUN_ON_MAIL & """" & _
          " --manual" & _
          " --id """ & m.EntryID & """" & _
          " --subject """ & Replace(m.Subject, """", "'") & """" & _
          " --sender """ & sender & """" & _
          " --tests """ & tests & """" & _
          " --body-file """ & tmp & """"
    If skipFlash Then cmd = cmd & " --test-only"

    ' cmd /k keeps the console open so you can read the result.
    ' NOTE: the whole command is wrapped in ONE extra pair of quotes. cmd /k,
    ' when it sees >2 quotes, strips the first and last quote on the line; the
    ' outer pair absorbs that so the inner quoted paths stay intact.
    Shell "cmd /k """ & cmd & """", vbNormalFocus
End Sub

' current open mail (Inspector) else the first selected mail (Explorer)
Private Function ActiveMail() As Outlook.MailItem
    On Error Resume Next
    Dim insp As Outlook.Inspector
    Set insp = Application.ActiveInspector
    If Not insp Is Nothing Then
        If TypeOf insp.CurrentItem Is Outlook.MailItem Then
            Set ActiveMail = insp.CurrentItem
            Exit Function
        End If
    End If
    Dim sel As Outlook.Selection
    Set sel = Application.ActiveExplorer.Selection
    If Not sel Is Nothing Then
        If sel.Count >= 1 Then
            If TypeOf sel.Item(1) Is Outlook.MailItem Then Set ActiveMail = sel.Item(1)
        End If
    End If
End Function

Private Sub WriteFile(ByVal path As String, ByVal text As String)
    Dim f As Integer
    f = FreeFile
    Open path For Output As #f
    Print #f, text
    Close #f
End Sub
