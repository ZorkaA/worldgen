import urllib.request
import json

prompt = """You are an expert procedural 3D world designer. Our game currently has a military base, airfield, outpost, radar station, and depot. The user wants to add a "city" zone with a high density of naturally-placed residential and commercial buildings. 

Design a high-density JSON layout template for a zone of type "city".
It should have at least 3 sub-districts (e.g., "downtown_core", "residential_suburbs", "commercial_strip", or similar).
Each sub-district should have multiple slots (e.g., 3-5 slots). 
Use appropriate candidates from our PolygonMilitary pack like: "SM_Bld_Village_House_01", "SM_Bld_Village_House_02" (assume 02 exists), "SM_Bld_Tent_01", "SM_Prop_Sandbags_01", "SM_Bld_Watchtower_01". (Mostly use Village House for city).
Ensure it is extremely high density (many slots, low buffer_meters, overlapping density_thresholds like 0.0 to 0.8).

Output ONLY valid JSON representing the "city" template object (without any markdown formatting). It should match this schema EXACTLY:
{
  "type": "city",
  "display_name": "High-Density Urban City",
  "sub_districts": [
    {
      "district_id": "string",
      "center_offset": [float, float],
      "slots": [
        {
          "slot_id": "string",
          "rel_pos": [float, float],
          "rotation_deg": float,
          "placement_role": "string",
          "candidates": ["string"],
          "density_threshold": float,
          "buffer_meters": float,
          "priority": int
        }
      ]
    }
  ]
}
"""

payload = {
    "model": "qwen3.8:27b",
    "messages": [
        {"role": "user", "content": prompt}
    ],
    "stream": False,
    "format": "json"
}

req = urllib.request.Request("http://localhost:11434/api/chat", data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req) as response:
    result = json.loads(response.read().decode())
    content = result["message"]["content"]
    
    # Save the output to a temporary file
    with open("city_generated.json", "w") as f:
        f.write(content)

print("Generated city template and saved to city_generated.json")
