# -----------------------------------------------------------------------------
# This is <Makefile>
# -----------------------------------------------------------------------------
#
#  The file originally was taken from https://github.com/EIDA/mediatorws and
#  adapted to the RT-RAMSIS project.
#
# REVISION AND CHANGES
# 2018/01/26        V0.1    Daniel Armbruster (SED, ETHZ)
#
# =============================================================================
#
# PURPOSE:
# --------
# Install RT-RAMSIS (https://gitlab.seismo.ethz.ch/indu/rt-ramsis).
#
# USAGE:
# ------
# Display a list of RT-RAMSIS subsystems available to be installed:
#
# 	$ make ls
#
# ----
# To install a specific RT-RAMSIS subsystem invoke:
#
# 	$ make install [VENV=PATH_TO_VENV]\
# 		SUBSYSTEMS="whitespace separated list of RT-RAMSIS subsystems to install"
#
# To install all RT-RAMSIS subsystems available invoke:
# 	
# 	$ make install [VENV=PATH_TO_VENV]
#
# To use a Python interpreter instance from a virtual environment pass the VENV
# variable. The default is your python3 interpreter in your PATH.
#
# =============================================================================

SUBSYSTEMS_ALL=ramsis_app
# TODO(damb): Provide installation for all subsystems
#SUBSYSTEMS_ALL=ramsis_app ramsis_workers
SUBSYSTEMS?=$(SUBSYSTEMS_ALL)

PYTHON=$(shell which python3)
PYTHON_PIP=$(shell which pip3)
PYRCC=$(shell which pyrcc5)

ifneq ($(VENV),)
PYTHON=$(realpath $(VENV)/bin/python3)
PYTHON_PIP=$(realpath $(VENV)/bin/pip3)
PYRCC=$(realpath $(VENV)/bin/pyrcc5)
endif

PATH_RAMSIS_SRC=ramsis

MANIFEST_IN=MANIFEST.in
MANIFEST_ALL=MANIFEST.in.all

# -----------------------------------------------------------------------------
#
CHECKVAR=$(if $(filter $(1),$(SUBSYSTEMS_ALL)),, \
	$(error ERROR: Invalid SUBSYSTEMS parameter value: $(1)))
CHECKVARS=$(foreach var,$(1),$(call CHECKVAR,$(var)))

$(call CHECKVARS, $(SUBSYSTEMS))

CHECK_DEP=$(strip $(shell which $(1))) 
CHECK_VENV_DEP=$(strip \
							 $(shell . $(VENV)/bin/activate && which $(1) && deactivate)) 
OQ_CHECK:=$(call CHECK_DEP,oq)
PYQT5_CHECK:=$(call CHECK_DEP,pyrcc5)
ifneq ($(VENV),)
OQ_CHECK:=$(call CHECK_VENV_DEP,oq)
PYQT5_CHECK:=$(call CHECK_VENV_DEP,pyrcc5)
endif

# -----------------------------------------------------------------------------
install: $(patsubst %,%.install,$(SUBSYSTEMS))
sdist: $(patsubst %,%.sdist,$(SUBSYSTEMS))
#test: $(patsubst %,%.test,$(SUBSYSTEMS))

.PHONY: clean build-clean 
clean: build-clean 

build-clean:
	rm -rfv $(MANIFEST_IN)
	rm -rfv build
	rm -rfv *.egg-info

.PHONY: ls
ls:
	@echo "SUBSYSTEMS available: \n$(SUBSYSTEMS_ALL)"


# install subsystems
%.install: %.MANIFEST
	$(PYTHON) setup.py $(@:.install=) develop

# TODO(damb): The checks bellow are a workaround
ramsis_app.install $(PATH_RAMSIS_SRC)/app/ui/views/images_rc.py: \
	ramsis_app.MANIFEST $(PATH_RAMSIS_SRC)/app/ui/views/images.qrc
	$(if $(OQ_CHECK),,$(error ERROR: OpenQuake not installed))
	$(if $(PYQT5_CHECK),,$(error ERROR: PyQt5 not installed))
	$(PYTHON) setup.py $(@:.install=) develop
	$(PYRCC) -o $(PATH_RAMSIS_SRC)/app/ui/views/images_rc.py $(word 2,$^)

# build source distributions
%.sdist: %.MANIFEST
	$(PYTHON) setup.py $(@:.sdist=) sdist

#%.test: %.install
#	python setup.py $(@:.test=) test

# -----------------------------------------------------------------------------
# utility rules

ramsis_app.MANIFEST: $(PATH_RAMSIS_SRC)/app/$(MANIFEST_IN) $(MANIFEST_ALL) 
	$(MAKE) build-clean
	cat $^ > $(MANIFEST_IN)

# ---- END OF <Makefile> ----
