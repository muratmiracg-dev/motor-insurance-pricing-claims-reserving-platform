.PHONY: install run test clean

install:
	python -m pip install -e .

run:
	PYTHONPATH=src python scripts/run_pipeline.py

test:
	PYTHONPATH=src python -m unittest discover -s tests -v

clean:
	find data/raw data/processed -type f ! -name '.gitkeep' -delete
	find reports -type f -name '*.xlsx' -delete

