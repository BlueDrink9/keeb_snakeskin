# Get the base names of all .svg files in preset_outlines/
SVG_FILES := $(wildcard preset_outlines/*.svg)
TARGETS := $(patsubst preset_outlines/%.svg,%,$(SVG_FILES))

.PHONY: $(TARGETS) all

define RUN_SNAKESKIN
	python src/snakeskin.py preset_outlines/$@.svg --config preset_configs/$@.json
endef

all_presets: $(TARGETS)

$(TARGETS):
	$(RUN_SNAKESKIN)
