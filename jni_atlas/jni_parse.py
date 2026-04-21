import re

TYPE_REGEX = re.compile(r"\((|.+?)\)(.+)")


def parse_jni_method_name(method):
	ret = "Java_"
	ret += _mangle(str(method.class_name)[1:-1]).replace("/", "_")
	ret += "_"
	ret += _mangle(str(method.method_name))
	return ret


def parse_jni_method_name_full(method):
	ret = parse_jni_method_name(method)
	ret += "__"
	ret += _mangle(_parse_parameter_signature(method)).replace("/", "_")
	return ret


def parse_return_type(method):
	sig = TYPE_REGEX.match(str(method.type_descriptor)).group(2)
	return _parse_type_signature(sig)


def parse_parameter_types(method):
	sig = _parse_parameter_signature(method)
	sig = iter(sig)
	ret = []
	while True:
		try:
			cur = next(sig)
			if cur == "L":
				ret.append(_parse_type_signature(_parse_class(sig)))
				cur = next(sig)
			elif cur == "[":
				param = "["
				cur = next(sig)
				if cur == "L":
					param += _parse_class(sig)
					ret.append(_parse_type_signature(param))
				else:
					param += cur
					ret.append(_parse_type_signature(param))
				cur = next(sig)
			else:
				ret.append(_parse_type_signature(cur))
		except StopIteration:
			break
	return ret


def _mangle(string):
	ret = ""
	for c in string:
		if c == "_":
			ret += "_1"
		elif c == ";":
			ret += "_2"
		elif c == "[":
			ret += "_3"
		elif c == "$":
			ret += "_"
		else:
			i = ord(c)
			if i < 128:
				ret += c
			else:
				ret += "_0{:04x}".format(i)
	return ret


def _parse_parameter_signature(method):
	return TYPE_REGEX.match(str(method.type_descriptor)).group(1)


def _parse_class(sig_iter):
	param = "L"
	while True:
		cur = next(sig_iter)
		param += cur
		if cur == ";":
			return param


def _parse_type_signature(sig):
	if sig == "Z":
		return "jboolean"
	if sig == "B":
		return "jbyte"
	if sig == "C":
		return "jchar"
	if sig == "S":
		return "jshort"
	if sig == "I":
		return "jint"
	if sig == "J":
		return "jlong"
	if sig == "F":
		return "jfloat"
	if sig == "D":
		return "jdouble"
	if sig.startswith("L"):
		sig = sig[1:-1]
		if sig == "java/lang/String":
			return "jstring"
		if sig == "java/lang/Class":
			return "jclass"
		return "jobject"
	if sig.startswith("["):
		sig = sig[1]
		if sig == "Z":
			return "jbooleanArray"
		if sig == "B":
			return "jbyteArray"
		if sig == "C":
			return "jcharArray"
		if sig == "S":
			return "jshortArray"
		if sig == "I":
			return "jintArray"
		if sig == "J":
			return "jlongArray"
		if sig == "F":
			return "jfloatArray"
		if sig == "D":
			return "jdoubleArray"
		return "jobjectArray"
	return "void"
