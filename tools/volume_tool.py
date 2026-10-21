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

    com_started = False
    try:
        # pycaw gibt es nur unter Windows. Der Import steht erst hier, damit
        # das Modul ueberall importierbar bleibt und ein fehlendes pycaw
        # als normaler Tool-Fehler gemeldet wird.
        from pycaw.pycaw import AudioUtilities

        # Der Webserver bearbeitet jede Anfrage in einem eigenen Thread. Windows-COM
        # (damit steuert pycaw die Lautstaerke) muss in JEDEM Thread einmal gestartet werden,
        # sonst: "Die erforderliche Windows-Komponente wurde nicht initialisiert".
        try:
            import comtypes
            comtypes.CoInitialize()
            com_started = True
        except Exception:
            pass   # kein comtypes (kein Windows) oder schon gestartet: weiter wie bisher

        devices = AudioUtilities.GetSpeakers()
        volume_control = devices.EndpointVolume

        volume_control.SetMasterVolumeLevelScalar(
            value / 100,
            None
        )

        # COM-Objekte freigeben, bevor COM in diesem Thread wieder beendet wird
        del volume_control, devices

        return ToolResult(
            success=True,
            data=percentage
        )

    except Exception as error:
        return ToolResult(
            success=False,
            error=str(error)
        )

    finally:
        if com_started:
            try:
                import comtypes
                comtypes.CoUninitialize()
            except Exception:
                pass
