import os
import sys

_plugin_dir = os.path.dirname(os.path.abspath(__file__))
if _plugin_dir not in sys.path:
	sys.path.insert(0, _plugin_dir)

from binaryninja.plugin import PluginCommand

from jni_atlas.apk_import import JNIAtlasAPKImporter
from jni_atlas.jni_show import JNIAtlasRadar


def _import_apk(bv):
	JNIAtlasAPKImporter(bv).start()


def _jni_radar(bv):
	JNIAtlasRadar(bv).start()


PluginCommand.register(
	r"JNIAtlas\Import APK (rename JNI methods)",
	"Parse an APK with Androguard and apply JNI prototypes to matching native symbols.",
	_import_apk,
)

PluginCommand.register(
	r"JNIAtlas\JNI Radar (graph + Log)",
	"Open an interactive flow graph: root → JNI exports → callees (deduped). Full listing also in the Log.",
	_jni_radar,
)
