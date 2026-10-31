# ReadAloud

<p align="center">
  <img src="data/icons/hicolor/scalable/apps/im.zackarious.ReadAloud.svg" alt="ReadAloud Logo" width="128" height="128"/>
</p>

<p align="center">
  <strong>An elegant, private, offline Text-to-Speech reader for the GNOME desktop.</strong>
</p>

<p align="center">
  <a href="https://flathub.org/apps/im.zackarious.ReadAloud"><img src="https://dl.flathub.org/assets/badges/flathub-badge-en.svg" alt="Download on Flathub" height="48"></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-1.8.10-blue.svg" alt="Version 1.8.10"/>
  <img src="https://img.shields.io/badge/license-GPL--3.0--or--later-blue.svg" alt="GPL-3.0 License"/>
  <img src="https://img.shields.io/badge/GTK-4-green.svg" alt="GTK 4"/>
  <img src="https://img.shields.io/badge/Libadwaita-1.0-purple.svg" alt="Libadwaita"/>
  <img src="https://img.shields.io/badge/Engine-Piper%20TTS-orange.svg" alt="Piper TTS"/>
  <img src="https://img.shields.io/badge/Platform-Linux-lightgrey.svg" alt="Linux"/>
</p>

---

**ReadAloud** is a modern, privacy-focused text-to-speech desktop application crafted with GTK4 and Libadwaita. Powered by the high-performance Piper neural speech engine, ReadAloud transforms your written text into rich, natural-sounding audio across diverse voices, accents, pitches, and speeds—complete with synchronized word highlighting, seamless playback controls, preset demos, and voice-optimized audio export.

Unlike conventional cloud-based voice assistants and commercial speech tools, ReadAloud is completely offline. Every syllable is synthesized locally on your own machine using efficient on-device neural models. ReadAloud requires zero internet connection, contains no telemetry, and transmits no data to external servers or third parties. Your personal documents, confidential manuscripts, private notes, and generated recordings remain entirely private, secure, and under your absolute personal control at all times.

ReadAloud is proud to be free and open-source software, licensed under the GNU General Public License v3.0. There are no subscriptions, no recurring fees, no locked paywalls, and no artificial daily usage limits. Transparent by design, the entire source code is openly audited and maintained by the community on GitHub at [https://github.com/Zackarious/ReadAloud](https://github.com/Zackarious/ReadAloud). Whether you are proofreading drafts, studying long articles, creating audio notes, or enhancing accessibility, ReadAloud offers an ethical, dependable, and always-accessible speech companion that forever puts your personal privacy and freedom first.

---

## 📸 Screenshots

<p align="center">
  <img src="data/screenshots/screenshot.png" alt="ReadAloud Screenshot" width="800"/>
</p>

---

## ✨ Features

- 🔒 **100% Offline & Private**: Text synthesis is performed entirely on your machine using local ONNX neural models.
- 🗣️ **Bundled Neural Voices**: Includes 26 natural-sounding English voices across **English (UK)** and **English (US)** with multiple voice actors, qualities (low, medium, high), and accents.
- ⭐ **Preset Voice Demos ("Run Demo")**: Instant 1-click test presets showcasing diverse neural voices, speeds, and pitches with overwrite warning protection.
- ⏳ **Loading HUD with Real-Time Countdown**: Sleek translucent HUD displaying a progress bar and estimated time remaining countdown during speech generation.
- 🎨 **Adaptive GNOME HIG Interface**: Built using Libadwaita with seamless support for light and dark system color schemes.
- 🎯 **Real-Time Word Highlighting**: Synchronized word-by-word visual highlight that smoothly tracks speech progression and automatically keeps text in view.
- ⏯️ **Complete Playback Controls**: Dedicated Play, Pause, Resume, and Stop controls with clean audio state transitions.
- 📍 **Read from Cursor or Selection**: Start listening from your current cursor location or selected text passage without needing to start from the beginning.
- 💾 **Multi-Format Audio Export**:
  - **MP3 (Voice-Optimized 64 kbps)**: Delivers crystal clear spoken-word audio with ~95% reduced file size.
  - **MP3 (128 kbps, 192 kbps, 256 kbps, 320 kbps)**: For standard to broadcast-grade fidelity.
  - **WAV**: Uncompressed 16-bit PCM audio.
  - **OGG Vorbis**: Open standard compressed audio.
  - **FLAC**: Lossless studio-grade compression.
- ⚡ **Simplified 3-Choice Speed Settings**: Easily choose between Normal, Fast, and Super Fast speeds, custom-calibrated across all 35 neural voice models with keyboard shortcut navigation (`Ctrl + Up` / `Ctrl + Down`).
- 🔍 **Dynamic Text Zoom**: Scale editor font from 70% to 1000% via shortcuts (`Ctrl +`, `Ctrl -`, `Ctrl 0`) or `Ctrl` + Mouse Wheel.
- 📜 **In-App Change Logs**: Browse version history and feature documentation directly within the application.

### 🎙️ Voice Quality Levels & Multi-Speaker Models

#### Quality
Voices are trained at one of 4 "quality" levels:
- **`x_low`** — 16Khz audio, 5-7M params
- **`low`** — 16Khz audio, 15-20M params
- **`medium`** — 22.05Khz audio, 15-20M params
- **`high`** — 22.05Khz audio, 28-32M params

#### Multi-Speaker
Some voices contain multiple speakers, which captures the style of multiple people within a single model.
Multi-speaker models can quickly switch between different speakers, but the quality of an individual speaker may be less than a single speaker model.

---

## ⌨️ Keyboard Shortcuts

| Action | Shortcut |
| :--- | :--- |
| **Play / Pause** | `Ctrl + P` / `Space` / `F5` |
| **Stop Playback** | `Escape` |
| **Save Audio to File** | `Ctrl + E` |
| **Increase Speed (+0.1)** | `Ctrl + Up` |
| **Decrease Speed (-0.1)** | `Ctrl + Down` |
| **Open Text File** | `Ctrl + O` |
| **Save Text to File** | `Ctrl + S` |
| **New Document Tab** | `Ctrl + T` |
| **Close Active Tab** | `Ctrl + W` |
| **Zoom In** | `Ctrl + +` / `Ctrl + =` / `Ctrl + Scroll Up` |
| **Zoom Out** | `Ctrl + -` / `Ctrl + Scroll Down` |
| **Reset Zoom (100%)** | `Ctrl + 0` |
| **Keyboard Shortcuts Help** | `Ctrl + ?` |
| **Quit Application** | `Ctrl + Q` |

---

## 📦 Installation

### From Flathub (Recommended)

ReadAloud is available as a sandboxed Flatpak on Flathub:

```bash
# Install ReadAloud
flatpak install flathub im.zackarious.ReadAloud

# Run ReadAloud
flatpak run im.zackarious.ReadAloud
```

### Building Flatpak Locally

To build and test the Flatpak package locally:

```bash
# Clone the repository
git clone https://github.com/zackarious/ReadAloud.git
cd ReadAloud

# Build and install locally
flatpak-builder --user --install --force-clean _flatpak_build im.zackarious.ReadAloud.json

# Run local build
flatpak run im.zackarious.ReadAloud
```

### Building from Source (Native Meson)

#### System Requirements & Dependencies

- **Python**: `>= 3.10`
- **GTK 4**: `gtk4 >= 4.12`
- **Libadwaita**: `libadwaita-1 >= 1.4`
- **GStreamer**: `gstreamer-1.0`, `gstreamer-plugins-base`, `gstreamer-plugins-good`, `gstreamer-plugins-ugly` (for MP3)
- **Meson**: `>= 1.0`
- **Ninja**: `>= 1.10`
- **Piper TTS**: `piper-tts`, `onnxruntime`

#### Build and Install

```bash
# Setup build directory
meson setup build --prefix=/usr/local

# Compile resources and translations
ninja -C build

# Run automated validation tests
ninja -C build test

# Install onto your system
sudo ninja -C build install
```

---

## 📁 Repository Structure

```
ReadAloud/
├── data/
│   ├── icons/                          # Application icons (scalable SVG & symbolic)
│   ├── screenshots/                    # AppStream & GitHub showcase screenshots
│   ├── im.zackarious.ReadAloud.desktop # Desktop entry definition
│   ├── im.zackarious.ReadAloud.gschema # GSettings schema
│   └── im.zackarious.ReadAloud.metainfo.xml.in # AppStream metadata
├── models/                             # Bundled Piper ONNX voice models
├── po/                                 # Internationalization & gettext translations
├── src/
│   ├── main.py                         # Application entrypoint & GtkApplication
│   ├── window.py                       # Main application window & UI logic
│   ├── reader.py                       # Playback engine, GStreamer pipeline & export
│   ├── pipervoice.py                   # Piper TTS model wrapper & discovery
│   ├── demos.py                        # Preset voice demos & configuration
│   └── window.ui                       # GTK 4 UI blueprint/template
├── im.zackarious.ReadAloud.json        # Flatpak manifest definition
├── meson.build                         # Top-level Meson build definition
└── README.md                           # Documentation
```

---

## 🤝 Contributing

Contributions, bug reports, and feature suggestions are welcome!

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

---

## 📜 License & Acknowledgments

- **License**: GNU General Public License v3.0 or later ([`GPL-3.0-or-later`](LICENSE)).
- **Original Parolu Project**: Created by [Walter Bernard](https://github.com/wbernard/parolu). ReadAloud is an evolution featuring enhanced English voice support, playback pausing, real-time tracking, multi-format audio export, and UI accessibility improvements.
- **Piper TTS**: Fast, local neural text-to-speech engine created by Michael Hansen ([Rhasspy / Piper](https://github.com/rhasspy/piper)).
- **Voices**: Voice models are provided by the [Piper Voices project](https://github.com/rhasspy/piper-voices) under their respective open licenses.
