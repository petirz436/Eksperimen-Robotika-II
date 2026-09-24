import cv2
import numpy as np
import os

# Dimension in mm (1 pixel = 1 mm)
W, H = 3500, 2800
img = np.ones((H, W, 3), dtype=np.uint8) * 255  # White background

cx, cy = W // 2, H // 2

# Colors (BGR)
COLOR_BLACK = (0, 0, 0)
COLOR_GREEN = (79, 168, 0)   # Green Base
COLOR_BLUE  = (210, 100, 0)  # Blue Base
COLOR_RED   = (0, 0, 220)    # Red Base
COLOR_YELLOW= (0, 221, 255)  # Yellow Stacking Pad

# 1. Draw outer circle (D = 200 cm = 2000 mm -> R = 1000 mm)
cv2.circle(img, (cx, cy), 1000, COLOR_BLACK, 15)

# 2. Draw inner circle (D = 160 cm = 1600 mm -> R = 800 mm)
cv2.circle(img, (cx, cy), 800, COLOR_BLACK, 15)

# 3. Base Tim Parameters:
# Base tim total rectangle: 90 cm (along radial) x 70 cm (perpendicular)
# Pad stacking: 40 x 40 cm at outer end
# Gerbang: 45 cm wide at ring boundary

# --- WEST BASE (GREEN) ---
# Outer circle edge at X = cx - 1000 = 750
# Base extends left from X=750 to X = 750 - 900 = -150 (or X=150 to 1050)
# Let's adjust so it fits nicely on the 3500x2800 banner:
# Base rect: X from (cx - 1000 - 700) to (cx - 1000), Y from (cy - 450) to (cy + 450)
# Green Base: 900 x 700 mm
gw, gh = 900, 700
gx2 = cx - 1000
gx1 = gx2 - gw
gy1 = cy - gh // 2
gy2 = cy + gh // 2
cv2.rectangle(img, (gx1, gy1), (gx2, gy2), COLOR_GREEN, -1)
cv2.rectangle(img, (gx1, gy1), (gx2, gy2), COLOR_BLACK, 5)

# Yellow Pad on Green Base (outer end 400x400 mm)
py1 = cy - 200
py2 = cy + 200
cv2.rectangle(img, (gx1, py1), (gx1 + 400, py2), COLOR_YELLOW, -1)
cv2.rectangle(img, (gx1, py1), (gx1 + 400, py2), COLOR_BLACK, 5)

# Gate (Gerbang 45 cm = 450 mm)
gate_w = 450
cv2.rectangle(img, (gx2 - 50, cy - gate_w // 2), (gx2 + 50, cy + gate_w // 2), (255, 255, 255), -1)
cv2.line(img, (gx2 - 50, cy - gate_w // 2), (gx2 + 50, cy - gate_w // 2), COLOR_BLACK, 5)
cv2.line(img, (gx2 - 50, cy + gate_w // 2), (gx2 + 50, cy + gate_w // 2), COLOR_BLACK, 5)


# --- EAST BASE (BLUE) ---
bx1 = cx + 1000
bx2 = bx1 + gw
by1 = cy - gh // 2
by2 = cy + gh // 2
cv2.rectangle(img, (bx1, by1), (bx2, by2), COLOR_BLUE, -1)
cv2.rectangle(img, (bx1, by1), (bx2, by2), COLOR_BLACK, 5)

# Yellow Pad on Blue Base
cv2.rectangle(img, (bx2 - 400, py1), (bx2, py2), COLOR_YELLOW, -1)
cv2.rectangle(img, (bx2 - 400, py1), (bx2, py2), COLOR_BLACK, 5)

# Gate
cv2.rectangle(img, (bx1 - 50, cy - gate_w // 2), (bx1 + 50, cy + gate_w // 2), (255, 255, 255), -1)
cv2.line(img, (bx1 - 50, cy - gate_w // 2), (bx1 + 50, cy - gate_w // 2), COLOR_BLACK, 5)
cv2.line(img, (bx1 - 50, cy + gate_w // 2), (bx1 + 50, cy + gate_w // 2), COLOR_BLACK, 5)


# --- SOUTH BASE (RED) ---
# Y from (cy + 1000) to (cy + 1000 + 900)
ry1 = cy + 1000
ry2 = ry1 + gw
rx1 = cx - gh // 2
rx2 = cx + gh // 2
cv2.rectangle(img, (rx1, ry1), (rx2, ry2), COLOR_RED, -1)
cv2.rectangle(img, (rx1, ry1), (rx2, ry2), COLOR_BLACK, 5)

# Yellow Pad on Red Base
px1 = cx - 200
px2 = cx + 200
cv2.rectangle(img, (px1, ry2 - 400), (px2, ry2), COLOR_YELLOW, -1)
cv2.rectangle(img, (px1, ry2 - 400), (px2, ry2), COLOR_BLACK, 5)

# Gate
cv2.rectangle(img, (cx - gate_w // 2, ry1 - 50), (cx + gate_w // 2, ry1 + 50), (255, 255, 255), -1)
cv2.line(img, (cx - gate_w // 2, ry1 - 50), (cx - gate_w // 2, ry1 + 50), COLOR_BLACK, 5)
cv2.line(img, (cx + gate_w // 2, ry1 - 50), (cx + gate_w // 2, ry1 + 50), COLOR_BLACK, 5)

out_path = "/home/fathir/eksbot2/catkin_ws/src/eksbot_simulation/models/arena_ground/materials/textures/arena_banner.png"
cv2.imwrite(out_path, img)
print(f"Arena texture generated at: {out_path}")
