# Wavespeed AI - SeedVR2 Upscaler for Forge

![License](https://img.shields.io/badge/License-MIT-green.svg) ![Platform](https://img.shields.io/badge/Platform-SD%20WebUI%20Forge-blue.svg) ![Cost](https://img.shields.io/badge/Cost-%240.01%2Fupscale-yellow.svg)

A dedicated extension for **Stable Diffusion WebUI Forge** that integrates the Wavespeed AI (https://wavespeed.ai) **SeedVR2 Upscaler**. This tool allows you to seamlessly upscale your generated images to **2k, 4k, or 8k** resolution directly within the Forge interface for just **$0.01 USD per upscale**.

It features a streamlined workflow with "Grab Last Generated" functionality, a built-in aspect ratio corrector (center crop), and a **0.35 Megapixel optimizer** to ensure the highest possible texture quality from the SeedVR2 model.

---

## 🚀 Features

* **Ultra-Low Cost**: Professional grade upscaling for only **$0.01 USD per image**.
* **High-Fidelity Results**: Leverage SeedVR2 to upscale images to **2k, 4k, or 8k**.
* **0.35MP Optimization**: New **"Downscale to 0.35MP"** toggle. This pre-processes images to the model's "sweet spot," preventing waxy textures and maximizing skin/surface detail.
* **Format Flexibility**: Export results as **PNG, JPEG, or WEBP**.
* **Workflow Integration**: Instantly load the most recent image from your `txt2img` or `img2img` output folders with a single click.
* **Aspect Ratio Fixer**: Optional **Center Crop** tool to correct resolutions (e.g., trimming 1920x1088 to 1920x1080).
* **Auto-Save**: All upscaled results are automatically saved to your Forge `outputs/extras-images` folder.

---

## 📥 Installation

### Method 1: Install via Extension URL
1. Open **WebUI Forge**.
2. Navigate to the **Extensions** tab -> **Install from URL**.
3. Paste the repository URL: `https://github.com/sdprompts/forge-wavespeed-seedvr2-upscaler`
4. Click **Install**.
5. Go to the **Installed** tab and click **Apply and Restart UI**.

---

## 🔄 Updating the Extension

To ensure you have the latest features (like the 0.35MP downscaling option), use one of the following methods:

### Method 1: Via the Forge Interface (Recommended)
1. Navigate to the **Extensions** tab.
2. Go to the **Installed** sub-tab.
3. Click the **Check for updates** button.
4. If an update is available, click **Apply and restart UI**.

### Method 2: Via Command Line (Manual)
1. Open your terminal or CMD in the extension folder:
   `stable-diffusion-webui-forge/extensions/forge-wavespeed-seedvr2-upscaler`
2. Run the following command:
   `git pull`
3. Restart Forge.

---

## ⚙️ Configuration

1. Open Forge and go to the **Settings** tab.
2. Select **Wavespeed AI** from the sidebar.
3. Paste your key into the **Wavespeed API Key** field and click **Apply Settings**.

---

## 🖥️ Usage Guide

1. **Open the Tab**: Click on the **Wavespeed AI** tab in Forge.
2. **Select Input**: Use **"📅 Grab Last Generated Image"** or upload a file.
3. **Adjust Pre-Processing**:
   * **Downscale to 0.35MP**: (Recommended) Keep this checked to avoid "waxy" AI artifacts.
   * **Pre-Upscale Crop**: (Optional) Trims extra pixels from non-standard generations.
4. **Select Target**: Choose **2k, 4k, or 8k**.
5. **Upscale**: Click the **Upscale** button.

---

## 📜 License
This project is licensed under the MIT License.
