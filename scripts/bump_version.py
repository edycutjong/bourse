import sys
import re

def bump(version_str, part):
    parts = list(map(int, version_str.split('.')))
    if part == 'major':
        parts[0] += 1
        parts[1] = 0
        parts[2] = 0
    elif part == 'minor':
        parts[1] += 1
        parts[2] = 0
    elif part == 'patch':
        parts[2] += 1
    return '.'.join(map(str, parts))

def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ('major', 'minor', 'patch'):
        print("Usage: python bump_version.py [major|minor|patch]")
        sys.exit(1)
        
    part = sys.argv[1]
    
    # Read current version from pyproject.toml
    with open('pyproject.toml', 'r') as f:
        content = f.read()
    
    match = re.search(r'version\s*=\s*"([^"]+)"', content)
    if not match:
        print("Error: Could not find version in pyproject.toml")
        sys.exit(1)
        
    old_version = match.group(1)
    new_version = bump(old_version, part)
    
    # Update pyproject.toml
    new_content = content.replace(f'version = "{old_version}"', f'version = "{new_version}"')
    with open('pyproject.toml', 'w') as f:
        f.write(new_content)
        
    # Update bourse/ingest.py
    with open('bourse/ingest.py', 'r') as f:
        ingest_content = f.read()
    new_ingest = re.sub(
        r'("clientInfo"\s*:\s*\{[^}]*"version"\s*:\s*")([^"]+)(")',
        rf'\g<1>{new_version}\g<3>',
        ingest_content
    )
    with open('bourse/ingest.py', 'w') as f:
        f.write(new_ingest)
        
    # Update server/identity.py
    with open('server/identity.py', 'r') as f:
        id_content = f.read()
    new_id = re.sub(
        r'(version\s*=\s*")([^"]+)(")',
        rf'\g<1>{new_version}\g<3>',
        id_content
    )
    with open('server/identity.py', 'w') as f:
        f.write(new_id)
        
    # Update scripts/mcp_server.py
    with open('scripts/mcp_server.py', 'r') as f:
        mcp_content = f.read()
    new_mcp = re.sub(
        r'("version"\s*:\s*")([^"]+)(")',
        rf'\g<1>{new_version}\g<3>',
        mcp_content
    )
    with open('scripts/mcp_server.py', 'w') as f:
        f.write(new_mcp)
        
    print(new_version)

if __name__ == '__main__':
    main()
