# Examples

## UMAP Parameter Optimization

The `optimize_umap.py` script helps you find the best UMAP parameters for your port scan data using Bayesian optimization.

### Installation

Install the optional optimization dependencies:

```bash
uv sync --group optimize
```

### Basic Usage

```bash
uv run examples/optimize_umap.py nmap_output.xml --trials 50
```

This will:
1. Load your nmap scan results
2. Run 50 optimization trials using Bayesian optimization
3. Report the best parameters found

### Parallel Execution

Speed up optimization by running multiple trials in parallel:

```bash
uv run examples/optimize_umap.py nmap_output.xml --trials 100 --jobs 4
```

### Persistent Studies

Save optimization progress to a database so you can resume later:

```bash
uv run examples/optimize_umap.py nmap_output.xml \
    --trials 50 \
    --study-name my-scan-optimization \
    --storage sqlite:///optuna.db
```

### Visualization

Generate HTML plots showing optimization progress and parameter relationships:

```bash
uv run examples/optimize_umap.py nmap_output.xml \
    --trials 50 \
    --visualize \
    --output-dir optimization_results/
```

This creates:
- `optimization_history.html` - Shows how the score improved over trials
- `param_importances.html` - Which parameters matter most
- `parallel_coordinate.html` - Relationship between parameters and score
- `slice_plot.html` - How each parameter affects the score

### Saving Trial Bubble Charts

To save an interactive bubble chart for every trial (not just the best), use `--save-trials`:

```bash
uv run examples/optimize_umap.py nmap_output.xml \
    --trials 50 \
    --save-trials \
    --output-dir optimization_results/
```

This creates a `trials/` subdirectory with HTML files:
- `trials/trial_0000.html` - First trial visualization
- `trials/trial_0001.html` - Second trial visualization
- ...
- `trials/trial_0049.html` - Final trial visualization

Each file shows the full bubble chart for that trial's parameters, making it easy to visually compare different parameter combinations.

### Using the Results

After optimization completes, the script will print the best parameters. Use them with scanscope:

```bash
scanscope nmap_output.xml -o output.html \
    --n-neighbors 25 \
    --min-dist 0.15 \
    --metric cosine
```

### Extended Search Space

For more comprehensive optimization, use the `--extended-search` flag to explore additional parameters:

```bash
uv run examples/optimize_umap.py nmap_output.xml \
    --trials 100 \
    --extended-search \
    --jobs 4
```

Extended search includes:
- **`spread`** (0.5-3.0) - Controls the scale of the embedded space
- **`negative_sample_rate`** (1-20) - Controls non-neighbor sample count
- Wider ranges for `n_neighbors` (2-100) and `min_dist` (0.0-0.99)

This is slower but may find better parameter combinations for your specific dataset.

### Advanced Options

```bash
uv run examples/optimize_umap.py --help
```

Key options:
- `--save-trials` - Save bubble chart HTML for each trial (helpful for visual comparison)
- `--extended-search` - Enable extended parameter space (more thorough but slower)
- `--alpha` / `--beta` - Adjust the balance between trustworthiness and clustering quality
- `--pre-deduplicate` - Deduplicate hosts before UMAP (faster, less accurate)
- `--skip-post-deduplicate` - Skip deduplication after UMAP (enabled by default, use this to disable)
- `--remove-empty` - Exclude hosts with no open ports

### Tips

1. **Start small**: Test with 20-30 trials first, then increase if needed
2. **Use parallel jobs**: Set `--jobs 4` (or higher) if you have multiple cores
3. **Save your work**: Use `--storage` to persist results between runs
4. **Visualize**: Use `--visualize` to understand which parameters matter most
5. **Dataset size**: Larger datasets may need more trials to find optimal parameters
