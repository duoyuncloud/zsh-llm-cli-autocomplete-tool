#!/usr/bin/env python3
"""Convert training data to Axolotl-compatible format."""

import json
from typing import List, Dict

def convert_to_axolotl_format(input_file: str, output_file: str):
    """Convert our training data to Axolotl's alpaca format."""
    
    with open(input_file, 'r') as f:
        data = [json.loads(line) for line in f]
    
    axolotl_data = []
    
    for item in data:
        # Format for instruction fine-tuning
        axolotl_item = {
            "instruction": "Complete this Zsh command. Provide only the full command without explanations.",
            "input": item["input"],
            "output": item["output"],
            "system": "You are a Zsh shell expert. Always respond with complete, executable Zsh commands. Never explain your reasoning."
        }
        axolotl_data.append(axolotl_item)
    
    # Save in Axolotl format
    with open(output_file, 'w') as f:
        for item in axolotl_data:
            f.write(json.dumps(item) + '\n')
    
    print(f"✅ Converted {len(axolotl_data)} examples to Axolotl format")
    print(f"📁 Output: {output_file}")

def main():
    convert_to_axolotl_format(
        "src/training/zsh_training_data.jsonl",
        "src/training/zsh_training_data_axolotl.jsonl"
    )

if __name__ == "__main__":
    main()