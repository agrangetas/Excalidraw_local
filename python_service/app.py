import uuid
import json
import os
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Excalidraw Generator API")

FILE_PATH = "/workspace/infra-llm-rag.json"

# Layout Constants
COL_WIDTH = 260
ROW_HEIGHT = 160
COL_START_MARGIN = 50
ROW_START_MARGIN = 200

# Color Mapping
COLOR_MAP = {
    "blue": {"stroke": "#3b82f6", "bg": "#1e293b"},
    "green": {"stroke": "#10b981", "bg": "#1e293b"},
    "orange": {"stroke": "#f97316", "bg": "#1e293b"},
    "red": {"stroke": "#ef4444", "bg": "#1e293b"},
    "gray": {"stroke": "#94a3b8", "bg": "#1e293b"},
    # Fallback mappings for old chart colors
    "purple": {"stroke": "#8b5cf6", "bg": "#1e293b"},
    "yellow": {"stroke": "#eab308", "bg": "#1e293b"},
    "pink": {"stroke": "#ec4899", "bg": "#1e293b"},
    "rose": {"stroke": "#f43f5e", "bg": "#1e293b"},
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

def save_scene(scene: Dict[str, Any], custom_path: Optional[str] = None):
    target_path = custom_path if custom_path else FILE_PATH
    # Save to JSON
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(scene, f, indent=2, ensure_ascii=False)
    
    # Also save to .excalidraw duplicate
    excalidraw_path = target_path.replace(".json", "").replace(".excalidraw", "") + ".excalidraw"
    with open(excalidraw_path, "w", encoding="utf-8") as f:
        json.dump(scene, f, indent=2, ensure_ascii=False)

def reverse_color(stroke_color: str) -> str:
    for k, v in COLOR_MAP.items():
        if v["stroke"].lower() == stroke_color.lower():
            return k
    return "blue"

def get_node_label(node_id: str, elements: List[Dict[str, Any]]) -> str:
    for el in elements:
        if el.get("type") == "text" and el.get("containerId") == node_id and not el.get("isDeleted"):
            return el.get("text", "")
    return ""

def recalculate_arrow(arrow: Dict[str, Any], elements: List[Dict[str, Any]]):
    source_id = arrow.get("startBinding", {}).get("elementId")
    target_id = arrow.get("endBinding", {}).get("elementId")
    if not source_id or not target_id:
        return
        
    source = next((el for el in elements if el["id"] == source_id), None)
    target = next((el for el in elements if el["id"] == target_id), None)
    if not source or not target:
        return
        
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
        
    # Maintain routing style (orthogonal or straight)
    if len(arrow.get("points", [])) == 4:
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
        
    arrow["x"] = start_x
    arrow["y"] = start_y
    arrow["width"] = abs(end_x - start_x)
    arrow["height"] = abs(end_y - start_y)
    arrow["points"] = points
    arrow["version"] = arrow.get("version", 0) + 1

    # Move label if it exists
    label_el = next((el for el in elements if el["id"] == f"label_{arrow['id']}"), None)
    if label_el:
        if len(points) == 4:
            mx = start_x + points[2][0]
            my = start_y + points[2][1] - 20
        else:
            mx = start_x + (end_x - start_x) / 2
            my = start_y + (end_y - start_y) / 2 - 20
        label_el["x"] = mx - 50
        label_el["y"] = my
        label_el["version"] = label_el.get("version", 0) + 1

class NodeRequest(BaseModel):
    label: str
    type: str = "rectangle"
    col: int
    row: int
    color: str = "blue"

class ConnectRequest(BaseModel):
    from_node_id: str
    to_node_id: str
    label: Optional[str] = None
    style: Optional[str] = "solid"

class UpdateNodeRequest(BaseModel):
    node_id: str
    new_label: Optional[str] = None
    new_col: Optional[str] = None
    new_row: Optional[str] = None
    new_color: Optional[str] = None

class DeleteNodeRequest(BaseModel):
    node_id: str

class FrameRequest(BaseModel):
    title: str
    start_col: int
    start_row: int
    end_col: int
    end_row: int

class CompileRequest(BaseModel):
    filename: str

@app.get("/layout")
def get_scene_layout():
    scene = load_scene()
    nodes = []
    connections = []
    frames = []
    
    elements = scene["elements"]
    
    for el in elements:
        if el.get("isDeleted"):
            continue
            
        el_type = el.get("type")
        if el_type in ("rectangle", "ellipse", "diamond"):
            # Calculate logical col and row
            col = round((el["x"] - COL_START_MARGIN) / COL_WIDTH)
            row = round((el["y"] - ROW_START_MARGIN) / ROW_HEIGHT)
            label = get_node_label(el["id"], elements)
            color = reverse_color(el.get("strokeColor", "#3b82f6"))
            
            nodes.append({
                "id": el["id"],
                "label": label,
                "type": el_type,
                "col": col,
                "row": row,
                "color": color
            })
            
        elif el_type == "arrow":
            from_id = el.get("startBinding", {}).get("elementId")
            to_id = el.get("endBinding", {}).get("elementId")
            if from_id and to_id:
                # Find label
                label_el = next((e for e in elements if e["id"] == f"label_{el['id']}" and not e.get("isDeleted")), None)
                label_text = label_el["text"] if label_el else ""
                
                connections.append({
                    "id": el["id"],
                    "from": from_id,
                    "to": to_id,
                    "label": label_text
                })
                
        elif el_type == "frame":
            # Reverse calculate frame grid bounds
            start_col = round((el["x"] + 20 - COL_START_MARGIN) / COL_WIDTH) + 1
            start_row = round((el["y"] + 30 - ROW_START_MARGIN) / ROW_HEIGHT) + 1
            end_col = round((el["x"] + el["width"] + 20 - COL_START_MARGIN) / COL_WIDTH)
            end_row = round((el["y"] + el["height"] + 10 - ROW_START_MARGIN) / ROW_HEIGHT)
            
            frames.append({
                "id": el["id"],
                "title": el.get("name", ""),
                "start_col": start_col,
                "start_row": start_row,
                "end_col": end_col,
                "end_row": end_row
            })
            
    return {
        "nodes": nodes,
        "connections": connections,
        "frames": frames
    }

@app.post("/node")
def add_node(req: NodeRequest):
    scene = load_scene()
    
    w = 180
    h = 80
    
    x = COL_START_MARGIN + req.col * COL_WIDTH
    y = ROW_START_MARGIN + req.row * ROW_HEIGHT
    
    color_scheme = COLOR_MAP.get(req.color.lower(), COLOR_MAP["blue"])
    
    node_id = f"node_{uuid.uuid4().hex[:8]}"
    text_id = f"text_{uuid.uuid4().hex[:8]}"
    
    rect = {
        "id": node_id,
        "type": req.type if req.type in ("rectangle", "ellipse", "diamond") else "rectangle",
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "strokeColor": color_scheme["stroke"],
        "backgroundColor": color_scheme["bg"],
        "fillStyle": "solid",
        "strokeWidth": 2,
        "roughness": 0,
        "roundness": { "type": 3 } if req.type != "ellipse" else None,
        "opacity": 100,
        "boundElements": [{"type": "text", "id": text_id}],
        "version": 1
    }
    
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
        "containerId": node_id,
        "version": 1
    }
    
    scene["elements"].append(rect)
    scene["elements"].append(text)
    
    # Auto-assign to frames
    for el in scene["elements"]:
        if el["type"] == "frame" and not el.get("isDeleted"):
            fx, fy, fw, fh = el["x"], el["y"], el["width"], el["height"]
            cx, cy = x + w / 2, y + h / 2
            if fx <= cx <= (fx + fw) and fy <= cy <= (fy + fh):
                rect["frameId"] = el["id"]
                text["frameId"] = el["id"]
                break
                
    save_scene(scene)
    return {
        "success": true,
        "node_id": node_id,
        "message": f"Node '{req.label}' successfully created at physical coordinates X:{x}, Y:{y}."
    }

@app.post("/connect")
def connect_nodes(req: ConnectRequest):
    scene = load_scene()
    
    source = None
    target = None
    for el in scene["elements"]:
        if el["id"] == req.from_node_id and not el.get("isDeleted"):
            source = el
        elif el["id"] == req.to_node_id and not el.get("isDeleted"):
            target = el
            
    if not source or not target:
        raise HTTPException(status_code=404, detail="Source or target element not found")
        
    x1, y1 = source["x"], source["y"]
    w1, h1 = source["width"], source["height"]
    x2, y2 = target["x"], target["y"]
    w2, h2 = target["width"], target["height"]
    
    cx1, cy1 = x1 + w1 / 2, y1 + h1 / 2
    cx2, cy2 = x2 + w2 / 2, y2 + h2 / 2
    
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
    
    # Calculate orthogonal path if not on the same axis
    if abs(start_x - end_x) > 20 and abs(start_y - end_y) > 20:
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
        "strokeStyle": "dashed" if req.style == "dashed" else "solid",
        "roughness": 0,
        "opacity": 100,
        "points": points,
        "endArrowhead": "arrow",
        "startBinding": {"elementId": req.from_node_id, "focus": 0, "gap": 2},
        "endBinding": {"elementId": req.to_node_id, "focus": 0, "gap": 2},
        "version": 1
    }
    
    if "boundElements" not in source or source["boundElements"] is None:
        source["boundElements"] = []
    source["boundElements"].append({"type": "arrow", "id": arrow_id})
    
    if "boundElements" not in target or target["boundElements"] is None:
        target["boundElements"] = []
    target["boundElements"].append({"type": "arrow", "id": arrow_id})
    
    scene["elements"].append(arrow)
    
    if req.label:
        label_id = f"label_{arrow_id}"
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
            "verticalAlign": "middle",
            "version": 1
        }
        scene["elements"].append(label)
        
    save_scene(scene)
    return {
        "success": true,
        "connection_id": arrow_id,
        "message": f"Successfully linked {req.from_node_id} to {req.to_node_id} with a {req.style} arrow."
    }

@app.post("/update_node")
def update_node(req: UpdateNodeRequest):
    scene = load_scene()
    
    container = next((el for el in scene["elements"] if el["id"] == req.node_id and not el.get("isDeleted")), None)
    if not container:
        raise HTTPException(status_code=404, detail="Node not found")
        
    text = next((el for el in scene["elements"] if el.get("containerId") == req.node_id and not el.get("isDeleted")), None)
    
    mutated_fields = []
    
    # 1. Update text label
    if req.new_label is not None and text:
        text["text"] = req.new_label
        text["version"] = text.get("version", 0) + 1
        mutated_fields.append("new_label")
        
    # 2. Update position
    if req.new_col is not None or req.new_row is not None:
        col = int(req.new_col) if req.new_col is not None else round((container["x"] - COL_START_MARGIN) / COL_WIDTH)
        row = int(req.new_row) if req.new_row is not None else round((container["y"] - ROW_START_MARGIN) / ROW_HEIGHT)
        
        new_x = COL_START_MARGIN + col * COL_WIDTH
        new_y = ROW_START_MARGIN + row * ROW_HEIGHT
        
        dx = new_x - container["x"]
        dy = new_y - container["y"]
        
        container["x"] = new_x
        container["y"] = new_y
        container["version"] = container.get("version", 0) + 1
        
        if text:
            text["x"] += dx
            text["y"] += dy
            text["version"] = text.get("version", 0) + 1
            
        if req.new_col is not None:
            mutated_fields.append("new_col")
        if req.new_row is not None:
            mutated_fields.append("new_row")
            
        # Recalculate affected arrows
        for el in scene["elements"]:
            if el.get("type") == "arrow" and not el.get("isDeleted"):
                start_id = el.get("startBinding", {}).get("elementId")
                end_id = el.get("endBinding", {}).get("elementId")
                if start_id == req.node_id or end_id == req.node_id:
                    recalculate_arrow(el, scene["elements"])
                    
    # 3. Update color
    if req.new_color is not None:
        color_scheme = COLOR_MAP.get(req.new_color.lower(), COLOR_MAP["blue"])
        container["strokeColor"] = color_scheme["stroke"]
        container["backgroundColor"] = color_scheme["bg"]
        container["version"] = container.get("version", 0) + 1
        mutated_fields.append("new_color")
        
    save_scene(scene)
    return {
        "success": true,
        "node_id": req.node_id,
        "mutated_fields": mutated_fields
    }

@app.post("/delete_node")
def delete_node(req: DeleteNodeRequest):
    scene = load_scene()
    
    container = next((el for el in scene["elements"] if el["id"] == req.node_id and not el.get("isDeleted")), None)
    if not container:
        raise HTTPException(status_code=404, detail="Node not found")
        
    text = next((el for el in scene["elements"] if el.get("containerId") == req.node_id and not el.get("isDeleted")), None)
    
    container["isDeleted"] = True
    container["version"] = container.get("version", 0) + 1
    
    if text:
        text["isDeleted"] = True
        text["version"] = text.get("version", 0) + 1
        
    cascade_deleted_arrows = []
    
    # Clean up arrows linked to the deleted node
    for el in scene["elements"]:
        if el.get("type") == "arrow" and not el.get("isDeleted"):
            start_id = el.get("startBinding", {}).get("elementId")
            end_id = el.get("endBinding", {}).get("elementId")
            if start_id == req.node_id or end_id == req.node_id:
                el["isDeleted"] = True
                el["version"] = el.get("version", 0) + 1
                cascade_deleted_arrows.append(el["id"])
                # Also delete associated label text
                label_el = next((e for e in scene["elements"] if e["id"] == f"label_{el['id']}"), None)
                if label_el:
                    label_el["isDeleted"] = True
                    label_el["version"] = label_el.get("version", 0) + 1
                    
    save_scene(scene)
    return {
        "success": true,
        "deleted_node_id": req.node_id,
        "cascade_deleted_arrows": cascade_deleted_arrows
    }

@app.post("/frame")
def create_boundary_frame(req: FrameRequest):
    scene = load_scene()
    
    frame_x = COL_START_MARGIN + (req.start_col) * COL_WIDTH - 20
    frame_y = ROW_START_MARGIN + (req.start_row) * ROW_HEIGHT - 30
    
    end_x = COL_START_MARGIN + (req.end_col + 1) * COL_WIDTH - 20
    end_y = ROW_START_MARGIN + (req.end_row + 1) * ROW_HEIGHT - 10
    
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
        "name": req.title,
        "version": 1
    }
    
    scene["elements"].append(frame)
    
    # Associate contained nodes
    for el in scene["elements"]:
        if el["id"] == frame_id or el["type"] == "frame" or el.get("isDeleted"):
            continue
        if "x" in el and "y" in el:
            el_cx = el["x"] + el.get("width", 0) / 2
            el_cy = el["y"] + el.get("height", 0) / 2
            if frame_x <= el_cx <= end_x and frame_y <= el_cy <= end_y:
                el["frameId"] = frame_id
                
    save_scene(scene)
    return {
        "success": true,
        "frame_id": frame_id
    }

@app.post("/compile")
def compile_and_save(req: CompileRequest):
    scene = load_scene()
    
    # Filter out all deleted elements
    filtered_elements = [el for el in scene["elements"] if not el.get("isDeleted")]
    
    compiled_scene = {
        "type": "excalidraw",
        "version": 2,
        "source": "https://excalidraw.com",
        "elements": filtered_elements,
        "appState": scene.get("appState", {
            "theme": "dark",
            "viewBackgroundColor": "#0b0f19"
        }),
        "files": scene.get("files", {})
    }
    
    # Save compilation to target filename
    custom_path = f"/workspace/{req.filename}"
    save_scene(compiled_scene, custom_path=custom_path)
    
    return {
        "success": true,
        "filename": req.filename,
        "total_elements": len(filtered_elements),
        "download_url": f"http://localhost:3035/{req.filename}"
    }
