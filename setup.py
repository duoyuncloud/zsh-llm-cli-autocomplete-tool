from setuptools import setup, find_packages

setup(
    name="model-cli-autocomplete",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
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
