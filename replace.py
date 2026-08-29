import os
import glob

files = glob.glob('frontend/src/**/*.tsx', recursive=True)
for f in files:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Replace exact string matches
    content = content.replace("'http://localhost:8000/cases/'", "`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/cases/`")
    content = content.replace("'http://localhost:8000/audit-logs/'", "`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/audit-logs/`")
    
    # Replace template literal prefixes
    content = content.replace("http://localhost:8000", "${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}")
    
    with open(f, 'w', encoding='utf-8') as file:
        file.write(content)
print("Replaced successfully!")
