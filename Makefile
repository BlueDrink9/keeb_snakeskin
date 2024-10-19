.PHONY: maizeless ferris basic_macropad

define RUN_SNAKESKIN
	python src/snakeskin.py preset_outlines/$@.svg --config preset_configs/$@.json
endef

maizeless ferris basic_macropad:
	$(RUN_SNAKESKIN)

