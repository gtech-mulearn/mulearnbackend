import re

# Load campus.md
with open(r"c:\Work\MULEARN\muLearn Backend\mulearnbackend\.temp\campus.md", "r", encoding="utf-8") as f:
    md_content = f.read()

# Extract endpoints from campus.md
md_endpoints = set()
for match in re.finditer(r'Endpoint:\s*`(GET|POST|PUT|PATCH|DELETE)\s+([^`]+)`', md_content):
    md_endpoints.add(f"{match.group(1)} {match.group(2)}")

# Print endpoints in MD
print("Endpoints in campus.md:")
for ep in sorted(md_endpoints):
    print("  " + ep)

# Load urls.py
with open(r"c:\Work\MULEARN\muLearn Backend\mulearnbackend\api\dashboard\campus\urls.py", "r", encoding="utf-8") as f:
    urls_content = f.read()

# Extract path strings from urls.py
url_paths = set()
for match in re.finditer(r'path\(\s*"([^"]*)",', urls_content):
    url_paths.add(f"/api/v1/dashboard/campus/{match.group(1)}")

print("\nEndpoints implemented in urls.py:")
for ep in sorted(url_paths):
    print("  " + ep)

