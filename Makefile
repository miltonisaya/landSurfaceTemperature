#/***************************************************************************
# LandSurfaceTemperature
#
# This tool extracts Land Surface Temperature from satellite imagery
#                            -------------------
#       begin               : 2015-11-10
#       copyright           : (C) 2015 by Milton Isaya/Anadolu University
#       email               : milton_issaya@hotmail.com
# ***************************************************************************/
#
#/***************************************************************************
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU General Public License as published by  *
# *   the Free Software Foundation; either version 2 of the License, or     *
# *   (at your option) any later version.                                   *
# *                                                                         *
# ***************************************************************************/

#################################################
# Edit the following to match your sources lists
#################################################

# Add iso code for any locales you want to support here (space separated)
LOCALES =

PLUGINNAME = LandSurfaceTemperature

PY_FILES = \
	__init__.py \
	plugin.py

EXTRAS = metadata.txt

COMPILED_RESOURCE_FILES = resources.py

PEP8EXCLUDE = pydev,resources.py,conf.py,third_party,ui

# QGIS 3 plugin directory — detected per OS
UNAME := $(shell uname)
ifeq ($(UNAME), Darwin)
	QGISDIR = Library/Application Support/QGIS/QGIS3/profiles/default
else
	QGISDIR = .local/share/QGIS/QGIS3/profiles/default
endif

PLUGINDIR = $(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)

#################################################
# Normally you would not need to edit below here
#################################################

default: compile

compile: $(COMPILED_RESOURCE_FILES)

%.py : %.qrc
	pyrcc5 -o $*.py $<

test:
	@echo
	@echo "----------------------"
	@echo "Regression Test Suite"
	@echo "----------------------"
	@python -m pytest -v || true

deploy: compile
	@echo
	@echo "------------------------------------------"
	@echo "Deploying plugin to your QGIS 3 directory."
	@echo "------------------------------------------"
	mkdir -p $(PLUGINDIR)
	cp -vf $(PY_FILES) $(PLUGINDIR)
	cp -vf $(COMPILED_RESOURCE_FILES) $(PLUGINDIR)
	cp -vf $(EXTRAS) $(PLUGINDIR)
	cp -vfr icons $(PLUGINDIR)
	cp -vfr core $(PLUGINDIR)
	cp -vfr processing $(PLUGINDIR)

# Remove compiled Python files from the deployed plugin directory
dclean:
	@echo
	@echo "-----------------------------------"
	@echo "Removing any compiled python files."
	@echo "-----------------------------------"
	find $(PLUGINDIR) -iname "*.pyc" -delete
	find $(PLUGINDIR) -iname "__pycache__" -exec rm -Rf {} +

derase:
	@echo
	@echo "-------------------------"
	@echo "Removing deployed plugin."
	@echo "-------------------------"
	rm -Rf $(PLUGINDIR)

zip: deploy dclean
	@echo
	@echo "---------------------------"
	@echo "Creating plugin zip bundle."
	@echo "---------------------------"
	rm -f $(PLUGINNAME).zip
	cd $(HOME)/$(QGISDIR)/python/plugins; zip -9r $(CURDIR)/$(PLUGINNAME).zip $(PLUGINNAME)

package: compile
	# Create a zip package from the current git HEAD.
	# To package a specific tag or commit: make package VERSION=v1.0
	@echo
	@echo "------------------------------------"
	@echo "Exporting plugin to zip package.    "
	@echo "------------------------------------"
	rm -f $(PLUGINNAME).zip
	git archive --prefix=$(PLUGINNAME)/ -o $(PLUGINNAME).zip $(if $(VERSION),$(VERSION),HEAD)
	@echo "Created package: $(PLUGINNAME).zip"

transup:
	@echo
	@echo "------------------------------------------------"
	@echo "Updating translation files with any new strings."
	@echo "------------------------------------------------"
	@chmod +x scripts/update-strings.sh
	@scripts/update-strings.sh $(LOCALES)

transcompile:
	@echo
	@echo "----------------------------------------"
	@echo "Compiled translation files to .qm files."
	@echo "----------------------------------------"
	@chmod +x scripts/compile-strings.sh
	@scripts/compile-strings.sh $(LRELEASE) $(LOCALES)

transclean:
	@echo
	@echo "------------------------------------"
	@echo "Removing compiled translation files."
	@echo "------------------------------------"
	rm -f i18n/*.qm

clean:
	@echo
	@echo "-------------------------------"
	@echo "Removing compiled resource file"
	@echo "-------------------------------"
	rm -f $(COMPILED_RESOURCE_FILES)

pylint:
	@echo
	@echo "-----------------"
	@echo "Pylint violations"
	@echo "-----------------"
	@pylint --reports=n --rcfile=pylintrc . || true
	@echo
	@echo "----------------------"
	@echo "If you get a 'no module named qgis.core' error, try sourcing"
	@echo "the helper script we have provided first then run make pylint."
	@echo "e.g. source run-env-linux.sh <path to qgis install>; make pylint"
	@echo "----------------------"

# Run pep8 style checking
# http://pypi.python.org/pypi/pep8
pep8:
	@echo
	@echo "-----------"
	@echo "PEP8 issues"
	@echo "-----------"
	@pep8 --repeat --ignore=E203,E121,E122,E123,E124,E125,E126,E127,E128 \
		--exclude $(PEP8EXCLUDE) . || true
	@echo "-----------"
	@echo "Ignored in PEP8 check:"
	@echo $(PEP8EXCLUDE)
