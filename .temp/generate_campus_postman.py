import json
import re
import os

def generate_postman_collection():
    with open(r"c:\Work\MULEARN\muLearn Backend\mulearnbackend\.temp\campus.md", "r", encoding="utf-8") as f:
        content = f.read()

    collection = {
        "info": {
            "name": "muLearn Campus Dashboard API",
            "description": "Complete collection of all Campus Dashboard endpoints based on campus.md",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
        },
        "item": [],
        "variable": [
            {"key": "base_url", "value": "http://localhost:8000", "type": "string"},
            {"key": "token", "value": "YOUR_JWT_TOKEN", "type": "string"},
            {"key": "enabler_id", "value": "ENABLER_UUID", "type": "string"},
            {"key": "room_id", "value": "ROOM_UUID", "type": "string"},
            {"key": "schedule_id", "value": "SCHEDULE_UUID", "type": "string"},
            {"key": "id", "value": "UUID", "type": "string"},
            {"key": "ig_id", "value": "IG_UUID", "type": "string"},
            {"key": "org_id", "value": "ORG_UUID", "type": "string"},
        ]
    }

    # Regex to find endpoint blocks
    endpoint_pattern = re.compile(r'Endpoint:\s*`(GET|POST|PUT|PATCH|DELETE)\s+([^`]+)`')
    
    # split gives: [pre-text, METHOD1, PATH1, text1, METHOD2, PATH2, text2, ...]
    sections = endpoint_pattern.split(content)
    
    for i in range(1, len(sections), 3):
        method = sections[i]
        path = sections[i+1].strip()
        text_block = sections[i+2]
        
        # Extract path variables like <str:enabler_id> or <uuid:room_id> or {enabler_id}
        postman_path = path
        
        # If the doc uses `<id>`, convert to `{{id}}`
        postman_path = re.sub(r'<([^>]+)>', r'{{\1}}', postman_path)
        postman_path = re.sub(r'\{([^}]+)\}', r'{{\1}}', postman_path)
        
        # Remove /api/v1/dashboard/campus/ from path to make it clean
        cleaned_path = postman_path.replace("/api/v1/dashboard/campus/", "")
        cleaned_path = cleaned_path.replace("/api/v1/dashboard/enabler/", "")
        
        # Create URL parts
        parts = [p for p in postman_path.split("/") if p]
        
        # Name the request based on the path
        name = cleaned_path.strip("/")
        if not name:
            name = "campus-root"
            
        item = {
            "name": name,
            "request": {
                "method": method,
                "header": [
                    {
                        "key": "Authorization",
                        "value": "Bearer {{token}}",
                        "type": "text"
                    }
                ],
                "url": {
                    "raw": f"{{{{base_url}}}}/{'/'.join(parts)}",
                    "host": ["{{base_url}}"],
                    "path": parts
                }
            }
        }
        
        # Look for JSON body
        body_match = re.search(r'\*\*Request Body\*\*\s*```json\s*(.*?)\s*```', text_block, re.DOTALL)
        if body_match and method in ["POST", "PUT", "PATCH"]:
            body_json = body_match.group(1)
            item["request"]["body"] = {
                "mode": "raw",
                "raw": body_json,
                "options": {
                    "raw": {
                        "language": "json"
                    }
                }
            }
            
        collection["item"].append(item)

    out_path = r"c:\Work\MULEARN\muLearn Backend\mulearnbackend\.temp\Campus_Dashboard_Complete.postman_collection.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(collection, f, indent=4)
        
    print(f"Generated {len(collection['item'])} endpoints in {out_path}")

if __name__ == "__main__":
    generate_postman_collection()
