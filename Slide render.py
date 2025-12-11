# slide_renderer.py
import os
import win32com.client
import pythoncom
import uuid
import tempfile
from utils import logger

def export_slides_to_png(ppt_path: str):
    """
    Exports all slides of ppt_path into PNG images using PowerPoint COM.
    Returns a list of PNG file paths in correct order.
    """
    try:
        pythoncom.CoInitialize()
        powerpoint = win32com.client.Dispatch("PowerPoint.Application")
        powerpoint.Visible = 0

        pres = powerpoint.Presentations.Open(ppt_path, WithWindow=False)

        out_dir = os.path.join(tempfile.gettempdir(), f"slides_{uuid.uuid4().hex}")
        os.makedirs(out_dir, exist_ok=True)

        # Export all slides as Slide1.PNG, Slide2.PNG...
        pres.Export(out_dir, "PNG")

        pres.Close()
        powerpoint.Quit()
        pythoncom.CoUninitialize()

        # Collect slide images sorted by slide number
        files = sorted([os.path.join(out_dir, f) for f in os.listdir(out_dir) if f.lower().endswith(".png")])
        return files

    except Exception as e:
        logger.exception(f"PowerPoint export failed: {e}")
        return []
