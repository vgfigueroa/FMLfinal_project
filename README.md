# Can a Movie's Script or Poster Predict Its Box Office Success?

This project explores whether machine learning models can predict a movie's commercial success using only its screenplay or poster image — without access to cast popularity, franchise status, or marketing budgets. We built NLP-based and CNN-based models and tested them against inflation-adjusted box office ROI across 1,297 movies.

**Key finding:** Scripts alone explained less than 1% of ROI variance. Posters contained a small but measurable signal. Movie success depends heavily on factors outside the film itself.

---

## Project Structure

```
.
├── README.md
├── DataCollection/
│   ├── create_dataset.ipynb              # Data pipeline: TMDB → posters → scripts → ROI
│   ├── fill_in_missing_rois.ipynb        # Enrich missing ROI from Box Office Mojo
│   ├── master_movie_data.csv             # Compiled movie metadata (local copy)
│   └── open_source/                      # Movie Script Database scraping utilities
│       ├── CITATION.cff                  # Citation for the Movie Script Database tool
│       ├── open_source_movieScripts_scriptREADME.md
│       └── sources/                      # Per-site scraper modules (IMSDb, Dailyscript, etc.)
├── Scripts/
│   ├── qwen_nlp.ipynb                    # Generate Qwen3-4B script embeddings (2560-dim)
│   ├── Movie_script_NLP.ipynb            # RoBERTa model on movie overviews → log_ROI
│   ├── nlp_script_nn.ipynb               # Neural network on Qwen script embeddings
│   ├── nlp_script_other_features_nn.ipynb# NN on embeddings + tabular features
│   ├── xgboost.ipynb                     # XGBoost on Qwen script embeddings (5-fold CV)
│   └── find_keywords.ipynb               # Keyword extraction from scripts
└── Posters/
    ├── Movie_Posters_ResNet_Gross.ipynb  # ResNet50 + metadata MLP → gross revenue
    └── Movie_Posters_ResNet_ROI.ipynb    # ResNet50 variant targeting ROI directly
```

---

## Methods

### Dataset

- **Source:** TMDB Discover API (2005–2024), US theatrical releases
- **Size:** ~1,297 movies with scripts, posters, and computable ROI
- **ROI:** Inflation-adjusted to 2025 USD using BLS CPI data. Computed as `(gross_2025 - budget_2025) / budget_2025`, then log-transformed.
- **Posters:** Downloaded from TMDB. Movies missing a poster received a synthetic version (deterministic Gaussian noise on a placeholder image) to preserve dataset size for the poster experiments.
- **Scripts:** Scraped in priority order from IMSDb → SimplyScripts → ScriptSlug → Alexander Street. A second pass matched a local directory of 8,500+ scripts using normalized title matching and a manual correction map.

See `create_dataset.ipynb` for the full pipeline, including checkpointing, BOM enrichment, and train/test splitting.

---

### NLP Models (Script → ROI)

#### Embeddings: Qwen3-4B (`qwen_nlp.ipynb`)

Full scripts were embedded using `Qwen/Qwen3-Embedding-4B` (2,560-dimensional vectors). Scripts longer than 8,000 tokens were chunked with 200-token overlap; chunk embeddings were averaged. The instruction prefix used was:

> *"Represent this screenplay for predicting box office ROI based on genre, tone, and narrative structure"*

#### Neural Network (`nlp_script_nn.ipynb`)

A 4-layer MLP (2560 → 512 → 256 → 128 → 1) with LayerNorm, GELU, and dropout trained on the Qwen embeddings. Early stopping at 25 epochs patience.

- **Train R²:** ~0.9 (heavy overfitting)
- **Test R²:** ~-0.003 (no generalization)

Feature attributions were computed via Integrated Gradients (Captum) to identify which embedding dimensions drove predictions. High-ROI and low-ROI films activated slightly different dimensions, suggesting the embeddings encode a weak narrative signal that the model cannot reliably exploit.

#### XGBoost (`xgboost.ipynb`)

5-fold cross-validated XGBoost on the same Qwen embeddings (`max_depth=2`, `colsample_bytree=0.3`, heavy regularization).

- **Mean Test R²:** ~0.002–0.004 across folds

Both models confirmed the null result: screenplays as encoded by a large embedding model do not predict box office performance.

#### RoBERTa on Overviews (`Movie_script_NLP.ipynb`)

As a comparison, a fine-tuned `roberta-base` regression head was trained on TMDB plot summaries (not full scripts) to predict `log_ROI`.

- **Test R²:** ~0.034

Overviews performed marginally better than full scripts, likely because short summaries filter out noise and retain genre/tone signals more efficiently.

---

### CNN Models (Poster → Gross / ROI)

#### ResNet50 + Tabular MLP (`Movie_Posters_ResNet_Gross.ipynb`)

A pre-trained ResNet50 backbone (with `layer4` unfrozen for fine-tuning) extracted 2,048-dimensional image features. These were concatenated with tabular metadata:

- One-hot encoded genres (multi-label)
- One-hot encoded MPAA certification
- Log-normalized budget

The combined feature vector was fed into a 3-layer MLP (512 → 256 → 128 → 1) trained with Huber loss and a diversity loss term to reduce regression-to-the-mean.

**Target:** `log1p(gross_2025)` (inflation-adjusted gross revenue).

GradCAM visualizations highlighted which poster regions the model weighted most heavily, and a feature importance analysis decomposed how much each feature type contributed to the first-layer weights.

#### ResNet50 Variant Targeting ROI (`Movie_Posters_ResNet_ROI.ipynb`)

Same architecture with `log_roi` as the target instead of gross. This variant explored whether visual signals predict profitability rather than raw revenue.

---

## Results Summary

| Model | Input | Target | Test R² |
|---|---|---|---|
| RoBERTa | Plot overview (text) | log_ROI | ~0.034 |
| Qwen3 NN | Full script embedding | log_ROI | ~-0.003 |
| XGBoost | Full script embedding | log_ROI | ~0.002–0.004 |
| ResNet50 + MLP | Poster + genre + budget | log(gross) | small positive signal |

Scripts explain less than 1% of ROI variance. Posters carry a modest signal, boosted by the inclusion of budget as a metadata feature. The primary takeaway is that commercial success is driven by distribution, marketing, franchise effects, and audience reception — none of which are captured by the film's intrinsic creative content.

---

## Interpretation

The NLP attribution analysis (Integrated Gradients) revealed that certain embedding dimensions do separate high-ROI from low-ROI films in the test set — the signal exists in the representation space. The models' failure is therefore less about the embeddings and more about the noise in ROI itself: a single-number financial outcome integrates too many unobserved external factors for narrative features to reliably predict it.

GradCAM on the poster model showed that the network attends primarily to typography (title text) and central character imagery rather than color palettes or background. This is consistent with marketing research suggesting that legibility and character prominence drive poster engagement.

---

## Replication Notes

All experiments were run on Google Colab (T4 or L4 GPU). Data is stored in a shared Google Drive at `/content/gdrive/Shareddrives/FML_FINAL/`. To replicate:

1. Set `TMDB_BEARER_TOKEN` in your Colab secrets before running `create_dataset.ipynb`.
2. Run `create_dataset.ipynb` to build `movies_raw.csv`, posters, and scripts. Flags at the bottom of the notebook control which pipeline stages execute.
3. Run `qwen_nlp.ipynb` to generate `script_embeddings.npy` and `movies_with_embeddings.csv`.
4. Run the modeling notebooks in any order once embeddings and CSVs exist.

The script scraping pipeline uses `open_source/sources/` scrapers adapted from [Movie Script Database](https://github.com/Aveek-Saha/Movie-Script-Database) (Saha, 2021).

---

## Dependencies

```
torch torchvision transformers accelerate
scikit-learn xgboost captum
pandas numpy pillow requests beautifulsoup4
tqdm matplotlib
```

Install via:
```bash
pip install torch torchvision transformers accelerate scikit-learn xgboost captum pandas numpy pillow requests beautifulsoup4 tqdm matplotlib
```

---

## Citation

If you use the script database tooling, please cite:

```bibtex
@misc{Saha_Movie_Script_Database_2021,
    author = {Saha, Aveek},
    month  = {7},
    title  = {{Movie Script Database}},
    url    = {https://github.com/Aveek-Saha/Movie-Script-Database},
    year   = {2021}
}
```
