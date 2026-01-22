import gradio as gr
import requests
import json
import time
import base64
import os
import glob
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

def center_crop_pil(img, target_w, target_h):
    """
    Centers and crops the image to target dimensions.
    Used to trim 1920x1088 -> 1920x1080.
    """
    w, h = img.size
    
    # If the image is smaller than the target crop, return original to avoid errors
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

def upscale_image(api_key_input, input_image, image_url_input, resolution, out_fmt, enable_crop, crop_w, crop_h):
    # 1. Try Input Box, 2. Try Settings
    api_key = api_key_input.strip() if api_key_input else getattr(shared.opts, "wavespeed_api_key", "")
    
    if not api_key:
        return None, "Error: Please enter your API Key in the box or in Settings."

    # Determine Source
    target_image = ""
    
    # Logic: If using URL, we can't local crop easily. If using Input Image (PIL), we crop.
    if image_url_input and image_url_input.strip():
        target_image = image_url_input.strip()
        # Note: We cannot crop a remote URL unless we download it first. 
        # Assuming URL takes precedence and skips crop, or user must download it to 'img_input' first.
    elif input_image is not None:
        # --- CROP LOGIC START ---
        if enable_crop:
            try:
                input_image = center_crop_pil(input_image, int(crop_w), int(crop_h))
            except Exception as e:
                return None, f"Crop Error: {str(e)}"
        # --- CROP LOGIC END ---

        target_image = image_to_base64(input_image)
    else:
        return None, "Error: Please upload an image or provide an Image URL."

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
        timeout = 120 
        
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
                        
                        # Auto-Save
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
            
            time.sleep(1)

    except Exception as e:
        return None, f"System Error: {str(e)}"

# --- UI SETTINGS REGISTRATION ---
def on_ui_settings():
    section = ('wavespeed', "Wavespeed AI")
    shared.opts.add_option(
        "wavespeed_api_key",
        shared.OptionInfo(
            "", 
            "Wavespeed API Key", 
            gr.Textbox, 
            {"type": "password"}, 
            section=section
        )
    )

def on_ui_tabs():
    # Load default from settings if available
    saved_key = getattr(shared.opts, "wavespeed_api_key", "")

    with gr.Blocks(analytics_enabled=False) as wavespeed_interface:
        with gr.Row():
            with gr.Column():
                gr.Markdown("### 🌊 Wavespeed AI - SeedVR2 Upscaler")
                
                # The input box defaults to the saved setting
                api_input = gr.Textbox(
                    label="API Key", 
                    value=saved_key, 
                    type="password", 
                    placeholder="Leave empty to use Settings value"
                )
                
                with gr.Row():
                    res_input = gr.Dropdown(label="Target Resolution", choices=["2k", "4k", "8k"], value="4k")
                    fmt_input = gr.Radio(label="Output Format", choices=["jpeg", "png", "webp"], value="png")

                # --- NEW CROP UI ---
                with gr.Accordion("✂️ Pre-Upscale Crop (Fix Aspect Ratio)", open=False):
                    crop_chk = gr.Checkbox(label="Enable Center Crop", value=True)
                    with gr.Row():
                        crop_w = gr.Number(label="Crop Width", value=1920, precision=0)
                        crop_h = gr.Number(label="Crop Height", value=1080, precision=0)
                # -------------------

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
            # Added new inputs to the list: crop_chk, crop_w, crop_h
            inputs=[api_input, img_input, url_input, res_input, fmt_input, crop_chk, crop_w, crop_h],
            outputs=[img_output, status_output]
        )

    return [(wavespeed_interface, "Wavespeed AI", "wavespeed_ai_tab")]

script_callbacks.on_ui_settings(on_ui_settings)
script_callbacks.on_ui_tabs(on_ui_tabs)