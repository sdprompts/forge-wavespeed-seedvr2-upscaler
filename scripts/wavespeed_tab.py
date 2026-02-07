import gradio as gr
import requests
import json
import time
import base64
import os
import math
from io import BytesIO
from PIL import Image

# --- Forge/A1111 Imports ---
from modules import script_callbacks, shared, images, ui_components

# --- Configuration ---
API_URL = "https://api.wavespeed.ai/api/v3/wavespeed-ai/seedvr2/image"

def image_to_base64(image):
    """Converts a PIL Image to a base64 data URI."""
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{img_str}"

def scale_to_total_pixels(img, target_pixels=350000):
    """
    Resizes image to approximately 0.35MP while maintaining aspect ratio.
    Using LANCZOS to prevent 'waxy' artifacts during the subsequent AI upscale.
    """
    w, h = img.size
    aspect_ratio = w / h
    # Calculate new height: h = sqrt(target / aspect)
    new_h = math.sqrt(target_pixels / aspect_ratio)
    new_w = new_h * aspect_ratio
    
    return img.resize((int(new_w), int(new_h)), Image.LANCZOS)

def center_crop_pil(img, target_w, target_h):
    """Centers and crops the image to target dimensions."""
    w, h = img.size
    if target_w > w or target_h > h:
        return img
    left = (w - target_w) / 2
    top = (h - target_h) / 2
    right = (w + target_w) / 2
    bottom = (h + target_h) / 2
    return img.crop((left, top, right, bottom))

def get_latest_generated_image():
    """Scans output folders to find the most recent image."""
    paths = [
        shared.opts.outdir_txt2img_samples or os.path.join(os.getcwd(), "outputs", "txt2img-images"),
        shared.opts.outdir_img2img_samples or os.path.join(os.getcwd(), "outputs", "img2img-images"),
    ]

    latest_file = None
    latest_time = 0

    for path in paths:
        if os.path.exists(path):
            for root, dirs, files in os.walk(path):
                for file in files:
                    if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                        full_path = os.path.join(root, file)
                        try:
                            mtime = os.path.getmtime(full_path)
                            if mtime > latest_time:
                                latest_time = mtime
                                latest_file = full_path
                        except OSError:
                            continue
    
    if latest_file:
        return Image.open(latest_file)
    else:
        return None

def upscale_image(api_key_input, input_image, image_url_input, resolution, out_fmt, enable_crop, crop_w, crop_h, enable_downscale):
    # 1. API Key Auth
    api_key = api_key_input.strip() if api_key_input else getattr(shared.opts, "wavespeed_api_key", "")
    if not api_key:
        return None, "Error: Please enter your API Key in the box or in Settings."

    # 2. Source Handling & Pre-processing
    target_image = ""
    
    if image_url_input and image_url_input.strip():
        target_image = image_url_input.strip()
    elif input_image is not None:
        processed_img = input_image.copy()
        
        # Apply Center Crop if enabled
        if enable_crop:
            try:
                processed_img = center_crop_pil(processed_img, int(crop_w), int(crop_h))
            except Exception as e:
                return None, f"Crop Error: {str(e)}"
        
        # Apply 0.35MP Downscale if enabled (The "Magic" Step)
        if enable_downscale:
            try:
                processed_img = scale_to_total_pixels(processed_img, 350000)
            except Exception as e:
                return None, f"Downscale Error: {str(e)}"

        target_image = image_to_base64(processed_img)
    else:
        return None, "Error: Please upload an image or provide an Image URL."

    # 3. API Payload
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    payload = {
        "image": target_image,
        "target_resolution": resolution, 
        "output_format": out_fmt,
        "enable_base64_output": False,
        "enable_sync_mode": False
    }

    try:
        # Submit Task
        response = requests.post(API_URL, headers=headers, data=json.dumps(payload))
        if response.status_code != 200:
            return None, f"Submission Error {response.status_code}: {response.text}"
            
        data = response.json().get("data", {})
        request_id = data.get("id")
        
        if not request_id:
            return None, "Error: No Request ID received."

        # Poll for Results
        status_url = f"https://api.wavespeed.ai/api/v3/predictions/{request_id}/result"
        headers_poll = {"Authorization": f"Bearer {api_key}"}
        
        start_time = time.time()
        timeout = 180 # Increased timeout for higher resolutions
        
        while True:
            if time.time() - start_time > timeout:
                return None, "Error: Operation timed out."
                
            poll_res = requests.get(status_url, headers=headers_poll)
            if poll_res.status_code != 200:
                return None, f"Polling Error: {poll_res.text}"
            
            res_data = poll_res.json().get("data", {})
            status = res_data.get("status")
            
            if status == "completed":
                outputs = res_data.get("outputs", [])
                if outputs:
                    result_url = outputs[0]
                    img_res = requests.get(result_url)
                    if img_res.status_code == 200:
                        ret_img = Image.open(BytesIO(img_res.content))
                        
                        # Auto-Save to Forge Extras Folder
                        out_dir = shared.opts.outdir_extras_samples or os.path.join(os.getcwd(), "outputs", "extras-images")
                        images.save_image(
                            image=ret_img,
                            path=out_dir,
                            basename="",
                            seed=None,
                            prompt=None,
                            extension=out_fmt.lower(),
                            suffix="-wavespeed-upscale",
                            forced_filename=None
                        )
                        return ret_img, f"Success! Saved to {out_dir}"
                    else:
                        return None, "Error: Could not download result image."
                else:
                    return None, "Error: Completed but no output found."
            
            elif status == "failed":
                return None, f"Task Failed: {res_data.get('error')}"
            
            time.sleep(2) # Poll every 2 seconds to reduce API overhead

    except Exception as e:
        return None, f"System Error: {str(e)}"

# --- UI SETTINGS REGISTRATION ---
def on_ui_settings():
    section = ('wavespeed', "Wavespeed AI")
    shared.opts.add_option(
        "wavespeed_api_key",
        shared.OptionInfo("", "Wavespeed API Key", gr.Textbox, {"type": "password"}, section=section)
    )

def on_ui_tabs():
    saved_key = getattr(shared.opts, "wavespeed_api_key", "")

    with gr.Blocks(analytics_enabled=False) as wavespeed_interface:
        with gr.Row():
            with gr.Column():
                gr.Markdown("### 🌊 Wavespeed AI - SeedVR2 Upscaler")
                
                api_input = gr.Textbox(
                    label="API Key", 
                    value=saved_key, 
                    type="password", 
                    placeholder="Leave empty to use Settings value"
                )
                
                with gr.Row():
                    res_input = gr.Dropdown(label="Target Resolution", choices=["2k", "4k", "8k"], value="4k")
                    fmt_input = gr.Radio(label="Output Format", choices=["jpeg", "png", "webp"], value="png")

                # --- PRE-PROCESSING OPTIONS ---
                with gr.Accordion("⚙️ Pre-Processing (Recommended)", open=True):
                    downscale_chk = gr.Checkbox(
                        label="Downscale to 0.35MP (Optimizes SeedVR2 details)", 
                        value=True
                    )
                    crop_chk = gr.Checkbox(label="Enable Center Crop (Fix Aspect Ratio)", value=False)
                    with gr.Row():
                        crop_w = gr.Number(label="Crop Width", value=1920, precision=0)
                        crop_h = gr.Number(label="Crop Height", value=1080, precision=0)

                with gr.Tab("Upload / Local"):
                    with gr.Row():
                        grab_btn = gr.Button("📅 Grab Last Generated Image", variant="secondary")
                    img_input = gr.Image(label="Input Image", type="pil")
                
                with gr.Tab("Image URL"):
                    url_input = gr.Textbox(label="Image URL", placeholder="https://...")
                
                upscale_btn = gr.Button("Upscale", variant="primary")

            with gr.Column():
                img_output = gr.Image(label="Upscaled Result", type="pil")
                status_output = gr.Label(label="Status")

        grab_btn.click(fn=get_latest_generated_image, inputs=None, outputs=img_input)

        upscale_btn.click(
            fn=upscale_image,
            inputs=[
                api_input, img_input, url_input, res_input, fmt_input, 
                crop_chk, crop_w, crop_h, downscale_chk
            ],
            outputs=[img_output, status_output]
        )

    return [(wavespeed_interface, "Wavespeed AI", "wavespeed_ai_tab")]

script_callbacks.on_ui_settings(on_ui_settings)
script_callbacks.on_ui_tabs(on_ui_tabs)
