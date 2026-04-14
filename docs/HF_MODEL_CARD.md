---
base_model: Qwen/Qwen2.5-0.5B-Instruct
library_name: peft
pipeline_tag: text-generation
license: mit
tags:
- lora
- peft
- zsh
- cli
- command-completion
- transformers
- trl
- base_model:adapter:Qwen/Qwen2.5-0.5B-Instruct
---

# zsh-autocomplete-lora

LoRA adapter for local Zsh CLI command completion, used by the `duoyuncloud/zsh-llm-cli-autocomplete-tool` daemon runtime.

## Model Details

- **Adapter type:** PEFT LoRA (`task_type=CAUSAL_LM`)
- **Base model:** `Qwen/Qwen2.5-0.5B-Instruct`
- **Primary use case:** inline shell command completion in Zsh
- **Language:** shell command text (plus lightweight natural language in prompts)

## LoRA Configuration

From `adapter_config.json`:

- `r`: 16
- `lora_alpha`: 32
- `lora_dropout`: 0.05
- `target_modules`: `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj`
- `inference_mode`: true

## Intended Use

- Low-latency local command completion for terminal workflows
- Context-aware completion with shell history and lightweight repository context from host app
- Smart commit command suggestion (handled by host app logic + this adapter)

## Out-of-Scope Use

- Safety-critical automation without user review
- General-purpose factual Q&A or long-form generation
- Execution of generated commands without human confirmation

## Quick Usage

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

base_id = "Qwen/Qwen2.5-0.5B-Instruct"
adapter_id = "duoyuncloud/zsh-autocomplete-lora"

tokenizer = AutoTokenizer.from_pretrained(base_id, trust_remote_code=True)
base = AutoModelForCausalLM.from_pretrained(base_id, trust_remote_code=True)
model = PeftModel.from_pretrained(base, adapter_id)

# Optional: merge for faster standalone inference
merged = model.merge_and_unload()
```

For this project, installation and daemon wiring are handled by:

- `install.sh` in the project repository
- `python -m model_completer.daemon` runtime entrypoint

## Training Notes

This adapter is trained with SFT-style shell completion data (`instruction` / `input` / `output`) and optimized for local interactive inference.

## Limitations

- May suggest incorrect or unsafe commands in ambiguous contexts
- Performance depends on user history/context quality from host integration
- Should be used with explicit user acceptance before command execution

## Safety

- Keep human-in-the-loop confirmation for command execution
- Apply allow/deny checks in host app for risky flags/operations
- Avoid using generated output as direct automation input

## Links

- Project repository: https://github.com/duoyuncloud/zsh-llm-cli-autocomplete-tool
- Runtime install script and daemon integration are maintained in the project repository above.
