# ReadAloud

<p align="center">
  <img src="data/icons/hicolor/scalable/apps/im.zackarious.ReadAloud.svg" alt="ReadAloud Logo" width="128" height="128"/>
</p>

<p align="center">
  <strong>An elegant, private, offline Text-to-Speech reader for Windows and Linux (GNOME, KDE Plasma & more).</strong>
</p>

<p align="center">
  <a href="https://github.com/Zackarious/ReadAloud/releases/download/v1.8.19/ReadAloud-1.8.19-Windows-Setup-x64.exe"><img src="data/badges/download-windows.svg" alt="Download for Windows (.exe)" height="56"/></a>
  <a href="https://github.com/Zackarious/ReadAloud/releases/download/v1.8.19/ReadAloud-1.8.19-linux-x86_64.AppImage"><img src="data/badges/download-appimage.svg" alt="Download for Linux (.AppImage)" height="56"/></a>
  <a href="https://flathub.org/apps/im.zackarious.ReadAloud"><img src="data/badges/download-flathub.svg" alt="Download on Flathub" height="56"/></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-1.8.19-blue.svg" alt="Version 1.8.19"/>
  <img src="https://img.shields.io/badge/license-GPL--3.0--or--later-blue.svg" alt="GPL-3.0 License"/>
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-0078D6.svg" alt="Platform: Windows & Linux"/>
  <img src="https://img.shields.io/badge/Desktop-GNOME%20%7C%20KDE%20Plasma%20%7C%20Windows-green.svg" alt="Desktop: GNOME, KDE Plasma & Windows"/>
  <img src="https://img.shields.io/badge/GTK-4-green.svg" alt="GTK 4"/>
  <img src="https://img.shields.io/badge/Libadwaita-1.0-purple.svg" alt="Libadwaita"/>
  <img src="https://img.shields.io/badge/Engine-Piper%20TTS-orange.svg" alt="Piper TTS"/>
</p>

---

**ReadAloud** is a modern, privacy-focused, cross-platform text-to-speech desktop application crafted with GTK4 and Libadwaita. Built for both **Microsoft Windows (10/11)** and **Linux** (including **GNOME**, **KDE Plasma**, Cinnamon, MATE, and XFCE), ReadAloud delivers a native, responsive experience across operating systems and desktop environments. Powered by the high-performance Piper neural speech engine, ReadAloud transforms your written text into rich, natural-sounding audio across diverse voices, accents, pitches, and speeds—complete with synchronized word highlighting, intelligent sentence segmentation, seamless playback controls, preset demos, and voice-optimized audio export.

Unlike conventional cloud-based voice assistants and commercial speech tools, ReadAloud is completely offline. Every syllable is synthesized locally on your own machine using efficient on-device neural models. ReadAloud requires zero internet connection, contains no telemetry, and transmits no data to external servers or third parties. Your personal documents, confidential manuscripts, private notes, and generated recordings remain entirely private, secure, and under your absolute personal control at all times.

ReadAloud is proud to be free and open-source software, licensed under the GNU General Public License v3.0. There are no subscriptions, no recurring fees, no locked paywalls, and no artificial daily usage limits. Transparent by design, the entire source code is openly audited and maintained by the community on GitHub at [https://github.com/Zackarious/ReadAloud](https://github.com/Zackarious/ReadAloud). Whether you are proofreading drafts, studying long articles, creating audio notes, or enhancing accessibility on Windows or Linux, ReadAloud offers an ethical, dependable, and always-accessible speech companion that forever puts your personal privacy and freedom first.

---

## 📸 Screenshots & Feature Walkthrough

### Main Application Functions

#### 1. Document Importer & Dropzone
<p align="center">
  <img src="data/screenshots/01-drag-drop-importer.png" alt="Drag and Drop Document Importer" width="700"/>
</p>

*The main window presents an intuitive document dropzone with quick-action buttons, allowing users to effortlessly drag and drop reading materials to start listening without manual file browsing.*

- **Multi-Format Document Dropzone**: Seamlessly drag and drop `.txt`, `.md`, `.pdf`, or `.epub` files directly into ReadAloud to import them into working tabs.
- **Smart Book Chapter Extraction**: Automatically breaks EPUB and multi-chapter documents into distinct, navigable tabs.
- **Syntax & Symbol Cleansing**: Automatically strips distracting brackets, pipes, markdown hashes, and asterisks so the Piper neural speech engine reads pure, natural language.
- **Adaptive Window Controls**: Features standardized `:minimize,maximize,close` window controls, dedicated headerbar buttons, and font zoom capsule for instant one-click actions across all desktop environments.

---

#### 2. Synchronized Speech Playback & Word Highlighting
<p align="center">
  <img src="data/screenshots/05-active-playback-word-highlighting.png" alt="Active Speech Playback and Real-Time Word Highlighting" width="700"/>
</p>

*During audio playback, each spoken word is dynamically highlighted in signature yellow while playback controls coordinate state transitions, allowing users to effortlessly follow along visually as they listen.*

- **Synchronized Real-Time Word Highlighting**: High-contrast, dynamic highlighting tracks every spoken word in real-time and auto-scrolls to keep active text in view.
- **Signature Highlight Yellow Playback Buttons**: Primary controls (`Open Text File`, `Read Text`, `Pause`, `Stop`) are recoloured in `#f6d32d` to match the reader's active text highlight aesthetic.
- **Intelligent Sentence Segmentation**: Smooths PDF multi-column line breaks and joins hyphenated words, while guarding abbreviations (`Dr.`, `Mr.`, `e.g.`) and numerical values from premature pauses.
- **Automatic Paragraph Gap Separation**: Enforces clean `\n\n` empty line gaps between paragraphs, providing generous vertical separation that makes long articles effortless to follow during audio synthesis.

---

#### 3. Real-Time Speech Generation Progress HUD
<p align="center">
  <img src="data/screenshots/07-speech-generation-countdown-hud.png" alt="Real-Time Speech Generation Countdown HUD" width="700"/>
</p>

*While on-device neural speech is being synthesized, a sleek translucent progress HUD provides real-time percentage completion and an estimated seconds countdown, reassuring users with precise feedback and immediate cancellation control.*

- **Live Percentage & Countdown**: Displays real-time synthesis percentage and remaining time estimation (e.g. `Generating audio: 42% (~2s remaining)`).
- **Animated Activity Spinner**: Smooth loading spinner and progress indicator provide instant visual confirmation that audio processing is active.
- **One-Click Cancellation**: Click "Cancel" at any time to immediately abort speech synthesis and restore the workspace.

---

#### 4. High-Fidelity Neural Voice Library & Model Selector
<p align="center">
  <img src="data/screenshots/08-neural-voice-library-selector.png" alt="Neural Voice Selection Menu" width="700"/>
</p>

*The voice selector menu showcases diverse neural voices with clear speed and quality annotations, empowering users to tailor vocal timbre and generation speed to match their listening preferences.*

- **Diverse Voice Models**: Seamlessly choose from a curated catalog of natural-sounding neural voices across genders and styles.
- **Calibrated Quality Profiles**: Easily distinguish between Low, Medium, and High quality models optimized for speech generation speed versus acoustic fidelity.
- **Instant Live Switching**: Change the active narrator voice on the fly with automatic persistence for subsequent reading sessions.

---

#### 5. Multi-Language & Regional Accent Selector
<p align="center">
  <img src="data/screenshots/09-language-accent-selector.png" alt="Language and Regional Accent Selector" width="700"/>
</p>

*The regional dialect selector lets users switch between British and American English pronunciation profiles, ensuring natural and culturally familiar phonetic inflection for any document.*

- **Multi-Dialect Accents**: Toggle between British English (`English (UK)`) and American English (`English (US)`) voice packs.
- **Phonetic Naturalness**: Automatically selects region-appropriate phoneme mappings and stress patterns for smooth, natural narration.

---

#### 6. Calibrated Speech Speed Controls
<p align="center">
  <img src="data/screenshots/10-speech-speed-selector.png" alt="Calibrated Speech Speed Controls" width="700"/>
</p>

*The speech speed menu allows listeners to adjust narration pacing from deliberate slower study speeds to rapid reading rates, boosting productivity and learning comprehension.*

- **Five Calibrated Speeds**: Choose from `Slower`, `Slow`, `Normal`, `Fast`, and `Super Fast` speeds.
- **Pitch-Preserving Pacing**: Maintains natural voice pitch and timbre across all playback speeds without distorted chipmunk or robotic artifacts.

---

#### 7. Multi-Tab Document Reading & Thematic Highlighting
<p align="center">
  <img src="data/screenshots/11-multi-tab-audio-playback.png" alt="Multi-Tab Reading and Alternate Voice Playback" width="700"/>
</p>

*Synchronized real-time word highlighting guides the listener through rich historical documents with full multi-tab navigation, helping readers retain complex texts with combined visual and auditory immersion.*

- **Independent Multi-Tab Reading**: Maintain multiple reading documents, Wikipedia articles, or book chapters simultaneously across tabs.
- **Distraction-Free Visual Focus**: High-contrast active word highlighting keeps readers oriented in dense literature and long-form articles.

---

### Wikipedia Importer Features

#### 1. Live Autocomplete Search with Instant Previews
<p align="center">
  <img src="data/screenshots/03-wikipedia-live-search.png" alt="Live Autocomplete Wikipedia Search" width="700"/>
</p>

*As the user types into the search field, real-time Wikipedia suggestions appear with thumbnail previews and summaries, helping users immediately identify and import the exact topic they want to read.*

- **Official REST API Autocomplete**: Real-time debounced search backed by Wikipedia's official REST Search API, returning exact matches as you type.
- **Rich Visual Cards**: Displays article thumbnail previews, bold headings, and descriptive captions matching Wikipedia's website design.
- **In-Memory Thumbnail Caching**: Thread-safe in-memory image caching eliminates redundant network requests and ensures instant, flicker-free re-querying.
- **Keyboard-First Navigation**: Smoothly navigate down into suggestion cards with `Down Arrow`, hit `Enter` to import, or press `Escape` to dismiss.

---

#### 2. Wikipedia Top 25 Trending Topics Right Pane
<p align="center">
  <img src="data/screenshots/06-wikipedia-trending-topics.png" alt="Wikipedia Top 25 Trending Topics Right Pane" width="700"/>
</p>

*The expandable right pane displays the week's Top 25 Trending Wikipedia articles with ranking badges, thumbnail previews, view counts, and single-click import buttons, giving users immediate access to popular world knowledge without having to search.*

- **Curated Trending Discoveries**: Live scrapes Wikipedia's official weekly Top 25 Report (`Wikipedia:Top_25_Report`) complete with rank badges (`#1`, `#2`, ..., `#25`).
- **Rich Thumbnail Previews**: Displays high-quality thumbnail preview images and weekly view counters for each trending topic.
- **One-Click Instant Import**: Click the dedicated "Import" button on any trending row or click any row to instantly populate the search field.
- **In-Memory Caching & Live Refresh**: Caches report data in memory for instant re-opening while offering a manual refresh button (`view-refresh-symbolic`) to fetch the latest report.

---

## ✨ Features

- 🖥️ **Cross-Platform & Multi-Desktop**: Native experience on **Microsoft Windows (10/11)** and **Linux** across **GNOME**, **KDE Plasma**, Cinnamon, MATE, and XFCE with adaptive dark/light system theme matching.
- 🔒 **100% Offline & Private**: Text synthesis is performed entirely on your machine using local ONNX neural models.
- 🗣️ **Bundled Neural Voices**: Includes 35 natural-sounding voices across English and multilingual accents with multiple voice actors, qualities (low, medium, high), and styles.
- 📄 **Intelligent Sentence Segmentation**: Smoothly un-breaks PDF and multi-column line breaks, stitches hyphenated words, and safeguards abbreviations and numerical values from premature pauses.
- ⭐ **Preset Voice Demos ("Run Demo")**: Instant 1-click test presets showcasing diverse neural voices, speeds, and pitches with overwrite warning protection.
- ⏳ **Loading HUD with Real-Time Countdown**: Sleek translucent HUD displaying a progress bar and estimated time remaining countdown during speech generation.
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

## 💻 System & Software Requirements

ReadAloud runs fully offline using on-device Piper neural speech models and ONNX Runtime. Below are the hardware and operating system requirements:

### Minimum Requirements (Basic / Normal Voice Playback)
*Suitable for real-time speech playback with `medium`, `low`, and `x_low` voice models.*

| Component | Minimum Specification |
| :--- | :--- |
| **Processor** | 1.6 GHz or faster, 2-core processor (x86-64, ARM64, or Apple Silicon with SSE4.2 / NEON) |
| **Operating System** | • **Windows**: Windows 11, Windows Server 2025, or Windows Server 2022 *(Note: Microsoft official consumer support for Windows 10 ended in October 2025, though ReadAloud continues to run with MSVC 2022 runtime)*<br/>• **Linux**: Ubuntu 22.04 LTS+, Debian 12+, Fedora 38+, Arch Linux with GTK 4.6+ & Libadwaita 1.0+<br/>• **macOS**: macOS 12 (Monterey) or later |
| **Memory (RAM)** | 4 GB RAM (or 2 GB minimum available system memory) |
| **Hard Disk Space** | 4 GB of available storage space for application executable, GTK4 runtime, and pre-bundled 35 offline neural voice models |
| **Display** | 1280 × 768 minimum screen resolution |
| **Graphics Card & Drivers** | DirectX 11 / OpenGL 3.3 capable GPU (Intel HD Graphics 4000+, AMD Radeon R5/HD 7000+, NVIDIA GeForce 400 series or newer with standard WDDM 1.2+ drivers; Mesa llvmpipe software rasterizer supported as fallback) |
| **Audio Output** | Standard audio output device, sound card, or headphone jack (DirectSound / WASAPI on Windows, PulseAudio / PipeWire / ALSA on Linux, CoreAudio on macOS) |

### Recommended Requirements (High-Quality Voices & Batch Synthesis)
*Recommended for high-fidelity `high` quality voice models (28–32M parameters), instant book chapter audio rendering, and fast multi-tab playback.*

| Component | Recommended Specification |
| :--- | :--- |
| **Processor** | 2.5 GHz or faster quad-core (4 cores / 8 threads) or higher (Intel Core i5/i7 8th Gen+, AMD Ryzen 3000+, Snapdragon X Elite, Apple Silicon M1/M2/M3/M4) with AVX2 / FMA instruction support |
| **Operating System** | • **Windows**: Windows 11 64-bit (23H2 or newer), Windows Server 2025<br/>• **Linux**: Ubuntu 24.04 LTS+, Fedora 40+<br/>• **macOS**: macOS 14 (Sonoma) or newer |
| **Memory (RAM)** | 8 GB RAM or higher for rapid multi-tab processing and uncompressed high-fidelity audio buffers |
| **Hard Disk Space** | 8 GB of available space on a solid-state drive (NVMe SSD recommended for instant model loading and audio WAV/MP3 rendering) |
| **Display** | 1920 × 1080 (Full HD) or higher resolution with 100% or 125% DPI scaling |
| **Graphics Card & Drivers** | Dedicated or modern integrated GPU with Direct3D 12 / Vulkan / Metal support:<br/>• **NVIDIA**: GeForce GTX 1050 / RTX 2060 or newer (GeForce Game Ready / Studio Driver 535.xx or later)<br/>• **AMD**: Radeon RX 5000 / 6000 series or newer (AMD Software: Adrenalin Edition 23.x or later)<br/>• **Intel**: Intel Iris Xe Graphics, Arc A-Series, or UHD 630+ (Intel Graphics Driver 31.0.101.4000 or newer)<br/>• **Apple**: Apple Silicon Integrated GPU (M1, M2, M3, M4 with Metal 3) |
| **Audio Output** | 24-bit / 48kHz or 96kHz low-latency stereo output device or USB DAC |

---

## 📦 Installation & Downloads

Official releases are published on the **[GitHub Releases Page](https://github.com/Zackarious/ReadAloud/releases/latest)**.

> [!NOTE]
> **Multi-Volume Split File Downloads**:
> Because ReadAloud pre-bundles 35 offline neural voice models and full runtime engines (~2.4 GB uncompressed), large packages are split into 1800 MB volumes (`.001`, `.002`) to strictly adhere to GitHub's 2.0 GiB release asset ceiling. Download all numbered parts into the same folder before opening or extracting.

### 🪟 Microsoft Windows (10 / 11 / Server)

- 💽 **Windows Setup Installer (x64)**: Download all 3 setup files into the same folder, then double-click the `.exe` to run the setup wizard:
  - [`ReadAloud-1.8.19-Windows-Setup-x64.exe`](https://github.com/Zackarious/ReadAloud/releases/download/v1.8.19/ReadAloud-1.8.19-Windows-Setup-x64.exe) (Setup Launcher, 2.5 MB)
  - [`ReadAloud-1.8.19-Windows-Setup-x64-1.bin`](https://github.com/Zackarious/ReadAloud/releases/download/v1.8.19/ReadAloud-1.8.19-Windows-Setup-x64-1.bin) (Part 1 Data Slice, 1.8 GB)
  - [`ReadAloud-1.8.19-Windows-Setup-x64-2.bin`](https://github.com/Zackarious/ReadAloud/releases/download/v1.8.19/ReadAloud-1.8.19-Windows-Setup-x64-2.bin) (Part 2 Data Slice, 703 MB)
  - Full Inno Setup installer with desktop and Start Menu integration.
  - **Smart Component Detection & Auto-Download**: If either `ReadAloud-1.8.19-Windows-Setup-x64-1.bin` or `ReadAloud-1.8.19-Windows-Setup-x64-2.bin` is missing, Setup automatically detects the missing file(s) before file extraction begins, prompts for confirmation, and automatically downloads them directly from GitHub into your setup folder.
  - Pre-bundles all 35 neural voices, GTK4/Libadwaita runtimes, and MSVC 2022 libraries.
  - Supports silent enterprise installation: `ReadAloud-1.8.19-Windows-Setup-x64.exe /VERYSILENT /SUPPRESSMSGBOXES`
- 💼 **Windows Portable Edition (x64)**: Download [`ReadAloud-1.8.19-Windows-Portable-x64.7z.001`](https://github.com/Zackarious/ReadAloud/releases/latest) and [`ReadAloud-1.8.19-Windows-Portable-x64.7z.002`](https://github.com/Zackarious/ReadAloud/releases/latest) into the same folder, then extract with 7-Zip or WinRAR.
- ⚡ **Windows Portable Edition (ARM64)**: Download [`ReadAloud-1.8.19-windows-arm64-portable.zip.001`](https://github.com/Zackarious/ReadAloud/releases/latest) and [`ReadAloud-1.8.19-windows-arm64-portable.zip.002`](https://github.com/Zackarious/ReadAloud/releases/latest) into the same folder, then extract with 7-Zip, WinRAR, or Windows Explorer.
  - Native ARM64 build for Microsoft Surface Pro, Snapdragon X Elite, and Windows on ARM devices.

---

### 🐧 Linux (GNOME, KDE Plasma, XFCE & All Environments)

ReadAloud is fully supported across all Linux distributions and desktop environments.

#### Native Debian / Ubuntu Package (`.deb`)
Download the official `.deb` package from the **[Releases Page](https://github.com/Zackarious/ReadAloud/releases/latest)**:
```bash
# Install via APT (automatically resolves system dependencies)
sudo apt update
sudo apt install ./readaloud_1.8.19_amd64.deb

# Launch ReadAloud
readaloud
```

#### Standalone Linux AppImage (`.AppImage`)
Download the standalone AppImage launcher directly:
- [`ReadAloud-1.8.19-linux-x86_64.AppImage`](https://github.com/Zackarious/ReadAloud/releases/download/v1.8.19/ReadAloud-1.8.19-linux-x86_64.AppImage) (Standalone Launcher, ~1 MB)

Launch directly:
```bash
# Make executable and launch
chmod +x ReadAloud-1.8.19-linux-x86_64.AppImage
./ReadAloud-1.8.19-linux-x86_64.AppImage
```

- **Smart Component Detection & Auto-Download**: If either data slice (`ReadAloud-1.8.19-linux-x86_64.AppImage.001` or `ReadAloud-1.8.19-linux-x86_64.AppImage.002`) is missing, ReadAloud automatically detects the missing components on launch, prompts with an interactive GUI dialog (or terminal prompt), and automatically downloads them directly from GitHub into your folder with visual progress reporting before assembling the offline runtime.
- **Manual Download (Alternative)**: Download both data slices into the same folder alongside the AppImage before running:
  - [`ReadAloud-1.8.19-linux-x86_64.AppImage.001`](https://github.com/Zackarious/ReadAloud/releases/download/v1.8.19/ReadAloud-1.8.19-linux-x86_64.AppImage.001) (Part 1 Data Slice, 1.8 GB)
  - [`ReadAloud-1.8.19-linux-x86_64.AppImage.002`](https://github.com/Zackarious/ReadAloud/releases/download/v1.8.19/ReadAloud-1.8.19-linux-x86_64.AppImage.002) (Part 2 Data Slice, 535 MB)

---

### 🍏 Apple macOS (Apple Silicon & Intel)

#### Standalone macOS Universal Application (`.zip`)
Download the multi-volume macOS Universal split files from the **[Releases Page](https://github.com/Zackarious/ReadAloud/releases/latest)**:
- [`ReadAloud-1.8.19-macos-universal.zip.001`](https://github.com/Zackarious/ReadAloud/releases/latest)
- [`ReadAloud-1.8.19-macos-universal.zip.002`](https://github.com/Zackarious/ReadAloud/releases/latest)

Extract and run:
```bash
# Extract multi-volume zip using 7-Zip, The Unarchiver, or Terminal:
7z x ReadAloud-1.8.19-macos-universal.zip.001
# Or in Terminal:
cat ReadAloud-1.8.19-macos-universal.zip.* > ReadAloud.zip && unzip ReadAloud.zip

# Move ReadAloud.app to Applications
mv ReadAloud.app /Applications/
```

#### From Flathub (Recommended)

ReadAloud is available as a verified sandboxed Flatpak on Flathub:

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

## 🧪 Automated Testing & Quality Assurance Suite

### Purpose of Testing
Automated testing in ReadAloud serves as the bedrock of application stability, security, and performance across diverse desktop operating systems. Because ReadAloud unites real-time on-device neural text-to-speech synthesis with a reactive GTK 4 and Libadwaita user interface, comprehensive test coverage is essential to guarantee that every subsystem performs predictably under intensive workloads. The test suite thoroughly validates the entire audio synthesis pipeline, from local ONNX model discovery, voice inference, and calibrated playback speeds to pitch preservation and multi-format audio encoding in MP3, WAV, OGG, and FLAC. It rigorously exercises document parsing across plain text, Markdown, PDF, and EPUB files, ensuring that chapter extraction, symbol cleansing, and intelligent sentence segmentation function flawlessly without dropping text or creating unnatural pauses. Furthermore, the tests verify thread-safe coordination between background audio generation workers and the main GTK application loop, confirming that progress HUDs, cancellation signals, and dynamic word highlighting remain synchronized without race conditions or memory leaks. Integration tests also simulate network resilience, validating Wikimedia REST API autocomplete suggestions, weekly Top 25 Report scraping, in-memory thumbnail caching, and graceful offline fallbacks. By maintaining regression resistance across every core subsystem, automated testing guarantees an ethical, completely offline, and dependable reading companion for every user.

### Test Execution & Results Summary

Automated testing was conducted on **14 November 2026** alongside the release of version **v1.8.19**. A total of **333 tests** were executed across the entire test suite covering 28 test modules. **333 tests passed and 0 tests failed** (0 errors), achieving a **100% pass rate** in approximately 5.7 seconds.

| Metric | Result |
| :--- | :--- |
| **Date Conducted** | 14 November 2026 |
| **Target Version** | ReadAloud v1.8.19 |
| **Total Tests Conducted** | **333** |
| **Tests Passed** | **333 (100%)** |
| **Tests Failed** | **0 (0%)** |
| **Errors** | **0** |
| **Execution Duration** | 5.72 seconds |
| **Test Runner** | Python `unittest` (`python3 -m unittest discover -s tests`) |

### Test Suite Module Breakdown

| Test Module | Focus Area / Subsystem | Tests Conducted | Passed | Failed |
| :--- | :--- | :---: | :---: | :---: |
| `tests/test_about_window.py` | About dialog metadata, version parity, and GPLv3 attribution | 7 | 7 | 0 |
| `tests/test_appimage_launcher.py` | Standalone AppImage launcher slice detection, assembly, and desktop integration | 7 | 7 | 0 |
| `tests/test_audio_playback_fallback.py` | Audio pipeline fallbacks across GStreamer and SoundDevice drivers | 8 | 8 | 0 |
| `tests/test_auto_remove_tags_and_font_popup.py` | XML/HTML tag stripping, cleanup regexes, and font zoom capsule | 19 | 19 | 0 |
| `tests/test_bubble.py` | Word tracking bubble geometry, layout coordinates, and highlight tags | 37 | 37 | 0 |
| `tests/test_button_recolour.py` | Signature highlight yellow `#f6d32d` button styling and states | 5 | 5 | 0 |
| `tests/test_cached_playback.py` | Audio chunk caching, buffer memory reuse, and repeat playback | 7 | 7 | 0 |
| `tests/test_demos.py` | Preset voice demo scripts, speed/pitch configurations, and overwrite guards | 6 | 6 | 0 |
| `tests/test_document_importer.py` | Multi-format file ingestion, EPUB chapter extraction, and text decoding | 6 | 6 | 0 |
| `tests/test_drag_and_drop.py` | File dropzone signaling, multi-file queuing, and drag hover feedback | 18 | 18 | 0 |
| `tests/test_dropdown_full_text.py` | Dropdown text label overflow protection and ellipsis handling | 2 | 2 | 0 |
| `tests/test_editable_during_playback.py` | Document editor read-only locking and post-playback restoration | 1 | 1 | 0 |
| `tests/test_error_logger.py` | Structured crash logging, diagnostics formatting, and log rotation | 11 | 11 | 0 |
| `tests/test_export_filename.py` | Audio export path sanitization and multi-format filename generation | 5 | 5 | 0 |
| `tests/test_fixed_pitch_and_dropdown_tick.py` | Pitch preservation across speed changes and active menu checkmarks | 4 | 4 | 0 |
| `tests/test_generation_cancellation.py` | Instant worker cancellation, background thread termination, and HUD reset | 6 | 6 | 0 |
| `tests/test_highlight_and_language_tick.py` | Dynamic word highlight tag lifecycle and language radio checkmarks | 8 | 8 | 0 |
| `tests/test_paths.py` | Cross-platform model paths, user directories, and GResource locations | 6 | 6 | 0 |
| `tests/test_pause_voice_switch.py` | Playback pause/resume cycles, voice hot-swapping, and position markers | 10 | 10 | 0 |
| `tests/test_playback_seek_buttons.py` | Backward and forward 15-second skip buttons and seek boundaries | 10 | 10 | 0 |
| `tests/test_shortcuts.py` | Keyboard accelerators (`Space`, `Escape`, `Ctrl+O`, `Ctrl+S`, `Ctrl+T`) | 16 | 16 | 0 |
| `tests/test_speed_dropdown.py` | Speech speed menu items (`Slower` through `Super Fast`) and model rates | 6 | 6 | 0 |
| `tests/test_system_integrity.py` | Model discovery, metadata validation, and ONNX Runtime environment checks | 12 | 12 | 0 |
| `tests/test_tab_navigation_buttons.py` | Tab bar hover chevrons, auto-scroll positioning, and crossfade signals | 6 | 6 | 0 |
| `tests/test_tab_system.py` | Multi-tab document management, tab reordering, and close confirmation | 19 | 19 | 0 |
| `tests/test_text_tools.py` | Sentence segmentation, symbol cleansing, paragraph gaps, and hyphenation | 56 | 56 | 0 |
| `tests/test_wikipedia_importer.py` | REST API autocomplete, Top 25 table scraping, and thumbnail caching | 25 | 25 | 0 |
| `tests/test_word_wrap.py` | TextView margin calculations, word wrapping, and window resize adaptability | 10 | 10 | 0 |
| **Total Test Suite** | **Comprehensive Full System & Regression Validation** | **333** | **333** | **0** |

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
