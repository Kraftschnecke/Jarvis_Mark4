"""Lautstaerke im Webserver: COM muss in jedem Thread gestartet und wieder beendet werden
(Fehler 3.3 der Abnahme: 'Die erforderliche Windows-Komponente wurde nicht initialisiert')."""
import os
import sys
import threading
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

events = []

comtypes = types.ModuleType("comtypes")
comtypes.CoInitialize = lambda: events.append("init")
comtypes.CoUninitialize = lambda: events.append("uninit")
sys.modules["comtypes"] = comtypes


class Endpoint:
    def SetMasterVolumeLevelScalar(self, value, context):
        events.append(("set", value))


class Speakers:
    EndpointVolume = Endpoint()


pycaw = types.ModuleType("pycaw")
inner = types.ModuleType("pycaw.pycaw")


class AudioUtilities:
    @staticmethod
    def GetSpeakers():
        events.append("speakers")
        return Speakers()


inner.AudioUtilities = AudioUtilities
sys.modules["pycaw"] = pycaw
sys.modules["pycaw.pycaw"] = inner

from tools.volume_tool import set_volume

results = []
thread = threading.Thread(target=lambda: results.append(set_volume(30)))
thread.start()
thread.join()

assert results[0].success, results[0].error
assert events == ["init", "speakers", ("set", 0.3), "uninit"], events

# Fehler im Geraet: COM wird trotzdem beendet, Fehler kommt als Ergebnis zurueck
events.clear()
AudioUtilities.GetSpeakers = staticmethod(lambda: (_ for _ in ()).throw(OSError("kein Geraet")))
bad = set_volume(50)
assert not bad.success and "kein Geraet" in bad.error
assert events == ["init", "uninit"], events

# Ungueltige Werte starten COM gar nicht
events.clear()
assert not set_volume(150).success
assert not set_volume("laut").success
assert events == []

print("ALL TESTS PASSED")
