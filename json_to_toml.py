import json

# Load your downloaded service account json
with open("google_key.json", "r") as f:
    data = json.load(f)

# Open a file to write properly formatted toml
with open(".streamlit/secrets.toml", "w") as f:
    f.write("[google]\n")

    for key, value in data.items():
        if key == "private_key":
            # handle multiline private key properly
            f.write(f'{key} = """{value}"""\n')
        else:
            # write regular keys safely
            if isinstance(value, str):
                value = value.replace('"', '\\"')  # escape double quotes if any
                f.write(f'{key} = "{value}"\n')
            else:
                f.write(f"{key} = {value}\n")

print("✅ secrets.toml generated successfully!")
