import uuid
import json
import os
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Excalidraw Generator API")

FILE_PATH = "/workspace/infra-llm-rag.json"

# Layout Constants
COL_WIDTH = 250
ROW_HEIGHT = 150
COL_START_MARGIN = 50
ROW_START_MARGIN = 200

# Color Mapping
COLOR_MAP = {
    "blue": {"stroke": "#3b82f6", "bg": "#1e293b"},
    "purple": {"stroke": "#8b5cf6", "bg": "#1e293b"},
    "green": {"stroke": "#10b981", "bg": "#1e293b"},
    "yellow": {"stroke": "#eab308", "bg": "#1e293b"},
    "orange": {"stroke": "#f97316", "bg": "#1e293b"},
    "pink": {"stroke": "#ec4899", "bg": "#1e293b"},
    "rose": {"stroke": "#f43f5e", "bg": "#1e293b"},
    "slate": {"stroke": "#64748b", "bg": "#1e293b"},
}

def load_scene() -> Dict[str, Any]:
    if os.path.exists(FILE_PATH):
        try:
            with open(FILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "type": "excalidraw",
        "version": 2,
        "source": "https://excalidraw.com",
        "elements": [],
        "appState": {
            "theme": "dark",
            "viewBackgroundColor": "#0b0f19"
        },
        "files": {}
    }

def save_scene(scene: Dict[str, Any]):
    # Save to JSON
    with open(FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(scene, f, indent=2, ensure_ascii=False)
    
    # Also save to .excalidraw duplicate
    excalidraw_path = FILE_PATH.replace(".json", ".excalidraw")
    with open(excalidraw_path, "w", encoding="utf-8") as f:
        json.dump(scene, f, indent=2, ensure_ascii=False)

class NodeRequest(BaseModel):
    label: str
    type: str = "rectangle"
    column: int
    row: int
    color_type: str = "blue"

class ConnectRequest(BaseModel):
    source_id: str
    target_id: str
    label: Optional[str] = None
    style: Optional[str] = "orthogonal"

class FrameRequest(BaseModel):
    title: str
    start_col: int
    start_row: int
    end_col: int
    end_row: int

class TitleRequest(BaseModel):
    title: str
    subtitle: Optional[str] = None

@app.get("/scene")
def get_scene():
    return load_scene()

@app.post("/clear")
def clear_scene():
    scene = {
        "type": "excalidraw",
        "version": 2,
        "source": "https://excalidraw.com",
        "elements": [],
        "appState": {
            "theme": "dark",
            "viewBackgroundColor": "#0b0f19"
        },
        "files": {}
    }
    save_scene(scene)
    return {"status": "success", "message": "Scene cleared"}

@app.post("/title")
def set_title(req: TitleRequest):
    scene = load_scene()
    
    # Remove existing title_text and subtitle_text if any
    scene["elements"] = [el for el in scene["elements"] if el["id"] not in ("title_text", "subtitle_text")]
    
    title_el = {
        "id": "title_text",
        "type": "text",
        "x": 50,
        "y": 50,
        "width": 800,
        "height": 40,
        "strokeColor": "#f8fafc",
        "backgroundColor": "transparent",
        "fillStyle": "hachure",
        "strokeWidth": 1,
        "roughness": 0,
        "opacity": 100,
        "text": req.title,
        "fontSize": 24,
        "fontFamily": 2,
        "textAlign": "left",
        "verticalAlign": "middle"
    }
    scene["elements"].insert(0, title_el)
    
    if req.subtitle:
        sub_el = {
            "id": "subtitle_text",
            "type": "text",
            "x": 50,
            "y": 90,
            "width": 800,
            "height": 24,
            "strokeColor": "#94a3b8",
            "backgroundColor": "transparent",
            "fillStyle": "hachure",
            "strokeWidth": 1,
            "roughness": 0,
            "opacity": 100,
            "text": req.subtitle,
            "fontSize": 14,
            "fontFamily": 2,
            "textAlign": "left",
            "verticalAlign": "middle"
        }
        scene["elements"].insert(1, sub_el)
        
    save_scene(scene)
    return {"status": "success", "message": "Title updated"}

@app.post("/node")
def add_node(req: NodeRequest):
    scene = load_scene()
    
    w = 180
    h = 80
    
    # Calculate X and Y coordinates
    x = COL_START_MARGIN + (req.column - 1) * COL_WIDTH + (COL_WIDTH - w) / 2
    y = ROW_START_MARGIN + (req.row - 1) * ROW_HEIGHT + (ROW_HEIGHT - h) / 2
    
    color = COLOR_MAP.get(req.color_type.lower(), COLOR_MAP["blue"])
    
    node_id = f"node_{uuid.uuid4().hex[:8]}"
    text_id = f"text_{uuid.uuid4().hex[:8]}"
    
    # Create the node container shape
    rect = {
        "id": node_id,
        "type": "rectangle",
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "strokeColor": color["stroke"],
        "backgroundColor": color["bg"],
        "fillStyle": "solid",
        "strokeWidth": 2,
        "roughness": 0,
        "roundness": { "type": 3 },
        "opacity": 100,
        "boundElements": [{"type": "text", "id": text_id}]
    }
    
    # Create the inner text label
    text = {
        "id": text_id,
        "type": "text",
        "x": x + 10,
        "y": y + 20,
        "width": w - 20,
        "height": h - 40,
        "strokeColor": "#f8fafc",
        "backgroundColor": "transparent",
        "fillStyle": "hachure",
        "strokeWidth": 1,
        "roughness": 0,
        "opacity": 100,
        "text": req.label,
        "fontSize": 14,
        "fontFamily": 2,
        "textAlign": "center",
        "verticalAlign": "middle",
        "containerId": node_id
    }
    
    scene["elements"].append(rect)
    scene["elements"].append(text)
    
    # Auto-assign to any frame that spans this coordinate
    for el in scene["elements"]:
        if el["type"] == "frame":
            fx, fy, fw, fh = el["x"], el["y"], el["width"], el["height"]
            cx, cy = x + w / 2, y + h / 2
            if fx <= cx <= (fx + fw) and fy <= cy <= (fy + fh):
                rect["frameId"] = el["id"]
                text["frameId"] = el["id"]
                break
                
    save_scene(scene)
    return {"status": "success", "node_id": node_id, "text_id": text_id}

@app.post("/connect")
def connect_nodes(req: ConnectRequest):
    scene = load_scene()
    
    source = None
    target = None
    for el in scene["elements"]:
        if el["id"] == req.source_id:
            source = el
        elif el["id"] == req.target_id:
            target = el
            
    if not source or not target:
        raise HTTPException(status_code=404, detail="Source or target element not found")
        
    x1, y1 = source["x"], source["y"]
    w1, h1 = source["width"], source["height"]
    x2, y2 = target["x"], target["y"]
    w2, h2 = target["width"], target["height"]
    
    cx1, cy1 = x1 + w1 / 2, y1 + h1 / 2
    cx2, cy2 = x2 + w2 / 2, y2 + h2 / 2
    
    # Smart edge anchoring
    if x1 + w1 < x2:
        start_x, start_y = x1 + w1, cy1
        end_x, end_y = x2, cy2
    elif x2 + w2 < x1:
        start_x, start_y = x1, cy1
        end_x, end_y = x2 + w2, cy2
    elif y1 + h1 < y2:
        start_x, start_y = cx1, y1 + h1
        end_x, end_y = cx2, y2
    else:
        start_x, start_y = cx1, y1
        end_x, end_y = cx2, y2 + h2
        
    arrow_id = f"arrow_{uuid.uuid4().hex[:8]}"
    
    # Routing style
    if req.style == "orthogonal" and abs(start_x - end_x) > 20 and abs(start_y - end_y) > 20:
        mid_x = start_x + (end_x - start_x) / 2
        dx1 = mid_x - start_x
        dy1 = 0
        dx2 = 0
        dy2 = end_y - start_y
        dx3 = end_x - mid_x
        dy3 = 0
        
        points = [
            [0, 0],
            [dx1, dy1],
            [dx1 + dx2, dy1 + dy2],
            [dx1 + dx2 + dx3, dy1 + dy2 + dy3]
        ]
    else:
        points = [
            [0, 0],
            [end_x - start_x, end_y - start_y]
        ]
        
    arrow = {
        "id": arrow_id,
        "type": "arrow",
        "x": start_x,
        "y": start_y,
        "width": abs(end_x - start_x),
        "height": abs(end_y - start_y),
        "strokeColor": "#64748b",
        "strokeWidth": 2,
        "roughness": 0,
        "opacity": 100,
        "points": points,
        "endArrowhead": "arrow",
        "startBinding": {"elementId": req.source_id, "focus": 0, "gap": 2},
        "endBinding": {"elementId": req.target_id, "focus": 0, "gap": 2}
    }
    
    # Bind arrow to elements
    if "boundElements" not in source or source["boundElements"] is None:
        source["boundElements"] = []
    source["boundElements"].append({"type": "arrow", "id": arrow_id})
    
    if "boundElements" not in target or target["boundElements"] is None:
        target["boundElements"] = []
    target["boundElements"].append({"type": "arrow", "id": arrow_id})
    
    scene["elements"].append(arrow)
    
    # Add label if specified
    if req.label:
        label_id = f"label_{uuid.uuid4().hex[:8]}"
        if len(points) == 4:
            mx = start_x + points[2][0]
            my = start_y + points[2][1] - 20
        else:
            mx = start_x + (end_x - start_x) / 2
            my = start_y + (end_y - start_y) / 2 - 20
            
        label = {
            "id": label_id,
            "type": "text",
            "x": mx - 50,
            "y": my,
            "width": 100,
            "height": 20,
            "strokeColor": "#94a3b8",
            "backgroundColor": "transparent",
            "fillStyle": "hachure",
            "strokeWidth": 1,
            "roughness": 0,
            "opacity": 100,
            "text": req.label,
            "fontSize": 11,
            "fontFamily": 2,
            "textAlign": "center",
            "verticalAlign": "middle"
        }
        scene["elements"].append(label)
        
    save_scene(scene)
    return {"status": "success", "arrow_id": arrow_id}

@app.post("/frame")
def create_boundary_frame(req: FrameRequest):
    scene = load_scene()
    
    # Bounding box calculations with paddings
    frame_x = COL_START_MARGIN + (req.start_col - 1) * COL_WIDTH - 20
    frame_y = ROW_START_MARGIN + (req.start_row - 1) * ROW_HEIGHT - 30
    
    end_x = COL_START_MARGIN + req.end_col * COL_WIDTH - 20
    end_y = ROW_START_MARGIN + req.end_row * ROW_HEIGHT - 10
    
    frame_w = end_x - frame_x
    frame_h = end_y - frame_y
    
    frame_id = f"frame_{uuid.uuid4().hex[:8]}"
    
    frame = {
        "id": frame_id,
        "type": "frame",
        "x": frame_x,
        "y": frame_y,
        "width": frame_w,
        "height": frame_h,
        "strokeColor": "#475569",
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 1,
        "strokeStyle": "dashed",
        "roughness": 0,
        "roundness": { "type": 3 },
        "opacity": 40,
        "name": req.title
    }
    
    scene["elements"].append(frame)
    
    # Associate all elements inside the frame
    for el in scene["elements"]:
        if el["id"] == frame_id or el["type"] == "frame":
            continue
        if "x" in el and "y" in el:
            el_cx = el["x"] + el.get("width", 0) / 2
            el_cy = el["y"] + el.get("height", 0) / 2
            if frame_x <= el_cx <= end_x and frame_y <= el_cy <= end_y:
                el["frameId"] = frame_id
                
    save_scene(scene)
    return {"status": "success", "frame_id": frame_id}
