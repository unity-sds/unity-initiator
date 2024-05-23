#!/bin/bash
set -e

pip install pre-commit
pip install bandit

pre-commit install
pre-commit autoupdate

# Check the operating system
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    echo "Detected macOS. Installing dependencies using Homebrew..."

    # Install dependencies
    brew install tflint tfsec terraform-docs

    echo "Dependencies installed successfully."

elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    echo "Detected Linux. Downloading and installing pre-built binaries..."

    # Ensure bin directory exists
    mkdir -p "$HOME"/bin

    # Download the pre-built binaries to bin directory
    curl -L -o "$HOME"/bin/tflint.zip https://github.com/terraform-linters/tflint/releases/download/v0.51.1/tflint_linux_amd64.zip
    curl -L -o "$HOME"/bin/tfsec.tar.gz https://github.com/aquasecurity/tfsec/releases/download/v1.28.6/tfsec_1.28.6_linux_amd64.tar.gz
    curl -L -o "$HOME"/bin/terraform-docs.tar.gz https://github.com/terraform-docs/terraform-docs/releases/download/v0.17.0/terraform-docs-v0.17.0-linux-amd64.tar.gz

    # Unzip/Untar the binaries in the bin directory
    unzip "$HOME"/bin/tflint.zip -d "$HOME"/bin
    tar -xvf "$HOME"/bin/terraform-docs.tar.gz -C "$HOME"/bin
    tar -xvf "$HOME"/bin/tfsec.tar.gz -C "$HOME"/bin

    # Make the binaries executable
    chmod +x "$HOME"/bin/tflint "$HOME"/bin/terraform-docs "$HOME"/bin/tfsec

    # Verify if the binaries work
    "$HOME"/bin/tflint --version
    "$HOME"/bin/tfsec --version
    "$HOME"/bin/terraform-docs --version

elif [[ "$OSTYPE" == "msys" ]]; then
    # Windows
    echo "Detected Windows. Installing dependencies using Chocolatey..."

    # Install dependencies
    choco install tflint tfsec terraform-docs

    echo "Dependencies installed successfully."

else
    # Unsupported operating system
    echo "Unsupported operating system. Please install the dependencies manually."
fi
