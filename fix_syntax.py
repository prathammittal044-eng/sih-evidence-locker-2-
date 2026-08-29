import glob

files = glob.glob('frontend/src/**/*.tsx', recursive=True)
bad_string = "${process.env.NEXT_PUBLIC_API_URL || '${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}'}"
good_string = "${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}"

count = 0
for f in files:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    if bad_string in content:
        content = content.replace(bad_string, good_string)
        with open(f, 'w', encoding='utf-8') as file:
            file.write(content)
        count += 1
        print(f"Fixed {f}")

print(f"Total files fixed: {count}")
