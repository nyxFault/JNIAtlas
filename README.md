<div align="center">

# JNIAtlas

**Map JNI entry points from an APK and explore JNI-to-native call graphs in [Binary Ninja](https://binary.ninja/).**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Binary Ninja](https://img.shields.io/badge/Binary%20Ninja-4.0%2B-5C4EE5)](https://binary.ninja/)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-linux%20%7C%20macOS%20%7C%20windows-lightgrey)]()

*Inspired by [Ayrx JNIAnalyzer](https://github.com/Ayrx/binja-JNIAnalyzer).*

[Features](#features) · [Install](#install) · [Usage](#usage)

</div>

---

## Why JNIAtlas?

Native Android libraries expose JNI entry points as long mangled names (`Java_com_example_app_Foo_bar`). The readable contract (class, method, `static` or not, Java parameter types) lives in **DEX**. JNIAtlas connects the APK to the open `.so` so Binary Ninja shows real **JNI-style prototypes** (`JNIEnv*`, `jobject` / `jclass`, `jstring`, `jbyteArray`, …) instead of guessing.

---

## Features

| | |
|---|---|
| **Import APK** | Pick a matching APK; **Androguard** reads DEX, matches `native` methods to `Java_…` symbols, applies prototypes and optional comments/tags. |
| **JNI Radar** | No APK needed: lists JNI-shaped exports, prints a report to the **Log**, and opens an interactive **flow graph** (JNI exports and their callees). |
| **Robust JNI types** | Ships a self-contained JNI typedef path for Binary Ninja’s parser so prototypes resolve without external JNI typelibs. |

---

## Install

1. **Clone** (or copy) this repo into your Binary Ninja user plugin folder, for example:
   - **Linux:** `~/.binaryninja/plugins/JNIAtlas`
   - **macOS:** `~/Library/Application Support/Binary Ninja/plugins/JNIAtlas`
   - **Windows:** `%APPDATA%\Binary Ninja\plugins\JNIAtlas`

2. **Python deps** (same interpreter Binary Ninja uses for plugins):

   ```bash
   pip install androguard
   ```

   For **Import APK**, Androguard must import cleanly from that environment.

3. Restart Binary Ninja (or reload plugins).

---

## Usage

Open an Android **`.so`** in Binary Ninja, then:

| Command | What it does |
|---------|----------------|
| **Plugins → JNIAtlas → Import APK (rename JNI methods)** | Choose the APK that matches this build. Matching `Java_…` functions get JNI prototypes and comments. |
| **Plugins → JNIAtlas → JNI Radar (graph + Log)** | Scan JNI exports and callees; graph tab + full text in **View → Log**. |

**Tip:** Use an APK built from the same app revision as the native code you are analyzing so DEX names and descriptors line up.

---

## Requirements

- **Binary Ninja** with Python 3 API (**v3.0.0** or newer per `plugin.json`).
- **Androguard** for **Import APK** only.
- A matching **APK** when you want APK-driven typing.
- No external JNI typelib package is required.

---

## Project layout

```
JNIAtlas/
├── __init__.py          # Plugin entry, command registration
├── plugin.json          # Metadata
├── jni_atlas/
│   ├── apk_import.py    # Import APK workflow
│   ├── jni_parse.py     # JNI name / descriptor parsing
│   ├── jni_utils.py     # Prototypes and JNI type registration
│   └── jni_show.py      # JNI Radar graph + log report
└── README.md
```

---

## Inspiration & credits

- [Ayrx / binja-JNIAnalyzer](https://github.com/Ayrx/binja-JNIAnalyzer)
- [Binary Ninja](https://binary.ninja/) Python API

---

---

<div align="center">

</div>
