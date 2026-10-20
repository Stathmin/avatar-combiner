# Genetics suite 2026 — 100 adoptable ideas

One place for every genetics capability `avatar-combiner` could add **without
writing the science yourself**. Each row names an existing library, service or
sidecar, its 2026 status and licence, and what it removes from the lab's day.

Кратко: 100 готовых решений, сгруппированных по задачам. Ничего не пишем с
нуля — берём библиотеку или сервис, оборачиваем в `src/tools.py` и даём экран
в TUI.

Status and versions were checked on **2026-10-20** through the PyPI JSON API,
the GitHub REST API and the official service endpoints. Versions move; re-check
before pinning. “Live” means the endpoint answered on that date.

## Legend

| Mark | Meaning |
|---|---|
| `S` / `M` / `L` | effort: under a day / 1–3 days / a week+ or an external sidecar |
| `offline` | works air-gapped after a one-time cache or model download |
| `cloud` | sends identifiers or sequences off the machine; make it opt-in |
| `py3.9` | installs and runs on the project's current floor |
| `↑3.10` / `↑3.11` / `↑3.12` | raises the Python floor for that feature |
| `copyleft` | GPL/AGPL; affects what may ship inside the `.exe` |

## What hurts today

| Pain | Ideas that remove it |
|---|---|
| Plate maps are typed by hand; wells get swapped | 12, 19, 20, 21 |
| A primer looks fine in one tool and fails in another | 1, 2, 9, 11 |
| Multiplex pools are balanced by eye | 3, 10 |
| Hairpins and dimers are discovered after ordering | 13, 14, 18 |
| Cq and ΔΔCt live in hand-edited spreadsheets | 4, 5, 75, 76 |
| A bad amplification curve is only noticed later | 6, 7 |
| The reference gene was never validated | 8 |
| GenBank, SnapGene, VCF, BED and BAM files cannot be opened | 28, 29, 30, 31, 33, 34 |
| An rsID or marker has no gene, consequence or frequency | 52, 54, 56, 57 |
| Plant QTL and soybean marker data are looked up by hand | 53, 73, 74 |
| Results leave the tool as CSV only | 87, 88, 90, 91, 92 |
| Literature checks are manual copy-paste | 93, 95 |

## The one-screen suite

If the goal is a single “Genetics” screen rather than 100 menu items, group it
into five modules and hide everything else behind them:

| Module | What it does | Ideas |
|---|---|---|
| **Design** | primer and oligo design, specificity, structure | 1, 2, 11, 13, 18 |
| **Pool** | multiplex grouping and cross-talk simulation | 3, 10 |
| **Run QC** | Cq, efficiency, melt curves, reference genes | 4, 6, 7, 8 |
| **Annotate** | gene, variant, QTL and marker context | 52, 53, 54, 73, 74 |
| **Report** | XLSX, PDF, DOCX and cached provenance | 72, 88, 90, 91, 92 |

That is a coherent genetics suite with no hand-rolled science: every module is
a thin wrapper over a maintained project.

## Start here: ten low-risk wins

All permissive, offline and light enough for the current bundle.

1. **13 `seqfold`** — pure-Python hairpin and dimer ΔG, Windows wheel.
2. **15 `pydna`** — cloning, barcodes and assembly checks, BSD.
3. **12 `wellmap`** — declarative plate layouts with validation.
4. **32 `pyfaidx`** — indexed FASTA access without Biopython re-parsing.
5. **28 `gb-io`** — real GenBank parsing instead of regexes.
6. **29 `snapgene_reader`** — open the `.dna` files the lab already has.
7. **72 `requests-cache`** — make cloud annotation repeatable and offline.
8. **92 `openpyxl`** — formatted result workbooks, no pandas.
9. **89 `Jinja2` + 90 `reportlab`** — printable QC sheets from templates.
10. **75 `statsmodels`** — proper ANOVA and mixed models on Cq replicates.

## Ideas 1–100

### A. qPCR, primers and assay QC

| # | Idea | Use this (verified) | 2026 status | Licence | Effort / fit |
|---|---|---|---|---|---|
| 1 | Batch primer design across many targets | `primer3` CLI | 2.6.1, commits Aug 2026 | GPL-2.0 | S, offline, same engine as primer3-py |
| 2 | Specificity check before ordering | NCBI Primer-BLAST | live | free public | S, cloud |
| 3 | Multiplex pooling with dimer control | PrimerPooler | active 2026-10-16 | Apache-2.0 | S, CLI, offline |
| 4 | Cq, ΔCt and ΔΔCt without spreadsheets | `qpcr` 4.1.4 | 2025-04-22 | GPL-3.0, copyleft | M, offline |
| 5 | Per-amplicon efficiency fitting | `qpcR` 1.4-2 | 2025-06 | GPL-2+ | M, R sidecar |
| 6 | Amplification and melt-curve QC | `PCRedux` 1.2-1 | 2025-11-19 | MIT | M, R sidecar |
| 7 | Baseline correction cross-check | LinRegPCR | 2021, still hosted | free academic | S, Windows GUI |
| 8 | Reference-gene stability ranking | RefFinder | live | free web | S, cloud |
| 9 | Independent Tm and dimer second opinion | IDT OligoAnalyzer | live | free account | S, cloud |
| 10 | Tube-level hybridization and cross-talk | NUPACK 4.1 | 4.1 docs live | free academic, non-OSI | M, CLI |
| 11 | Offline specificity against a local genome | NCBI BLAST+ | 2.17.0 | public domain | M, sidecar, offline |
| 12 | Declarative plate layouts with validation | `wellmap` 3.5.2 | 2023-09, stable | MIT | S, py3.9, unmaintained |

### B. Oligo thermodynamics and sequence constraints

| # | Idea | Use this (verified) | 2026 status | Licence | Effort / fit |
|---|---|---|---|---|---|
| 13 | Pure-Python folding and dimer ΔG | `seqfold` 0.10.2 | 2026-06-14 | MIT | S, py3.9, Windows wheel |
| 14 | Stronger RNA and DNA structure calls | `ViennaRNA` 2.7.2 | 2025-12-30 | custom, non-OSI | M, check redistribution |
| 15 | Cloning, barcodes and assembly checks | `pydna` 5.5.16 | 2026-06-09 | BSD | M, pulls numpy and matplotlib |
| 16 | Constraint-based oligo and barcode design | `dnachisel` 3.2.16 | 2025-05-10 | MIT | M, pulls numpy |
| 17 | Plant codon usage tables | `python-codon-tables` 0.1.18 | 2025-05-09 | CC0-1.0 | S, py3.9, zero deps |
| 18 | Salt-corrected Tm presets | `primer3-py` (already installed) | maintained | GPL-2.0-or-later | S, no new dependency |

### C. Plate handling and lab systems

| # | Idea | Use this (verified) | 2026 status | Licence | Effort / fit |
|---|---|---|---|---|---|
| 19 | Read and write plate maps and run summaries | `Plateo` 0.3.1 | 2025-05-29 | MIT | M |
| 20 | Canonical 384-well labware definitions | `opentrons` 10.1.0 | 2026-10-15 | Apache-2.0 | S, ↑3.10 |
| 21 | Plate and liquid-handler abstraction | `pylabrobot` 0.2.2 | 2026-07-30 | MIT | L, only if hardware arrives |
| 22 | Push run records to an ELN | eLabFTW 6.0.8 | 2026-10-14 | AGPL-3.0, copyleft | M, self-host |
| 23 | Sample and plate tracking in a LIMS | SENAITE 2.6.0 | 2025-04 | GPL-2.0, copyleft | L, self-host |
| 24 | Versioned SOPs with a DOI | protocols.io API v3 | live | freemium, token | S, cloud |
| 25 | Lab data registry | openBIS 20.10 | current | free academic, proprietary core | L, self-host |

### D. Sequence files, intervals and genome data

| # | Idea | Use this (verified) | 2026 status | Licence | Effort / fit |
|---|---|---|---|---|---|
| 26 | Stream FASTQ and FASTA pairs | `dnaio` 1.2.4 | 2025-10-12 | MIT | S, Windows wheel |
| 27 | Indexed FASTA and FASTQ with QC stats | `pyfastx` 2.3.1 | 2026-06-10 | MIT | S, Windows wheel |
| 28 | Parse GenBank flat files | `gb-io` 0.4.0 | 2026-02-23 | MIT | S, Windows wheel |
| 29 | Import SnapGene `.dna` files | `snapgene_reader` 0.1.23 | 2025-05-10 | MIT | S, pure Python |
| 30 | BAM, CRAM, VCF and tabix access | `pysam` 0.24.1 | 2026-09-07 | MIT | M, no Windows wheel |
| 31 | Pure-Python VCF read and write | `vcfpy` 0.14.2 | 2025-10-02 | MIT | S, py3.9 |
| 32 | Random access to indexed FASTA | `pyfaidx` 0.9.1 | 2026-10-19 | BSD-3-Clause | S, py3.9 |
| 33 | Query GFF and GTF hierarchies | `gffutils` 0.14 | 2026-03-31 | MIT | M, sqlite, numpy |
| 34 | BED, GFF and VCF interval operations | `pybedtools` 0.12.1 | 2026-08-26 | MIT | M, needs `bedtools.exe` |
| 35 | ORF and gene calling | `pyrodigal` 3.7.1 | 2026-03-07 | GPL-3.0, copyleft | M |
| 36 | Phylogenetic tree input and output | `dendropy` 5.1.1 | 2026-10-14 | BSD | S, pure Python |
| 37 | Coverage tracks | `pyBigWig` 0.3.26 | 2026-09-14 | MIT | S |
| 38 | BIOM tables | `biom-format` 2.1.18 | 2026-10-05 | BSD | S, py3.9 |
| 39 | Genome download and management | `genomepy` 0.16.4 | 2026-06-09 | MIT | M, py3.9 |
| 40 | Fast interval data frames | `pyranges` 0.1.4 | 2025-03-14 | MIT | S |
| 41 | Amplicon consensus | `pyabpoa` 1.5.7.1 | 2026-09-17 | MIT | M |

### E. Alignment, motifs and figures

| # | Idea | Use this (verified) | 2026 status | Licence | Effort / fit |
|---|---|---|---|---|---|
| 42 | HMM profile search | `pyhmmer` 0.12.3 | 2026-08-19 | MIT/BSD | M, Windows wheel |
| 43 | SIMD pairwise alignment | `pyopal` 0.7.3 | 2025-08-07 | MIT | S, Windows wheel |
| 44 | Fast multiple sequence alignment | `pyfamsa` 0.7.0 | 2026-03-24 | GPL-3.0, copyleft | M |
| 45 | Edit distance and fuzzy matching | `edlib` 1.3.9 | 2024-09-04 | MIT | S |
| 46 | SIMD Smith-Waterman | `parasail` 1.3.4 | 2023-02-17 | BSD | S |
| 47 | Plasmid and feature maps | `dna-features-viewer` 3.1.5 | 2025-05-09 | MIT | S, matplotlib |
| 48 | Circular genome plots | `pycirclize` 1.10.1 | 2025-10-03 | MIT | M, pandas and numpy |
| 49 | Genome-browser figures | `pyGenomeTracks` 3.9 | 2024-07-10 | GPL-3.0, copyleft | L, heavy |
| 50 | Sequence logos | `logomaker` 0.8.7 | 2025-03-25 | MIT | M, pandas |
| 51 | Static charts for reports | `matplotlib` 3.11.2 | 2026-09-11 | PSF/BSD | M, ↑3.11, heavy |

### F. Variant, gene and clinical annotation

| # | Idea | Use this (verified) | 2026 status | Licence | Effort / fit |
|---|---|---|---|---|---|
| 52 | Consequence annotation from rsID or HGVS | Ensembl VEP REST | release 116 | Apache-2.0, no key | S, cloud, cache it |
| 53 | Plant and soybean gene lookup | Ensembl Plants REST | release 116, 267 species | free, no key | S, cloud |
| 54 | One-call variant aggregation | MyVariant.info | live | BSD, no key | S, cloud |
| 55 | Gene symbol and ID mapping | MyGene.info | live | BSD, no key | S, cloud |
| 56 | ClinVar, dbSNP and Gene records | NCBI E-utilities | live | public domain, key optional | S, cloud |
| 57 | Population allele frequency | gnomAD GraphQL v4 | live | free, no key | S, cloud |
| 58 | Deleteriousness score | CADD | live | free non-commercial, registration for batch | S, human only |
| 59 | Splice-effect prediction | SpliceAI 1.3.1 | 2020, repo active 2026 | GPL-3.0, copyleft | L, offline model, human |
| 60 | Missense pathogenicity | AlphaMissense | live, dataset CC BY 4.0 | free | S, human only |
| 61 | Gene-disease evidence | Open Targets Platform v4 | live | free, no key | S, cloud |
| 62 | SNP-trait associations | GWAS Catalog REST v2 | 232,202 studies | free, no key | S, cloud |
| 63 | Polygenic score definitions | PGS Catalog REST | 6,991 scores | free, no key | S, cloud |
| 64 | PGx dosing guidelines | CPIC API v1 | 2026 guideline data | free, no key | S, human only |
| 65 | Star-allele calling | `pypgx` 0.27.0 | 2026-06-12 | MIT | L, VCF or BAM, human |

### G. Statistics, population and plant genetics

| # | Idea | Use this (verified) | 2026 status | Licence | Effort / fit |
|---|---|---|---|---|---|
| 66 | Phenotype terms and similarity | `pyhpo` 4.0.0 | 2025-03-09 | MIT | S, offline |
| 67 | Offline gene and transcript models | `pyensembl` 2.28.3 | 2026-10-20 | Apache-2.0 | M, ↑3.11 |
| 68 | Fast VCF and BCF parsing | `cyvcf2` 0.34.0 | 2026-06-25 | MIT | S |
| 69 | Allele stats, PCA, relatedness | `scikit-allel` 1.3.13 | 2024-09-17 | MIT | M, ↑3.10 |
| 70 | Kinship, IBD and association | PLINK 2 | 2.0.0-b.1.0, 2026-10-19 | GPL-3.0, copyleft | M, sidecar, offline |
| 71 | Offline GO enrichment | `goatools` 1.6.6 | 2026-10-18 | BSD | M, offline |
| 72 | HTTP cache with expiry and retry | `requests-cache` 1.3.3 | 2026-07-03 | BSD-2-Clause | S, makes cloud work offline |
| 73 | Plant QTL and comparative data | Gramene | live, no key | free | M, cache bulk tables |
| 74 | Soybean QTL and markers | SoyBase | live | free, attribution | M, no public API found |
| 75 | ANOVA and mixed models on Cq | `statsmodels` 0.15.0 | 2026-08-27 | BSD-3 | M, ↑3.10 |
| 76 | Distributions and tests | `scipy` 1.18.1 | 2026-08-21 | BSD-3 | M, ↑3.12 |

### H. Expression, omics and enrichment

| # | Idea | Use this (verified) | 2026 status | Licence | Effort / fit |
|---|---|---|---|---|---|
| 77 | GSEA and over-representation | `gseapy` 1.3.1 | 2026-07-26 | BSD-3 | M, py3.9 |
| 78 | Gene-set libraries | Enrichr | live | free academic | S, cloud |
| 79 | Multi-source functional profiling | g:Profiler | live | free non-commercial | S, cloud |
| 80 | Expression data container | `anndata` 0.13.4 | 2026-09-18 | BSD-3 | M, ↑3.12 |
| 81 | Expression QC and clustering | `scanpy` 1.12.4 | 2026-08-27 | BSD-3 | L, ↑3.12 |
| 82 | Batch correction across plates | `scvi-tools` 1.5.1 | 2026-09-10 | BSD-3 | L, torch, ↑3.12 |
| 83 | Diversity and ordination | `scikit-bio` 0.7.4 | 2026-09-21 | BSD-3 | M, ↑3.10 |

### I. Workflow and reporting

| # | Idea | Use this (verified) | 2026 status | Licence | Effort / fit |
|---|---|---|---|---|---|
| 84 | Reproducible multi-plate runs | Snakemake 9.27.0 | 2026 | MIT | M, ↑3.11 |
| 85 | Heavy pipeline scaling | Nextflow 26.10.2 | 2026-10-15 | Apache-2.0 | L, JVM |
| 86 | Parameterised report notebooks | `papermill` 2.7.0 | current | BSD-3 | M |
| 87 | Publication-quality reports | Quarto 1.10.19 | 2026-10-06 | MIT | M, external binary |
| 88 | HTML to PDF | `WeasyPrint` 70.0 | 2026-09-08 | BSD-3 | M, ↑3.10, native libs |
| 89 | Report templating | `Jinja2` 3.1.6 | 2025-03-05 | BSD-3 | S, py3.9 |
| 90 | PDF primitives | `reportlab` 5.0.1 | 2026-08-20 | BSD | M |
| 91 | DOCX reports | `python-docx` 1.2.0 | 2025-06-16 | MIT | S, lxml |
| 92 | Formatted XLSX workbooks | `openpyxl` 3.1.5 | 2024-06-28 | MIT | S, py3.9, no pandas |

### J. AI and agent infrastructure

| # | Idea | Use this (verified) | 2026 status | Licence | Effort / fit |
|---|---|---|---|---|---|
| 93 | Literature and variant queries for an agent | BioMCP 0.9.3 | 2026-10-18 | MIT | M, cloud |
| 94 | 1000+ tool registry instead of custom wrappers | ToolUniverse 1.5.7 | 2026-10-19 | Apache-2.0 | L, ↑3.10 |
| 95 | PubMed search MCP | PubMed MCP (`cyanheads`) | pushed 2026-10-12 | Apache-2.0 | M, Node and NCBI key |
| 96 | Gene lookup MCP | Ensembl MCP | pushed 2026-02-11 | MIT | S |
| 97 | Taxonomy and assembly metadata MCP | NCBI Datasets MCP | 2025-12-21 | non-commercial | S |
| 98 | Structure lookup MCP | AlphaFold MCP | 2025-12-21 | non-commercial | S |
| 99 | Local LLM run summaries | `ollama` 0.6.3 | 2026-09-29 | MIT | M, local daemon |
| 100 | Embedded GGUF inference | `llama-cpp-python` 0.3.36 | current | MIT | L, heavy build |

## Traps, in the order they bite

1. **GPL is already in the bundle.** `primer3-py` is GPL-2.0-or-later, so the
   shipped `.exe` already carries GPL obligations. Adding GPL-3 tools (ideas 4,
   35, 44, 49, 59, 70) upgrades the whole distribution to GPL-3. Decide whether
   that is acceptable before adding any of them; otherwise run them as optional
   sidecars.
2. **Windows wheels are not universal.** `pysam` has no Windows wheel and
   `pybedtools` needs `bedtools.exe`. `opentrons` needs Python 3.10+,
   `pyensembl` 3.11+, and `scipy`, `scanpy`, `anndata`, `scvi-tools` now need
   3.12. The project's current floor is 3.9, so either raise it or isolate these
   behind optional extras that are never imported by the qPCR path.
3. **Heavy imports kill startup.** `matplotlib`, `numpy`, `pandas` and `torch`
   belong in lazy imports, not in `tools.py`. Keep `Bio.Seq`, `Pint` and
   `primer3-py` as the only eager imports.
4. **Cloud annotation leaks sample names.** MCP servers, Enrichr, g:Profiler,
   Gramene and ELN APIs all send identifiers off-machine. Cache with
   `requests-cache` (idea 72) and gate the first network call behind an explicit
   toggle.
5. **Human databases return empty for soybean.** ClinVar, gnomAD, CADD,
   AlphaMissense, CPIC and HPO are human-only. Gate them on species instead of
   showing empty panels for plant samples.
6. **No instrument binary parser exists.** There is no maintained CFX or
   QuantStudio binary parser. Keep reading the CSV/XLSX exports with stdlib
   `csv` and `openpyxl`; do not hand-roll a binary format.
7. **Non-OSI licences need a human decision.** ViennaRNA and NUPACK are not
   redistributable inside a lab `.exe` without checking terms; both MCP servers
   marked non-commercial cannot ship in a paid build.

## Suggested build order

| Wave | Add | Why now |
|---|---|---|
| 1 | 13, 15, 12, 32, 28, 29, 72, 92, 89, 90 | permissive, offline, light, immediately useful |
| 2 | 1, 2, 11, 3, 4, 6, 8 | closes the primer and QC loop |
| 3 | 52, 53, 54, 56, 62, 73, 74 | turns marker IDs into annotation, cached |
| 4 | 75, 77, 88, 91, 99 | statistics, enrichment, reports, local summaries |

Wave 1 alone gives the tool format import, structure checks, plate validation,
offline caching and a real report — without a single new compiled dependency on
the critical path.
