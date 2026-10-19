from tools.tool_result import ToolResult


def set_volume(percentage):
    try:
        value = float(percentage)
    except (TypeError, ValueError):
        return ToolResult(
            success=False,
            error="Die Lautstaerke muss eine Zahl sein."
        )

    if not 0 <= value <= 100:
        return ToolResult(
            success=False,
            error="Die Lautstaerke muss zwischen 0 und 100 Prozent liegen."
        )

    try:
        # pycaw gibt es nur unter Windows. Der Import steht erst hier, damit
        # das Modul ueberall importierbar bleibt und ein fehlendes pycaw
        # als normaler Tool-Fehler gemeldet wird.
        from pycaw.pycaw import AudioUtilities

        devices = AudioUtilities.GetSpeakers()
        volume_control = devices.EndpointVolume

        volume_control.SetMasterVolumeLevelScalar(
            value / 100,
            None
        )

        return ToolResult(
            success=True,
            data=percentage
        )

    except Exception as error:
        return ToolResult(
            success=False,
            error=str(error)
        )
