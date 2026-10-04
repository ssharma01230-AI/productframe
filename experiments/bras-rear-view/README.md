# Bra compiler experiment

This is an isolated, opt-in image-generation experiment for the uploaded **Navy lace bralette**. It does not create API generation jobs, write production database records, or use the worker queue.

## Current configuration

- Product data: captured from product `Navy lace bralette` in the local database.
- Product reference: fetched from local MinIO using the same object key used by the application.
- Template reference: `docs/bras-output-details/references/08_rear_model.png`.
- Provider call: OpenAI `images.edit`, with product reference first and template reference second.
- Model: `OPENAI_IMAGE_MODEL` from `services/worker/.env` (currently `gpt-image-2.5-sunburst`).
- Request size: `1024x1024`.
- Quality: `high`.
- API key: read from the existing worker environment; never stored in this folder.

The initial `input.prompt.txt` and `negative.prompt.txt` are generated from the current compiler. Edit `input.prompt.txt` for each prompt iteration. Keep `negative.prompt.txt` unchanged unless deliberately testing the negative prompt too.

## Workflow

1. Edit `input.prompt.txt`.
2. Run the experiment command below.
3. Inspect the generated PNG and manifest under `results/`.
4. Provide the next prompt amendment; do not change production code or invoke the application workflow.

The runner always sends both references in the normal order: product image, then rear-model template image. It records the exact prompt, negative prompt, model, settings, reference paths and provider request ID in each result manifest.

## Commands

From the repository root:

```bash
# Refresh the initial prompt/data snapshot without generating anything
PYTHONPATH=services/api/src:services/worker/src services/worker/.venv/bin/python \
  experiments/bras-rear-view/run_compiler_experiment.py --init

# After editing input.prompt.txt, perform one paid OpenAI provider test
PYTHONPATH=services/api/src:services/worker/src services/worker/.venv/bin/python \
  experiments/bras-rear-view/run_compiler_experiment.py --run --provider openai

# Or run the same references/prompt through Gemini
PYTHONPATH=services/api/src:services/worker/src services/worker/.venv/bin/python \
  experiments/bras-rear-view/run_compiler_experiment.py --run --provider gemini
```

`--init` is safe and does not call an image provider. `--run` is the only command that generates an image and requires explicit approval for that iteration.
