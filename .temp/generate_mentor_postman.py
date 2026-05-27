import json
import re
import os

def generate_postman_collection():
    with open(r"c:\Work\MULEARN\muLearn Backend\mulearnbackend\.temp\mentor_dashboard.md", "r", encoding="utf-8") as f:
        content = f.read()

    collection = {
        "info": {
            "name": "muLearn Mentor Dashboard API",
            "description": "Complete collection of all Mentor Dashboard endpoints based on mentor_dashboard.md",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
        },
        "item": [],
        "variable": [
            {"key": "base_url", "value": "http://localhost:8000", "type": "string"},
            {"key": "token", "value": "YOUR_JWT_TOKEN", "type": "string"},
            {"key": "org_id", "value": "ORG_UUID", "type": "string"},
            {"key": "mentor_id", "value": "MENTOR_UUID", "type": "string"},
            {"key": "session_id", "value": "SESSION_UUID", "type": "string"},
            {"key": "task_id", "value": "TASK_UUID", "type": "string"},
            {"key": "user_id", "value": "USER_UUID", "type": "string"},
            {"key": "log_id", "value": "LOG_UUID", "type": "string"},
            {"key": "muid", "value": "user@mulearn", "type": "string"}
        ]
    }

    # Regex to find endpoint blocks
    # Looking for ### `METHOD /path/`
    endpoint_pattern = re.compile(r'### `(GET|POST|PUT|PATCH|DELETE) ([^`]+)`')
    
    sections = endpoint_pattern.split(content)
    
    # sections will be [pre-text, METHOD1, PATH1, text1, METHOD2, PATH2, text2, ...]
    
    for i in range(1, len(sections), 3):
        method = sections[i]
        path = sections[i+1]
        text_block = sections[i+2]
        
        # Extract path variables like <str:mentor_id> or <uuid:session_id>
        # In the markdown they are usually written as /path/<mentor_id>/ or /path/:mentor_id
        # Let's clean it up for Postman
        postman_path = path
        
        # If the doc uses `<mentor_id>`, convert to `{{mentor_id}}`
        postman_path = re.sub(r'<([^>]+)>', r'{{\1}}', postman_path)
        
        # Create URL parts
        url_parts = ["api", "v1", "dashboard", "mentor"] + [p for p in postman_path.replace("/mentor/", "/").split("/") if p and p != "api" and p != "v1" and p != "dashboard"]
        
        # Reconstruct path string for raw URL
        raw_path = "/".join(url_parts)
        
        # Name the request based on the path
        name = raw_path.replace("api/v1/dashboard/mentor/", "").strip("/")
        if not name:
            name = "mentor-root"
            
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
                    "raw": f"{{{{base_url}}}}/{raw_path}",
                    "host": ["{{base_url}}"],
                    "path": url_parts
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
            
        # Optional: Add query params if described
        # (Assuming they might be in a table or code block, skip for now unless specifically needed)
        
        collection["item"].append(item)

    out_path = r"c:\Work\MULEARN\muLearn Backend\mulearnbackend\.temp\Mentor_Dashboard_Complete.postman_collection.json"
    with open(out_path, "w") as f:
        json.dump(collection, f, indent=4)
        
    print(f"Generated {len(collection['item'])} endpoints in {out_path}")

if __name__ == "__main__":
    generate_postman_collection()
