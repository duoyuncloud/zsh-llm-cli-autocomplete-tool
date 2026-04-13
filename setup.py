from setuptools import setup, find_packages

setup(
    name="model-cli-autocomplete",
    version="0.1.0",
    description="AI-powered Zsh inline command autocomplete with local model + LoRA",
    author="duoyuncloud",
    license="MIT",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.10",
    install_requires=[
        "requests>=2.28.0",
        "pyyaml>=6.0",
        "argcomplete>=2.0.0", 
        "python-dotenv>=0.19.0",
        "prompt-toolkit>=3.0.0",
    ],
    entry_points={
        "console_scripts": [
            "model-completer=model_completer.cli:main",
        ],
    },
)
