' ============================================================================
'  UserForm  frmTests  -  checkbox "select tests" dialog for the Auto-UT button.
'
'  Setup: in the VBA editor, Insert > UserForm, set its (Name) = frmTests, and
'  paste THIS block into the form's code window (double-click the blank form).
'  Do NOT add any controls by hand - they are created at runtime below, so the
'  form stays a plain blank UserForm and there is no .frx to manage and no
'  "trust access to the VBA project object model" needed.
'
'  The Module (outlook_macro.vba) does (late-bound so it compiles without this
'  form present):
'      Set f = UserForms.Add("frmTests") : f.MailSubject = subj : f.Show
'      If f.Cancelled Then Exit Sub Else tests = f.Result
'
'  Result is a comma list of the ticked keys (e.g. "boot,serdes"); none ticked
'  yields "all". Keep TESTS below in sync with autotest.py TEST_REGISTRY.
' ============================================================================
Option Explicit

Public Result As String        ' comma list of selected keys, or "all"
Public Cancelled As Boolean    ' True if Cancel / window closed
Public MailSubject As String   ' set by the caller before .Show (shown as a note)

' dynamically-added buttons need WithEvents so their Click handlers fire.
Private WithEvents btnOK As MSForms.CommandButton
Private WithEvents btnCancel As MSForms.CommandButton

' "key|label" per test item; ; separated. Matches autotest.py TEST_REGISTRY.
Private Const TESTS As String = _
    "boot|Boot health  (adb device + dmesg scan);" & _
    "serdes|SerDes / LSLink  (ping + flashid / switch / version 0x13)"

' keys ticked by default (comma list). Others start unticked.
Private Const DEFAULT_ON As String = "boot"

Private Sub UserForm_Initialize()
    Dim items() As String, parts() As String, i As Long, y As Long

    Me.Caption = "Auto-UT  -  select tests"
    Me.Width = 380
    Me.BackColor = &H80000005      ' window background
    y = 10

    ' which mail we're about to trigger for (set by the caller)
    If Len(MailSubject) > 0 Then
        Dim s As String
        s = MailSubject
        If Len(s) > 140 Then s = Left$(s, 140) & "..."
        Dim lblMail As MSForms.Label
        Set lblMail = Me.Controls.Add("Forms.Label.1", "lblMail")
        lblMail.Caption = "Mail:  " & s
        lblMail.Left = 12: lblMail.Top = y: lblMail.Width = 356: lblMail.Height = 30
        lblMail.WordWrap = True
        lblMail.ForeColor = &H606060
        y = y + 36
    End If

    AddLabel "lblHdr", "Tick the test items to run  (none ticked = all):", _
             12, y, 350, 16, True
    y = y + 26

    items = Split(TESTS, ";")
    For i = LBound(items) To UBound(items)
        parts = Split(items(i), "|")
        Dim cb As MSForms.CheckBox
        Set cb = Me.Controls.Add("Forms.CheckBox.1", "chk_" & parts(0))
        cb.Caption = parts(1)
        cb.Left = 18: cb.Top = y: cb.Width = 350: cb.Height = 18
        cb.Value = IsDefaultOn(parts(0))    ' default: only DEFAULT_ON keys ticked
        y = y + 24
    Next i

    y = y + 8
    Set btnOK = Me.Controls.Add("Forms.CommandButton.1", "btnOK")
    btnOK.Caption = "Run"
    btnOK.Left = 205: btnOK.Top = y: btnOK.Width = 75: btnOK.Height = 26
    btnOK.Default = True

    Set btnCancel = Me.Controls.Add("Forms.CommandButton.1", "btnCancel")
    btnCancel.Caption = "Cancel"
    btnCancel.Left = 290: btnCancel.Top = y: btnCancel.Width = 75: btnCancel.Height = 26
    btnCancel.Cancel = True

    Me.Height = y + 66            ' + title bar / borders
    Cancelled = True             ' default (X-close) counts as cancel
End Sub

' True if `key` appears in the DEFAULT_ON comma list (case-insensitive).
Private Function IsDefaultOn(ByVal key As String) As Boolean
    Dim d() As String, i As Long
    d = Split(LCase$(DEFAULT_ON), ",")
    For i = LBound(d) To UBound(d)
        If Trim$(d(i)) = LCase$(Trim$(key)) Then
            IsDefaultOn = True
            Exit Function
        End If
    Next i
End Function

' ByVal on the numeric params so callers may pass Long variables (e.g. y) - a
' ByRef "As Single" param would reject a Long with "ByRef argument type mismatch".
Private Sub AddLabel(ByVal nm As String, ByVal cap As String, _
                     ByVal l As Single, ByVal t As Single, _
                     ByVal w As Single, ByVal h As Single, ByVal bold As Boolean)
    Dim lbl As MSForms.Label
    Set lbl = Me.Controls.Add("Forms.Label.1", nm)
    lbl.Caption = cap
    lbl.Left = l: lbl.Top = t: lbl.Width = w: lbl.Height = h
    lbl.Font.Bold = bold
End Sub

Private Sub btnOK_Click()
    Dim ctl As MSForms.Control, sel As String
    For Each ctl In Me.Controls
        If TypeOf ctl Is MSForms.CheckBox Then
            If ctl.Value Then
                If Len(sel) > 0 Then sel = sel & ","
                sel = sel & Mid$(ctl.Name, 5)     ' strip the "chk_" prefix
            End If
        End If
    Next ctl
    If Len(sel) = 0 Then sel = "all"
    Result = sel
    Cancelled = False
    Me.Hide
End Sub

Private Sub btnCancel_Click()
    Cancelled = True
    Me.Hide
End Sub
