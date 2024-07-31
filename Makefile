.PHONY: compile sync all

# Run all steps
all: compile sync

# Compile the requirements using uv
compile:
	uv pip compile requirements.in -o requirements.txt --index-strategy unsafe-any-match --emit-index-url

# Sync the requirements using uv
sync:
	uv pip sync requirements.txt

