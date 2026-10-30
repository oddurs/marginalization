# The Widening Edge — build pipeline
#
#   make data      fetch raw sources (cached), process, export stats macros
#   make figures   render the Python-generated figures (the map)
#   make pdf       compile the paper with latexmk + LuaLaTeX
#   make all       data → figures → pdf
#   make final     like `pdf`, but fails if any \placeholder remains
#   make clean     remove LaTeX build products (keeps data caches)
#   make distclean also remove raw downloads and processed data

PYTHON ?= python3
JOB    := widening-edge
PDF    := $(JOB).pdf

# Fixed timestamp so repeated builds produce byte-identical PDFs.
export SOURCE_DATE_EPOCH ?= 1767225600
export FORCE_SOURCE_DATE := 1
export MPLBACKEND := Agg

FETCHERS := m49 wdi cepii unctad cables ncdrisc iab chat naturalearth
RAW_STAMPS := $(foreach f,$(FETCHERS),data/raw/.$(f).stamp)

PROCESSED := data/processed/countries.csv
STATS     := generated/stats.tex
MAP       := figures/remoteness_map.pdf

.PHONY: all data fetch process figures pdf final clean distclean check-citations

all: data figures pdf

# ---------------------------------------------------------------- data
fetch: $(RAW_STAMPS)

data/raw/.%.stamp: scripts/fetch_%.py scripts/_common.py
	$(PYTHON) scripts/fetch_$*.py
	@touch $@

data: $(STATS)

data/processed/remoteness.csv: scripts/build_remoteness.py $(RAW_STAMPS)
	$(PYTHON) scripts/build_remoteness.py

$(PROCESSED): scripts/process_countries.py data/processed/remoteness.csv $(RAW_STAMPS)
	$(PYTHON) scripts/process_countries.py
	$(PYTHON) scripts/process_timeseries.py
	$(PYTHON) scripts/process_adoption.py

$(STATS): scripts/export_stats.py $(PROCESSED)
	$(PYTHON) scripts/export_stats.py

process: $(PROCESSED)

# ---------------------------------------------------------------- figures
figures: $(MAP)

$(MAP): scripts/make_map.py $(PROCESSED)
	$(PYTHON) scripts/make_map.py

# ---------------------------------------------------------------- paper
LATEXMK := latexmk -r ../.latexmkrc -jobname=$(JOB)

pdf: $(STATS) $(MAP)
	cd paper && $(LATEXMK) main.tex
	cp paper/build/$(PDF) $(PDF)

final: $(STATS) $(MAP)
	cd paper && $(LATEXMK) -g -usepretex='\def\finalbuild{}' main.tex
	@if grep -q "PLACEHOLDER:" paper/build/$(JOB).log; then \
	  echo "ERROR: placeholders remain:"; grep "PLACEHOLDER:" paper/build/$(JOB).log; exit 1; fi
	cp paper/build/$(PDF) $(PDF)

check-citations:
	$(PYTHON) scripts/verify_citations.py

clean:
	rm -rf paper/build $(PDF)

distclean: clean
	rm -rf data/raw/* data/raw/.*.stamp data/processed/* generated/* figures/*
