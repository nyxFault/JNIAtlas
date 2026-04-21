from collections import namedtuple
from binaryninja.log import log_info, log_error

from jni_atlas.jni_parse import parse_parameter_types, parse_return_type

Method = namedtuple("Method", ["class_name", "method_name", "type_descriptor", "is_static"])

_JNI_ATLAS_NATIVE_TABLE_BYTES = 0x748
_JNI_ATLAS_INVOKE_TABLE_BYTES = 0x200

# Parsed in batches because Binja's type parser resolves typedef dependencies per parse call.
_JNI_ATLAS_HEADER = """
typedef unsigned char jboolean;
typedef char jbyte;
typedef unsigned short jchar;
typedef short jshort;
typedef int jint;
typedef long long jlong;
typedef float jfloat;
typedef double jdouble;
typedef jint jsize;

struct _jobject { char opaque; };
struct _jarray { char opaque; };
typedef struct _jobject* jobject;
typedef jobject jclass;
typedef jobject jstring;
typedef jobject jthrowable;
typedef jobject jweak;
typedef jobject jarray;
typedef jarray jbooleanArray;
typedef jarray jbyteArray;
typedef jarray jcharArray;
typedef jarray jshortArray;
typedef jarray jintArray;
typedef jarray jlongArray;
typedef jarray jfloatArray;
typedef jarray jdoubleArray;
typedef jarray jobjectArray;

struct JNIInvokeInterface_ { char opaque[%d]; };
typedef const struct JNIInvokeInterface_* JavaVM;

struct JNINativeInterface_ { char opaque[%d]; };
typedef const struct JNINativeInterface_* JNIEnv;
""" % (
	_JNI_ATLAS_INVOKE_TABLE_BYTES,
	_JNI_ATLAS_NATIVE_TABLE_BYTES,
)

_JNI_ATLAS_BATCHES = [
	"""
typedef unsigned char jboolean;
typedef char jbyte;
typedef unsigned short jchar;
typedef short jshort;
typedef int jint;
typedef long long jlong;
typedef float jfloat;
typedef double jdouble;
typedef jint jsize;
""",
	"""
struct _jobject { char opaque; };
struct _jarray { char opaque; };
typedef struct _jobject* jobject;
typedef jobject jclass;
typedef jobject jstring;
typedef jobject jthrowable;
typedef jobject jweak;
typedef jobject jarray;
typedef jarray jbooleanArray;
typedef jarray jbyteArray;
typedef jarray jcharArray;
typedef jarray jshortArray;
typedef jarray jintArray;
typedef jarray jlongArray;
typedef jarray jfloatArray;
typedef jarray jdoubleArray;
typedef jarray jobjectArray;
""",
	"""
struct JNIInvokeInterface_ { char opaque[%d]; };
typedef const struct JNIInvokeInterface_* JavaVM;
struct JNINativeInterface_ { char opaque[%d]; };
typedef const struct JNINativeInterface_* JNIEnv;
"""
	% (
		_JNI_ATLAS_INVOKE_TABLE_BYTES,
		_JNI_ATLAS_NATIVE_TABLE_BYTES,
	),
]


def _typeparser_result_to_map(result):
	out = {}
	if result is None:
		return out
	types = getattr(result, "types", None)
	if isinstance(types, dict):
		for k, v in types.items():
			out[k] = v
	elif isinstance(types, list):
		for p in types:
			if hasattr(p, "name") and hasattr(p, "type"):
				out[p.name] = p.type
	return out


def _register_jni_types_incremental(bv):
	for bi, blob in enumerate(_JNI_ATLAS_BATCHES):
		try:
			r = bv.parse_types_from_string(blob, import_dependencies=False)
			chunk = _typeparser_result_to_map(r)
			if chunk:
				# Commit each batch before parsing the next one so typedef chains resolve.
				added = bv.user_type_container.add_types(chunk)
				if added is None:
					log_error(
						"[JNIAtlas] user_type_container.add_types returned None (batch {})".format(
							bi
						)
					)
			elif bi == 0:
				log_info(
					"[JNIAtlas] JNI batch {} parse returned no type map (unexpected)".format(bi)
				)
		except SyntaxError as e:
			log_info("[JNIAtlas] JNI batch {} skipped: {}".format(bi, e))
		except Exception as e:
			log_info("[JNIAtlas] JNI batch {} error: {}".format(bi, e))
	if bv.get_type_by_name("jobject") is not None and bv.get_type_by_name("jbyteArray") is not None:
		return True
	if bv.get_type_by_name("jobject") is not None:
		return True
	return False


_JNI_SAFE_PRIMITIVE = {
	"void": "void",
	"jboolean": "uint8_t",
	"jbyte": "int8_t",
	"jchar": "uint16_t",
	"jshort": "int16_t",
	"jint": "int32_t",
	"jlong": "int64_t",
	"jfloat": "float",
	"jdouble": "double",
}


def _jni_type_to_parseable(jni_name):
	if jni_name in _JNI_SAFE_PRIMITIVE:
		return _JNI_SAFE_PRIMITIVE[jni_name]
	return "void*"


def build_binja_type_signature(method_name, method, attr):
	t = ""
	t += parse_return_type(method)
	t += " {}".format(method_name)
	t += " (JNIEnv* env, "
	if method.is_static:
		t += "jclass thiz"
	else:
		t += "jobject thiz"
	for count, param in enumerate(parse_parameter_types(method)):
		t += ", {} p{}".format(param, count)
	t += ")"
	if attr:
		t += " {}".format(attr)
	return t


def build_binja_type_signature_safe(method_name, method, attr):
	# Fallback signature that avoids JNI typedef dependencies entirely.
	t = ""
	t += _jni_type_to_parseable(parse_return_type(method))
	t += " {}".format(method_name)
	t += " (void* env, void* thiz"
	for count, param in enumerate(parse_parameter_types(method)):
		t += ", {} p{}".format(_jni_type_to_parseable(param), count)
	t += ")"
	if attr:
		t += " {}".format(attr)
	return t


def register_jni_atlas_jni_types(bv):
	if getattr(bv, "_jni_atlas_jni_types_registered", False):
		return True

	if _register_jni_types_incremental(bv):
		bv._jni_atlas_jni_types_registered = True
		log_info("[JNIAtlas] Registered JNI types (incremental)")
		return True

	def _have_core_jni():
		return bv.get_type_by_name("jobject") is not None

	for label, blob in (
		("full", _JNI_ATLAS_HEADER),
		(
			"minimal",
			"""
struct _jobject { char opaque; };
struct _jarray { char opaque; };
struct JNIInvokeInterface_ { char opaque[%d]; };
struct JNINativeInterface_ { char opaque[%d]; };
"""
			% (_JNI_ATLAS_INVOKE_TABLE_BYTES, _JNI_ATLAS_NATIVE_TABLE_BYTES),
		),
	):
		try:
			bv.parse_types_from_string(blob, import_dependencies=False)
			log_info("[JNIAtlas] Registered JNI types ({})".format(label))
			if _have_core_jni():
				bv._jni_atlas_jni_types_registered = True
				return True
			log_info("[JNIAtlas] Bulk JNI parse did not surface jobject; types may still be incomplete")
		except SyntaxError as e:
			log_info("[JNIAtlas] JNI type block {} skipped: {}".format(label, e))
			continue
		except Exception as e:
			log_info("[JNIAtlas] JNI type block {} error: {}".format(label, e))
			continue

	log_error(
		"[JNIAtlas] Could not register JNI typedefs; prototypes may fall back to void*/ints."
	)
	return False


def apply_jni_function_prototype(func, sig_str, fallback_sig=None):
	last_err = None
	for imp_dep in (False, True):
		try:
			# Try without importing external type deps first; this is more stable for JNI aliases.
			typ, new_name = func.view.parse_type_string(sig_str, import_dependencies=imp_dep)
			func.set_user_type(typ)
			if new_name is not None:
				ns = str(new_name)
				if ns and ns != func.name:
					func.name = ns
			return
		except Exception as e:
			last_err = e
			continue
	if fallback_sig:
		log_info(
			"[JNIAtlas] Using void*/int fallback for {} (primary parse failed: {})".format(
				func.name, last_err
			)
		)
		try:
			typ, new_name = func.view.parse_type_string(
				fallback_sig, import_dependencies=False
			)
			func.set_user_type(typ)
			if new_name is not None:
				ns = str(new_name)
				if ns and ns != func.name:
					func.name = ns
			return
		except Exception as e2:
			last_err = e2
	log_error("[JNIAtlas] Could not apply prototype: {} ({})".format(sig_str, last_err))


def ensure_tag_type(bv, name="JNIAtlas", icon="map"):
	existing = bv.get_tag_type(name)
	if existing is not None:
		return existing
	return bv.create_tag_type(name, icon)


def apply_comment(func, method):
	base = func.comment or ""
	if "JNIAtlas" in base:
		return
	func.comment = "{}\nJNIAtlas:\nClass: {}\nMethod: {}".format(
		base, method.class_name, method.method_name
	)


def apply_function_tag(func, tagtype, data):
	name = tagtype.name
	tags = func.get_function_tags(auto=False, tag_type=name)
	for tag in tags:
		if tag.type.name == name:
			break
	else:
		func.add_tag(name, data)
