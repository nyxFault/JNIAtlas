from pathlib import Path

from binaryninja.plugin import BackgroundTaskThread
from binaryninja.interaction import get_open_filename_input
from binaryninja.log import log_info, log_error

from jni_atlas.jni_utils import (
	Method,
	build_binja_type_signature,
	build_binja_type_signature_safe,
	register_jni_atlas_jni_types,
	apply_jni_function_prototype,
	ensure_tag_type,
	apply_comment,
	apply_function_tag,
)
from jni_atlas.jni_parse import parse_jni_method_name, parse_jni_method_name_full


class JNIAtlasAPKImporter(BackgroundTaskThread):
	def __init__(self, bv):
		BackgroundTaskThread.__init__(self, "JNIAtlas: Import APK…", True)
		self.bv = bv

	def run(self):
		try:
			from androguard.misc import AnalyzeAPK
		except ImportError:
			log_error("[JNIAtlas] Androguard not installed. pip install git+https://github.com/androguard/androguard.git")
			return

		register_jni_atlas_jni_types(self.bv)
		tag = ensure_tag_type(self.bv)

		fname = get_open_filename_input("JNIAtlas — Select APK")
		if not fname:
			return
		fname_root = Path(fname).name
		with open(fname, "rb") as f:
			log_info("[JNIAtlas] Analyzing APK")
			analysis = self._run_analysis(f, AnalyzeAPK)
			log_info("[JNIAtlas] Analysis complete")
			# Support both short and fully-mangled JNI symbol forms.
			method_map = {}
			for method in analysis:
				method_map[parse_jni_method_name(method)] = method
				method_map[parse_jni_method_name_full(method)] = method

			for func in self.bv.functions:
				if func.name == "JNI_OnLoad":
					apply_jni_function_prototype(
						func,
						"jint JNI_OnLoad(JavaVM *vm, void *reserved);",
						fallback_sig="int32_t JNI_OnLoad(void *vm, void *reserved);",
					)
					apply_function_tag(func, tag, "JNI_OnLoad")
					continue
				if func.name == "JNI_OnUnload":
					apply_jni_function_prototype(
						func,
						"void JNI_OnUnload(JavaVM *vm, void *reserved);",
						fallback_sig="void JNI_OnUnload(void *vm, void *reserved);",
					)
					apply_function_tag(func, tag, "JNI_OnUnload")
					continue
				try:
					m = method_map[func.name]
					log_info("[JNIAtlas] Typing: {}".format(func.name))
					apply_jni_function_prototype(
						func,
						build_binja_type_signature(func.name, m, ""),
						fallback_sig=build_binja_type_signature_safe(func.name, m, ""),
					)
					apply_function_tag(func, tag, "APK: {}".format(fname_root))
					apply_comment(func, m)
				except KeyError:
					continue

	def _run_analysis(self, apk, AnalyzeAPK):
		ret = []
		_, _, dex = AnalyzeAPK(apk)
		for klass in dex.get_classes():
			for method in klass.get_methods():
				if "native" in method.access:
					ret.append(
						Method(
							method.class_name,
							method.name,
							method.descriptor,
							"static" in method.access,
						)
					)
		return ret
