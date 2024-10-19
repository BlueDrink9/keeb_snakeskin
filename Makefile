# Get the base names of all .svg files in preset_outlines/
SVG_FILES := $(wildcard preset_outlines/*.svg)
TARGETS := $(patsubst preset_outlines/%.svg,%,$(SVG_FILES))

.PHONY: $(TARGETS)

define RUN_SNAKESKIN
	python src/snakeskin.py preset_outlines/$@.svg --config preset_configs/$@.json
endef

$(TARGETS):
	$(RUN_SNAKESKIN)

