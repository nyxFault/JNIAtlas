from binaryninja.plugin import BackgroundTaskThread
from binaryninja.flowgraph import FlowGraph, FlowGraphNode
from binaryninja.enums import BranchType, InstructionTextTokenType
from binaryninja.function import DisassemblyTextLine, InstructionTextToken
from binaryninja.interaction import show_message_box, MessageBoxButtonSet
from binaryninja.log import log_info, log_warn

from jni_atlas.jni_utils import register_jni_atlas_jni_types


def _is_jni_export_name(name: str) -> bool:
	if not name:
		return False
	if name.startswith("Java_"):
		return True
	if name in ("JNI_OnLoad", "JNI_OnUnload"):
		return True
	return False


def _truncate(s: str, n: int = 88) -> str:
	if not s:
		return s
	return s if len(s) <= n else s[: n - 1] + "…"


def _function_graph_lines(func, prefix: str):
	addr = func.start
	name = _truncate(func.name or "<sub>", 88)
	line1 = DisassemblyTextLine(
	    [
	        InstructionTextToken(InstructionTextTokenType.TextToken, prefix),
	        InstructionTextToken(InstructionTextTokenType.CodeSymbolToken, name, value=addr, address=addr),
	    ],
	    address=addr,
	)
	addr_hex = "{:#x}".format(addr)
	line2 = DisassemblyTextLine(
	    [
	        InstructionTextToken(InstructionTextTokenType.TextToken, "@ "),
	        InstructionTextToken(InstructionTextTokenType.PossibleAddressToken, addr_hex, value=addr),
	    ],
	    address=addr,
	)
	return [line1, line2]


def _bind_flow_node_to_function(node: FlowGraphNode, func, prefix: str) -> None:
	node.lines = _function_graph_lines(func, prefix)
	blocks = getattr(func, "basic_blocks", None) or []
	if blocks:
		node.basic_block = blocks[0]


def _collect_report(bv):
	lines = []
	lines.append("JNIAtlas — JNI Radar")
	fn = getattr(bv.file, "filename", None) if bv.file else None
	lines.append("BinaryView: {}".format(fn or "(no file)"))
	lines.append("")

	jni_funcs = [f for f in bv.functions if _is_jni_export_name(f.name)]
	if not jni_funcs:
		log_warn("[JNIAtlas] No Java_* / JNI_OnLoad / JNI_OnUnload symbols found.")
		lines.append("No JNI-shaped exports found (names starting with Java_ or JNI_OnLoad/Unload).")
		return "\n".join(lines)

	jni_funcs.sort(key=lambda f: f.start)
	lines.append("Found {} JNI entry point(s):\n".format(len(jni_funcs)))

	for func in jni_funcs:
		try:
			callees = func.callees
		except Exception as e:
			callees = []
			lines.append("{} @ {:#x}  (callees error: {})".format(func.name, func.start, e))
			continue

		lines.append("▸ {} @ {:#x}".format(func.name, func.start))
		if not callees:
			lines.append("   (no resolved callees)")
		else:
			for c in sorted(callees, key=lambda x: x.start):
				lines.append("   → {} @ {:#x}".format(c.name or "<sub>", c.start))
		lines.append("")

	return "\n".join(lines)


def build_jni_radar_flowgraph(bv) -> FlowGraph:
	jni_funcs = sorted([f for f in bv.functions if _is_jni_export_name(f.name)], key=lambda f: f.start)
	g = FlowGraph()
	g.view = bv
	root = FlowGraphNode(g)
	fn = getattr(bv.file, "filename", None) if bv.file else None
	root.lines = [
		"JNIAtlas Radar",
		_truncate(fn or "(no file name)", 64),
		"{} JNI entry point(s)".format(len(jni_funcs)),
	]
	g.append(root)

	if not jni_funcs:
		hint = FlowGraphNode(g)
		hint.lines = ["No Java_* / JNI_OnLoad / JNI_OnUnload symbols found."]
		g.append(hint)
		root.add_outgoing_edge(BranchType.UnconditionalBranch, hint)
		return g

	nodes_by_addr = {}

	for jf in jni_funcs:
		n = FlowGraphNode(g)
		_bind_flow_node_to_function(n, jf, "JNI: ")
		g.append(n)
		nodes_by_addr[jf.start] = n
		root.add_outgoing_edge(BranchType.UnconditionalBranch, n)

	for jf in jni_funcs:
		jni_node = nodes_by_addr[jf.start]
		try:
			callees = jf.callees
		except Exception:
			continue
		for callee in sorted(callees, key=lambda x: x.start):
			if callee.start == jf.start:
				continue
			if callee.start not in nodes_by_addr:
				cn = FlowGraphNode(g)
				_bind_flow_node_to_function(cn, callee, "→ ")
				g.append(cn)
				nodes_by_addr[callee.start] = cn
			jni_node.add_outgoing_edge(BranchType.UnconditionalBranch, nodes_by_addr[callee.start])

	return g


class JNIAtlasRadar(BackgroundTaskThread):
	def __init__(self, bv):
		BackgroundTaskThread.__init__(self, "JNIAtlas: JNI Radar…", True)
		self.bv = bv

	def run(self):
		register_jni_atlas_jni_types(self.bv)

		text = _collect_report(self.bv)
		for line in text.splitlines():
			log_info(line)

		try:
			graph = build_jni_radar_flowgraph(self.bv)
			self.bv.show_graph_report("JNIAtlas — JNI Radar", graph)
			log_info("[JNIAtlas] Flow graph tab opened. Full text report is in View → Log.")
		except Exception as e:
			log_warn("[JNIAtlas] Could not build graph: {} — see Log for text report.".format(e))
			preview = text if len(text) < 1200 else text[:1100] + "\n… (truncated — full report in Log)"
			show_message_box("JNIAtlas — JNI Radar (text only)", preview, MessageBoxButtonSet.OKButtonSet)
